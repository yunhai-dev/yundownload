from ftplib import FTP, error_perm, error_reply
from pathlib import Path
from urllib.parse import urlparse, unquote

from yundownload.core.resources import Resources
from yundownload.network.base import BaseProtocolHandler
from yundownload.utils.core import Result
from yundownload.utils.exceptions import ConnectionException, AuthException
from yundownload.utils.logger import logger


class FTPProtocolHandler(BaseProtocolHandler):
    def __init__(self):
        super().__init__()
        self.ftp = None
        self.support_rest = False
        self.support_size = False

    @staticmethod
    def check_protocol(uri: str) -> bool:
        """检查是否支持FTP协议"""
        return uri.lower().startswith("ftp://")

    def download(self, resources: "Resources"):
        super().download(resources)
        return self._download(resources)

    def _download(self, resources: "Resources"):
        """实现断点续传的流式下载"""
        uri = resources.uri
        local_path = resources.save_path

        parsed = urlparse(uri)
        host = parsed.hostname
        port = parsed.port or resources.ftp_port or 21
        username = parsed.username or "anonymous"
        password = parsed.password or "anonymous@"
        remote_path = unquote(parsed.path)

        if remote_path.startswith('/'):
            # 某些FTP服务器不需要前导斜杠
            remote_path = remote_path[1:]
        if not remote_path:
            logger.error(f"Empty remote path in URI: {uri}")
            return Result.FAILURE

        self._connect(host, port, resources.ftp_timeout)
        self._login(username, password)

        logger.info(f"Login success to {uri}")

        file_size = self._get_remote_size(remote_path)

        prepare = self._prepare_local_file(local_path, file_size)
        self._total_size = file_size
        if prepare == Result.EXIST:
            return Result.EXIST

        with open(local_path, "ab" if self.support_rest else "wb") as f:
            self.current_size += local_path.stat().st_size
            start_pos = f.tell()

            if self.support_rest and start_pos > 0:
                logger.info(f"FTP download resuming from {uri}")
                self.ftp.voidcmd(f"REST {start_pos}")

            def write_chunk(data: bytes):
                f.write(data) # noqa
                self.current_size += len(data)

            logger.info(f"FTP download started from {uri}")
            resp = self.ftp.retrbinary(f"RETR {remote_path}", write_chunk, rest=start_pos)

            if not resp.startswith("226"):
                logger.error(f"The FTP transfer did not complete {uri}")
                return Result.FAILURE

            return Result.SUCCESS

    def close(self):
        """关闭连接"""
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                pass
            self.ftp = None

    def _connect(self, host: str, port: int, timeout: int):
        """建立FTP连接"""
        self.ftp = FTP()
        try:
            self.ftp.connect(host, port, timeout=timeout)
            self._detect_capabilities()
        except Exception as e:
            raise ConnectionException(f"FTP connection failed: {e}")

    def _login(self, username: str, password: str):
        """用户认证"""
        try:
            resp = self.ftp.login(username, password)
            if "230" not in resp:
                raise AuthException("FTP authentication failed")
        except error_perm as e:
            raise AuthException(f"Authentication error: {e}")

    def _detect_capabilities(self):
        """检测服务器能力"""
        try:
            # 检测REST支持
            self.ftp.voidcmd("REST 0")
            self.support_rest = True
        except error_perm:
            self.support_rest = False

        try:
            # 检测SIZE支持
            self.ftp.voidcmd("TYPE I")
            self.ftp.size("")
            self.support_size = True
        except error_perm:
            self.support_size = False

    def _get_remote_size(self, remote_path: str) -> int:
        """获取远程文件大小"""
        if self.support_size:
            try:
                return self.ftp.size(remote_path)
            except error_reply:
                pass
        return 0

    def _prepare_local_file(self, local_path: Path, remote_size: int) -> 'Result':
        """准备本地文件（处理断点续传）"""
        if local_path.exists():
            local_size = local_path.stat().st_size
            if 0 < remote_size < local_size:
                local_path.unlink()
            elif self.support_rest and local_size == remote_size:
                return Result.EXIST
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
        return Result.UNKNOWN