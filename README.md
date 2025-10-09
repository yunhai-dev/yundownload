![PyPI - Version](https://img.shields.io/pypi/v/yundownload)
![PyPI - Downloads](https://img.shields.io/pypi/dw/yundownload)
![PyPI - License](https://img.shields.io/pypi/l/yundownload)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/yundownload)

# Intro

[Official documentation](https://yunhai-dev.github.io/yundownload/)
> This project is a file downloader, supporting dynamic download according to the size of the file to choose the
> download mode, for the connection that supports breakpoint continuation will automatically break the connection, for
> the
> unsupported link will overwrite the previous content, the project includes retry mechanism, etc., currently supports:
> streaming download, large file fragment download.

# Install

`pip install yundownload`

# Document

[yundownload GitHub](https://github.com/yunhai-dev/yundownload)

# Give an example

```python
from yundownload import Downloader, Resources, WorkerFuture

if __name__ == '__main__':
    with Downloader() as d:
        r1: WorkerFuture = d.submit(Resources(
            uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
            save_path="DeepSeek-R1-AWQ/model-00074-of-00074.safetensors"
        ))
        r2 = d.submit(Resources(
            uri='ftp://yunhai:admin123@192.168.6.99/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip',
            save_path='0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip'
        ))
        r3 = d.submit(Resources(
            uri='sftp://root:20020308@192.168.6.99/root/quick_start.sh',
            save_path='quick_start.sh'
        ))
        r4 = d.submit(Resources(
            uri='https://c1.7bbffvip.com/video/xiantaiyoushu/%E7%AC%AC01%E9%9B%86/index.m3u8',
            save_path='./video/download.mp4',
            metadata={'test': 'test'}
        ))
    print(r1.wait(), r2.wait(), r3.wait(), r4.wait())
    print(r1.state.is_success())
    print(r1.resources.uri)
```

> The command line supports the easiest download in the current version '0.6.0-beta.2' and will be improved in the future

`yundownload uri save_path`

# Change log
- V 0.6.21
  - Fixed some bugs
  - Fix progress abnormal
- V 0.6.20
  - Added CLI parameters
  - Fix progress abnormal
- V 0.6.17
    - Fixed the exception of clearing the cache after m3u8 download
    - Provide the option to force streaming downloads for HTTP downloads
- V 0.6.16
    - Fixed some bugs
- V 0.6.15
    - Fixed some bugs
- V 0.6.14
    - Fixed some bugs
- V 0.6.13
    - The _breakpoint_resumption method has been modified to handle cases where the server does not support Accept-Ranges
    - Use stream to send scoped requests to improve performance and avoid unnecessary requests
    - Updated version number to 0.6.13
- V 0.6.12
    - Fix the abnormal import caused by type labeling
- V 0.6.11
    - Fixed path management issues and unavailability caused by previous version updates
- V 0.6.10 (Unavailable and removed)
    - The fix is compatible with python 3.10
    - Improved task status tracking
    - Modify the average speed to real-time speed
- V 0.6.9
    - Fixed dynamic semaphore errors
- V 0.6.8
    - Fix proxy usage exceptions
    - Fixed incomplete statistics
    - Add default environment variables to control default values such as log output
    - Added proxy test cases
- V 0.6.0-beta.1
    - This is the pre-beta version of version 0.6.0, this time we brought some new features, and removed some of the
      logic and features that were useless and redundant in the previous version, in this version we removed the
      dependency on Niquests, because it didn't conform to the coding specifications and habits of Python, so there was
      a strange way of writing 'async with await client.get(url)', so we still used version 0.4.0 httpx as our network
      request module
- V 0.5.3
    - Fixed some bugs
- V 0.5.2
    - Fixed some bugs
- V 0.5.1
    - Fixed some bugs
- V 0.5.0
    - We thought that a faster underlying framework would make downloads faster, so we removed the original request
      module (httpx) and used a new download module (niquests).
    - And optimized the UI of the terminal tool
- V 0.4.11
    - Optimized type prompts and load command support
- V 0.4.2
    - Fix retry progress
- V 0.4.1
    - Added to file path creation
- V 0.4.0
    - Refactor the core modules, optimize the code structure, and optimize the download speed
- V 0.3.4
    - Fixed event loop duplicate creation
- V 0.3.3
    - Fix progress bar not reset
- V 0.3.2
    - Fixed the file length inconsistency caused by the request header
- V 0.3.1
    - Added version attribute to the package.
      The command line tool wget parameter has also been added to give the request a default header
- V 0.3.0
    - To optimize the performance of the code, need to pay attention to at the same time, in this version and later
      versions of the API changes, details please refer to
      the [official documentation](https://yunhai-dev.github.io/yundownload/) description of V0.3 version
- V 0.2.15
    - Big change, remove 'run' function, add 'download' function. See the documentation.
- V 0.2.14
    - Modified the document and some prompts.
- V 0.2.13
    - Fixed multiple file fragment download file name issue
- V 0.2.12
    - Fixed a size issue with the last piece of the shard download file
- V 0.2.11
    - Removes the compressed portion of the default request header
- V 0.2.10
    - Agent added to support proxy
- V 0.2.9
    - Fix known bugs
- V 0.2.8
    - Fix known bugs and add warnings for subsequent optimization of large file shards
- V 0.2.7
    - Fix known bugs
- V 0.2.6
    - None Example Change the asynchronous writing of files in fragment download
- V 0.2.5
    - Fix known bugs
- V 0.2.4
    - Add the auth parameter to carry identity information
    - You can add the max_redirects parameter to limit the number of redirects
    - Add the retries parameter to specify the number of request tries
    - Add the verify parameter to specify whether to verify the SSL certificate
- V 0.2.3
    - Remove the default log display and add a progress bar to the command line tool
- V 0.2.2
    - Fixed exception handling of sharding download
- V 0.2.1
    - Repair download failure displays complete
- V 0.2.0
    - Fixed an issue with fragment breakpoint continuation in fragment download
- V 0.1.19
    - Fix stream download breakpoint resume issue
- V 0.1.18
    - Fix known bugs
- V 0.1.17
    - Add forced streaming downloads
- V 0.1.16
    - Add command line tools
- V 0.1.15
    - Optimized fragmentation download breakpoint continuation
- V 0.1.14
    - exclude
- V 0.1.13
    - Troubleshooting Heartbeat detection
- V 0.1.12
    - This version throws an exception after a retry failure
- V 0.1.10
    - Optimized breakpoint continuation
    - Optimized concurrent downloads
    - Optimized heartbeat detection
    - Optimized error retry
    - This version still does not throw an exception after a retry failure

# Future

- Provides webui or desktop applications
- Asynchronous support for YunDownloader (although asynchronous is currently used internally, downloader cannot be used
  in asynchronous functions)