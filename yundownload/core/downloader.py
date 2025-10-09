import sys
from concurrent.futures import ProcessPoolExecutor, Future
from typing import TYPE_CHECKING, Type

from ..utils.work import WorkerFuture
from ..network.base import BaseProtocolHandler
from ..network.ftp import FTPProtocolHandler
from ..network.http import HttpProtocolHandler
from ..network.m3u import M3U8ProtocolHandler
from ..network.sftp import SFTPProtocolHandler
from ..utils.core import Result
from ..utils.exceptions import NotSupportedProtocolException
from ..utils.logger import logger
from ..utils.tools import retry

if TYPE_CHECKING:
    from ..core import Resources


def _run(protocols: Type['BaseProtocolHandler'], resources: 'Resources') -> 'Result':
    """
    Run the download callback

    :param protocols: Protocol Matcher
    :param resources: Resource Object
    :return: Result
    """
    return protocols()(resources)


class DownloadProcessPoolExecutor(ProcessPoolExecutor):
    """
    Download the process pool
    """

    def __init__(self, max_workers: int = None, **kwargs):
        super().__init__(max_workers, **kwargs)

    def run_download(self, protocol: Type['BaseProtocolHandler'], resources: 'Resources') -> 'Future[Result]':
        """
        Submit the download task

        :param protocol: Protocol Matcher
        :param resources: Resource Object
        :return: A Future object that returns the result
        """
        return super().submit(_run, protocol, resources)


class Downloader:
    """
    Downloader
    """

    def __init__(self, max_workers: int = 1):
        """
        Downloader

        :param max_workers: Maximum number of processes
        """
        self._protocols: list = [M3U8ProtocolHandler, HttpProtocolHandler, FTPProtocolHandler, SFTPProtocolHandler]
        self._lock_protocol = None
        self._download_pool = DownloadProcessPoolExecutor(max_workers=max_workers)

    def submit(self, resources: 'Resources') -> 'WorkerFuture':
        """
        Submit the task

        :param resources: Resource Object
        :return:
        """
        if self._lock_protocol:
            protocol = self._lock_protocol
        else:
            protocol = self._match_protocol(resources)
        resources.lock()
        return WorkerFuture(
            future=self._download_pool.run_download(protocol, resources),
            protocol=protocol,
            resources=resources
        )

    def lock_protocol(self, protocol: BaseProtocolHandler):
        """
        Lock the protocol

        :param protocol: Protocol Matcher
        :return:
        """
        if self._lock_protocol:
            raise RuntimeError("A protocol is already locked.")
        self._lock_protocol = protocol

    def _match_protocol(self, resources: 'Resources') -> Type['BaseProtocolHandler']:
        """
        Match the download protocol

        :param resources: Resource Object
        :return: Protocol Matcher
        """
        for protocol in self._protocols:
            if protocol.check_protocol(resources.uri):
                logger.info(f"Protocol {protocol.__name__} is supported for {resources.uri}")
                return protocol
        raise NotSupportedProtocolException(resources.uri)

    def add_protocol(self, protocol_handler: BaseProtocolHandler):
        """
        Add a custom protocol handler

        :param protocol_handler: Protocol Matcher
        """
        if isinstance(protocol_handler, BaseProtocolHandler):
            self._protocols.insert(0, protocol_handler)
        else:
            raise TypeError("protocol_handler must be a subclass of BaseProtocolHandler "
                            "and implement its required methods")

    def remove_protocol(self, protocol_handler: BaseProtocolHandler):
        """
        Remove the custom protocol handler

        :param protocol_handler: Protocol Matcher
        """
        if isinstance(protocol_handler, BaseProtocolHandler):
            self._protocols.remove(protocol_handler)
        else:
            raise TypeError("protocol_handler must be a subclass of BaseProtocolHandler "
                            "and implement its required methods")

    def close(self):
        self._download_pool.shutdown(wait=False, cancel_futures=True)
        sys.exit(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
