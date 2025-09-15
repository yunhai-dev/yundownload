import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urljoin
from shutil import rmtree

import aiofiles
import m3u8
from httpx import AsyncClient, Response, AsyncHTTPTransport

from yundownload.network.base import BaseProtocolHandler
from yundownload.utils.core import Result
from yundownload.utils.logger import logger

if TYPE_CHECKING:
    from yundownload.core.resources import Resources
    from yundownload.utils.equilibrium import DynamicSemaphore

from yundownload.utils import DEFAULT_CHUNK_SIZE
from Crypto.Cipher import AES


class M3U8ProtocolHandler(BaseProtocolHandler):
    @staticmethod
    def check_protocol(uri: str) -> bool:
        parse = urlparse(uri)
        return parse.scheme in {'http', 'https'} and parse.path.endswith('.m3u8')

    def download(self, resources: 'Resources') -> 'Result':
        super().download(resources)
        return asyncio.run(self.download_segments(resources))

    async def download_segments(self, resources: 'Resources') -> 'Result':
        """
        Download the m3u8 playlist

        :param resources: Resource objects
        :return: Result
        """
        resources.update_semaphore()
        if resources.save_path.exists():
            return Result.EXIST
        async with AsyncClient(
                auth=resources.http_auth,
                timeout=resources.http_timeout,
                params=resources.http_params,
                headers=resources.http_headers,
                cookies=resources.http_cookies,
                mounts={
                    'http://': AsyncHTTPTransport(
                        proxy=resources.http_proxy.get('http'),
                    ),
                    'https://': AsyncHTTPTransport(
                        proxy=resources.http_proxy.get('https'),
                    )
                },
                verify=resources.http_verify
        ) as client:
            final_playlist = await self.handle_variant_playlist(client, resources)
            segments = self.parse_segments(final_playlist)
            tasks = []
            video_path = resources.save_path.parent / f"{resources.save_path.stem}"
            video_path.mkdir(parents=True, exist_ok=True)
            self._total = len(segments)
            segment_paths = []
            for index, seg in enumerate(segments):
                segment_path = video_path / f"{index}.ts"
                tasks.append(
                    asyncio.create_task(
                        self.download_segment(index, seg, segment_path, client, resources.semaphore)
                    )
                )
                segment_paths.append(segment_path)

            results = await asyncio.gather(*tasks)

            if all([r & (Result.SUCCESS | Result.EXIST) for r in results]):
                if not segments[0]['encryption']:
                    await self.merge_segments(segment_paths, resources.save_path)
                elif segments[0]['encryption'] and segments[0]['encryption']['method'] == 'AES-128':
                    key_resp = await client.get(segments[0]['encryption']['key_uri'])
                    key_content = key_resp.content
                    await self.merge_segments(segment_paths, resources.save_path, key_content, segments)

                else:
                    logger.info("This is a encrypted m3u8, please decrypt it by yourself")
                return Result.SUCCESS
            return Result.FAILURE

    async def download_segment(self, index: int, seg: dict, save_path: Path, client: 'AsyncClient',
                               sem: 'DynamicSemaphore') -> 'Result':
        """
        Download the clip
        There is no encryption here, you can decrypt it by rewriting the method
        and getting the value via seg['encryption'].

        :param index: Slice index
        :param seg: Fragment information
        :param save_path: The path to save the clip
        :param client: Network connection pooling
        :param sem: Asynchronous semaphore
        :return:
        """
        async with sem:
            logger.info(f"Downloading fragments #{index} encryption {bool(seg['encryption'])} from {seg['uri']}")
            async with client.stream('GET', seg['uri']) as response:
                response: Response
                if not response.is_success: sem.record_result(success=False)
                response.raise_for_status()
                if save_path.exists() and response.headers.get('Content-Length') == str(save_path.stat().st_size):
                    sem.record_result(success=True)
                    await sem.adaptive_update()
                    return Result.EXIST
                async with aiofiles.open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=DEFAULT_CHUNK_SIZE):
                        await f.write(chunk)
                        self.current_size += len(chunk)
                sem.record_result(response.elapsed.total_seconds(), True)
                await sem.adaptive_update()
            logger.info(f"Download fragments #{index} success from {seg['uri']}")
            self._steps += 1
            return Result.SUCCESS

    @staticmethod
    async def merge_segments(segment_paths: list[Path], save_path: Path, key_content: bytes = None, segments: list = None) -> None:
        async with aiofiles.open(save_path, "wb") as f:
            if key_content and segments:
                for index, segment_path in enumerate(segment_paths):
                    cipher = AES.new(key_content, AES.MODE_CBC, bytes.fromhex(segments[index]['encryption']['iv'][2:]))
                    async with aiofiles.open(segment_path, "rb") as segment_file:
                        while True:
                            chunk = await segment_file.read(16384)
                            if not chunk:
                                break
                            await f.write(cipher.decrypt(chunk))
                    logger.info(f"Merge fragments #{segment_path} to {save_path}")

            else:
                for segment_path in segment_paths:
                    async with aiofiles.open(segment_path, "rb") as segment_file:
                        chunk_size = DEFAULT_CHUNK_SIZE
                        while True:
                            chunk = await segment_file.read(chunk_size)
                            if not chunk:
                                break
                            await f.write(chunk)
                    logger.info(f"Merge fragments #{segment_path} to {save_path}")

        for segment_path in segment_paths:
            segment_path.unlink()
            logger.info(f"Delete fragments #{segment_path}")
        rmtree(segment_paths[0].parent, ignore_errors=True)
        logger.info(f"Merge fragments success to {save_path}")

    @staticmethod
    def parse_segments(playlist: m3u8.M3U8) -> list:
        """Parse TS fragment information"""
        segments = []
        for seg in playlist.segments:
            segment_info = {
                'duration': seg.duration,
                'uri': urljoin(playlist.base_uri, seg.uri),
                'encryption': None
            }

            if seg.key:
                segment_info['encryption'] = {
                    'method': seg.key.method,
                    'key_uri': urljoin(playlist.base_uri, seg.key.uri) if seg.key.uri else None,
                    'iv': seg.key.iv if seg.key.iv else None
                }

            segments.append(segment_info)
        return segments

    async def handle_variant_playlist(self, client: 'AsyncClient', resources: 'Resources') -> 'm3u8.M3U8':
        """Process the main playlist and select the sub-list with the highest bitrate"""
        playlist = await self.m3u8_load(client, resources.uri)
        if not playlist.is_variant:
            return playlist

        logger.info(f'm3u8 contains {len(playlist.playlists)} bitrate: {resources.uri} to {resources.save_path}')

        # Select the sub-playlist with the highest bandwidth
        best_playlist = max(
            playlist.playlists,
            key=lambda p: p.stream_info.bandwidth
        )

        logger.info(
            f'Selected sub-bitrate: {best_playlist.uri}, bindwidth: {best_playlist.stream_info.bandwidth}bps resolution: {best_playlist.stream_info.resolution} codecs: {best_playlist.stream_info.codecs}')

        # Load the child playlist
        sub_url = urljoin(playlist.base_uri, best_playlist.uri)
        return await self.m3u8_load(client, sub_url)

    @staticmethod
    async def m3u8_load(client: 'AsyncClient', uri: str) -> 'm3u8.M3U8':
        response = await client.get(uri)
        response: Response
        response.raise_for_status()
        return m3u8.M3U8(response.text, base_uri=urljoin(str(response.url), "."))

    def close(self):
        pass
