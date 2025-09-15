import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import paramiko
from paramiko.ssh_exception import SSHException

from yundownload.core.resources import Resources
from yundownload.network.base import BaseProtocolHandler
from yundownload.utils import retry
from yundownload.utils.core import Result
from yundownload.utils.exceptions import ConnectionException, AuthException
from yundownload.utils.config import DEFAULT_CHUNK_SIZE
from yundownload.utils.logger import logger


class SFTPProtocolHandler(BaseProtocolHandler):
    def __init__(self):
        super().__init__()
        self.transport: Optional[paramiko.Transport] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.support_resume = True

    @staticmethod
    def check_protocol(uri: str) -> bool:
        """检查是否支持 SFTP 协议"""
        return uri.lower().startswith("sftp://")

    def download(self, resources: "Resources"):
        super().download(resources)
        return self._download(resources)

    def _download(self, resources: "Resources"):
        """实现 SFTP 断点续传下载"""
        uri = resources.uri
        local_path = resources.save_path

        parsed = urlparse(uri)
        host = parsed.hostname
        port = parsed.port or resources.sftp_port or 22
        username = parsed.username or "anonymous"
        password = parsed.password or ""
        remote_path = unquote(parsed.path)

        self._connect(host, port)
        self._login(username, password)

        logger.info(f"Login success to {uri}")

        file_stat = self.sftp.stat(remote_path)
        file_size = file_stat.st_size

        prepare_result = self._prepare_local_file(local_path, file_size)
        if prepare_result & Result.EXIST:
            return Result.EXIST

        start_pos = local_path.stat().st_size if local_path.exists() else 0

        with self.sftp.open(remote_path, 'rb') as remote_file:
            remote_file.seek(start_pos)

            with open(local_path, 'ab' if start_pos > 0 else 'wb') as local_file:
                while True:
                    data = remote_file.read(DEFAULT_CHUNK_SIZE)
                    if not data:
                        break

                    local_file.write(data)
                    self.current_size += len(data)

        if local_path.stat().st_size != file_size:
            raise IOError("File size mismatch after download")

        return Result.SUCCESS

    def close(self):
        """关闭连接"""
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()

    def _connect(self, host: str, port: int):
        """建立 SFTP 连接"""
        try:
            self.transport = paramiko.Transport((host, port)) # noqa
            self.transport.connect()
        except (SSHException, TimeoutError) as e:
            raise ConnectionException(f"SFTP connection failed: {e}")

    def _login(self, username: str, password: str):
        """用户认证"""
        try:
            self.transport.auth_password(username, password)
            if not self.transport.is_authenticated():
                raise AuthException("SFTP authentication failed")

            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        except SSHException as e:
            raise AuthException(f"Authentication error: {e}")

    @staticmethod
    def _prepare_local_file(local_path: Path, remote_size: int) -> 'Result':
        """准备本地文件（处理断点续传）"""
        if local_path.exists():
            local_size = local_path.stat().st_size
            if 0 < remote_size < local_size:
                local_path.unlink()
            elif local_size == remote_size:
                return Result.EXIST
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
        return Result.UNKNOWN
