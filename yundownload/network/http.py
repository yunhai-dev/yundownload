import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import httpx

from yundownload.network.base import BaseProtocolHandler
from yundownload.utils.config import DEFAULT_HEADERS, DEFAULT_CHUNK_SIZE
from yundownload.utils.core import Result
from yundownload.utils.equilibrium import DynamicSemaphore
from yundownload.utils.logger import logger
from yundownload.utils.tools import convert_slice_path

if TYPE_CHECKING:
    from yundownload.core.resources import Resources


class HttpProtocolHandler(BaseProtocolHandler):

    def __init__(self):
        super().__init__()
        self.client: None | httpx.Client = None
        self.aclient: None | httpx.AsyncClient = None
        self._method = 'GET'
        self._slice_threshold = None
        self.sliced_chunk_size = None

    def download(self, resources: 'Resources'):
        super().download(resources)
        self._slice_threshold = resources.http_slice_threshold
        self._method = resources.http_method
        self.sliced_chunk_size = resources.http_sliced_chunk_size

        # 创建基础配置
        base_config = self._create_base_config(resources)

        # 创建同步客户端
        sync_config = base_config.copy()
        sync_config['mounts'] = {
            'http://': httpx.HTTPTransport(
                proxy=resources.http_proxy.get('http'),
            ),
            'https://': httpx.HTTPTransport(
                proxy=resources.http_proxy.get('https'),
            )
        }
        sync_config['transport'] = httpx.HTTPTransport(retries=5)

        self.client = httpx.Client(**sync_config)
        self.client.params.merge(resources.http_params)
        self.client.headers.update(resources.http_headers)
        self.client.cookies.update(resources.http_cookies)

        # 创建异步客户端
        async_config = base_config.copy()
        async_config['mounts'] = {
            'http://': httpx.AsyncHTTPTransport(
                proxy=resources.http_proxy.get('http'),
            ),
            'https://': httpx.AsyncHTTPTransport(
                proxy=resources.http_proxy.get('https'),
            )
        }
        async_config['transport'] = httpx.AsyncHTTPTransport(retries=5)

        self.aclient = httpx.AsyncClient(**async_config)
        resources.update_semaphore()
        return self._match_method(resources)

    @staticmethod
    def _create_base_config(resources: 'Resources'):
        """
        创建HTTP客户端的基础配置
        
        Args:
            resources: 资源对象
            
        Returns:
            包含基础配置的字典
        """
        return {
            'timeout': resources.http_timeout,
            'auth': resources.http_auth,
            'headers': DEFAULT_HEADERS,
            'follow_redirects': True,
            'verify': resources.http_verify
        }

    @staticmethod
    def check_protocol(uri: str) -> bool:
        check_uri = uri.lower()
        return check_uri.startswith('http') or check_uri.startswith('https')

    def _match_method(self, resources: 'Resources') -> Result:
        try:
            test_response = self.client.head(resources.uri)
            test_response.raise_for_status()
            content_length = int(test_response.headers.get('Content-Length', 0))
        except httpx.HTTPStatusError as e:
            try:
                with self.client.stream(self._method, resources.uri, data=resources.http_data) as test_response:
                    test_response.raise_for_status()
                    content_length = int(test_response.headers.get('Content-Length', 0))
            except Exception as e2:
                logger.error(e2, exc_info=True)
                return Result.FAILURE
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.FAILURE

        if resources.save_path.exists():
            if resources.save_path.stat().st_size == content_length:
                return Result.EXIST
            elif resources.save_path.stat().st_size > content_length:
                resources.save_path.unlink()
        resources.save_path.parent.mkdir(parents=True, exist_ok=True)
        breakpoint_flag = self._breakpoint_resumption(test_response)
        resources.metadata['_breakpoint_flag'] = breakpoint_flag
        self._total_size = content_length
        if breakpoint_flag and content_length > self._slice_threshold and not resources.http_stream:
            logger.info(f'sliced download: {content_length} {resources.uri} to {resources.save_path}')
            return asyncio.run(self._sliced_download(resources, content_length))
        else:
            logger.info(f'stream download: {resources.uri} to {resources.save_path}')
            return self._stream_download(resources, content_length)

    def _stream_download(self, resources: 'Resources', content_length: int) -> Result:
        headers = {}
        if resources.save_path.exists():
            file_size = resources.save_path.stat().st_size
            if file_size == content_length:
                logger.info(f'file exist skip download: {resources.uri} to {resources.save_path}')
                return Result.EXIST
            elif file_size > content_length:
                resources.save_path.unlink()
            else:
                headers['Range'] = f'bytes={file_size}-'

        with self.client.stream(self._method,
                                resources.uri,
                                headers=headers,
                                data=resources.http_data) as response:
            response.raise_for_status()
            if resources.metadata.get('_breakpoint_flag', False):
                file_mode = 'ab'
            else:
                file_mode = 'wb'
            with resources.save_path.open(file_mode) as f:
                self.current_size += resources.save_path.stat().st_size
                for chunk in response.iter_bytes(chunk_size=DEFAULT_CHUNK_SIZE):
                    f.write(chunk)
                    self.current_size += len(chunk)
        return Result.SUCCESS

    async def _sliced_download(self, resources: 'Resources', content_length: int) -> Result:
        path_template = convert_slice_path(resources.save_path)
        chunks_path = []
        tasks = []
        for start in range(0, content_length, self.sliced_chunk_size):
            end = start + self.sliced_chunk_size - 1
            if end > (content_length - 1):
                end = content_length - 1
            slice_path = path_template(start)
            tasks.append(
                asyncio.create_task(
                    self._sliced_chunked_download(resources, slice_path, start, end, resources.semaphore)
                )
            )
            chunks_path.append(slice_path)
        results = await asyncio.gather(*tasks)
        if all(results):
            self._merge_chunk(resources.save_path, chunks_path)
            if not self.aclient.is_closed:
                await self.aclient.aclose()
            return Result.SUCCESS
        return Result.FAILURE

    async def _sliced_chunked_download(self, resources: 'Resources', save_path: Path, start: int, end: int,
                                       sem: 'DynamicSemaphore') -> bool:
        async with sem:
            logger.info(f'start sliced download: {resources.uri} to {resources.save_path} {start}-{end}')
            headers = {'Range': f'bytes={start}-{end}'}
            if save_path.exists():
                chunk_file_size = save_path.stat().st_size
                if chunk_file_size == self.sliced_chunk_size:
                    logger.info(f'slice exist skip download: {resources.uri} to {save_path}')
                    self.current_size += save_path.stat().st_size
                    return True
                elif chunk_file_size > self.sliced_chunk_size:
                    logger.info(f'slice size is larger than the slice size: {resources.uri} to {save_path}')
                    save_path.unlink()
                elif chunk_file_size == end - start + 1:
                    logger.info(f'slice exist skip download: {resources.uri} to {save_path}')
                    self.current_size += save_path.stat().st_size
                    return True
                else:
                    file_start = start + chunk_file_size
                    logger.info(f'slice breakpoint resumption: {resources.uri} to {save_path}')
                    headers['Range'] = f'bytes={file_start}-{end}'
                    if file_start == end:
                        logger.info(f'slice exist skip download: {resources.uri} to {save_path}')
                        self.current_size += save_path.stat().st_size
                        return True
            async with self.aclient.stream(self._method,
                                           resources.uri,
                                           headers=headers,
                                           data=resources.http_data) as response:
                response: httpx.Response
                if not response.is_success: sem.record_result(success=False)
                response.raise_for_status()
                async with aiofiles.open(save_path, 'ab') as f:
                    self.current_size += save_path.stat().st_size
                    async for chunk in response.aiter_bytes(chunk_size=DEFAULT_CHUNK_SIZE):
                        await f.write(chunk)
                        self.current_size += len(chunk)
                sem.record_result(response.elapsed.total_seconds(), True)
                await sem.adaptive_update()
            logger.info(f'sliced download success: {resources.uri} to {save_path}')
            return True

    @staticmethod
    def _merge_chunk(save_path: Path, result: list[Path]):
        with save_path.open('wb') as f:
            for chunk_path in result:
                with chunk_path.open('rb') as f_chunk:
                    while True:
                        chunk = f_chunk.read(DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                logger.info(f'merge chunk success: {save_path} to {chunk_path}')
        for chunk_path in result:
            chunk_path.unlink()
            logger.info(f'delete chunk success: {chunk_path}')
        logger.info(f'merge file success: {save_path}')

    def _breakpoint_resumption(self, response):
        if response.headers.get('Accept-Ranges') == 'bytes':
            return True
        else:
            try:
                content = response.request.content
            except httpx.RequestNotRead:
                content = None
            with self.client.stream(self._method, response.request.url, content=content,
                                    headers={'Range': 'bytes=0-1'}) as test_response:
                test_response.raise_for_status()
                return (test_response.headers.get('Content-Range', '').startswith('bytes 0-1/') or
                        test_response.headers.get('Content-Length') == '2')

    def close(self):
        self.client.close()
