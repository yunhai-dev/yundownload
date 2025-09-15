# 快速开始

> 由于 YunDownload 在经历了大大小小多次更改导致代码过于杂乱，所以于 0.6.0 版本引入设计模式重构了该项目，并且去除了一些冗余代码。

## 安装

您可以通过 `pip` 直接安装本模块

```bash
pip install yundownload
```

如果您已经安装，那么可以通过如下命令更新

```bash
pip install yundownload --upgrade
```

## 快速使用

```python
from yundownload import Downloader, Resources
from yundownload.utils import WorkerFuture 

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

如你所见，该版本可以支持 `http`、`sftp`、`ftp` 以及 `m3u8` 视频的下载

## 资源参数

### 环境变量

在下载资源时，您可以通过环境变量来设置下载器的相关参数，以下是支持的环境变量：

- `YUNDOWNLOAD_LOG_EVERY`: 设置统计日志的输出间隔时间，默认为 `10`
- `YUNDOWNLOAD_DEFAULT_CHUNK_SIZE`: 设置下载器的默认流分块大小，默认为 `1024 * 1024`
- `YUNDOWNLOAD_DEFAULT_SLICED_CHUNK_SIZE`: 设置下载器分片大小，默认为 `1024 * 1024 * 100`
- `YUNDOWNLOAD_DEFAULT_TIMEOUT`: 设置下载器的默认超时时间，默认为 `60`
- `YUNDOWNLOAD_DEFAULT_MAX_RETRY`: 设置下载器的默认重试次数，默认为 `3`
- `YUNDOWNLOAD_DEFAULT_RETRY_DELAY`: 设置下载器的默认重试延迟时间，默认为 `3`

### 强制流式（HTTP 可用）

你可以通过 `http_stream` 参数来强制使用流式下载，这样可以避免服务无法承接自动并发或文件不支持切片下载。

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_stream=True
)
```

### 请求方式（HTTP 与 M3U8 可用）

目前支持的请求方式有 `GET`、`POST`、`PUT`、`DELETE`，默认为 `GET` 请求。

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_method="GET"
)
```

### 禁用切片（HTTP 与 M3U8 可用）

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_stream=True
)
```

### 请求参数（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求参数以字典的形式传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_params={
        "page": "1"
    }
)
```

### 请求数据

请求数据以字典的形式传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_data={
        "data": "test"
    }
)
```

### 请求代理（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求代理以字典的形式传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_proxy={
        "http": "http://127.0.0.1:8080",
        "https": "https://127.0.0.1:8080"
    }
)
```

### 请求头（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求头以字典的形式传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
)
```

### 请求 cookie（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求时携带的 cookie

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_cookies={
        "name": "value"
    }
)
```

### 请求 verify（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求时是否校验证书，默认为 `True`

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_verify=False
)
```

### 请求超时（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求超时以秒为单位传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_timeout=10
)
```

### 请求认证（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，请求认证以元组的形式传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_auth=("username", "password")
)
```

### 切片阈值（仅HTTP可用）

切片阈值以字节为单位传入

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="model-00074-of-00074.safetensors",
    http_slice_threshold=1024 * 1024 * 1024
)
```

### FTP 连接超时（仅FTP可用）

FTP 连接超时以秒为单位传入

```python
from yundownload import Resources

Resources(
    uri="ftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    ftp_timeout=10
)
```

### FTP 端口（仅FTP可用）

FTP 端口传入，或者你也可以通过uri携带

```python
from yundownload import Resources

Resources(
    uri="ftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    ftp_port=21
)
```

### SFTP 端口（仅SFTP可用）

FTP 端口传入，或者你也可以通过uri携带

```python
from yundownload import Resources

Resources(
    uri="sftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    sftp_port=21
)
```

### 拓展元数据（拓展）

拓展元数据以字典的形式传入，可以用于为自定义的下载协议携带自定义的元数据

```python
from yundownload import Resources

Resources(
    uri="sftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    metadata={
        "name": "value"
    }
)
```

### 重试次数（全局可用）

重试次数以整数的形式传入

```python
from yundownload import Resources

Resources(
    uri="sftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    retry=3
)
```

### 重试间隔（全局可用）

重试次数以整数或元组（start 到 end 随机间隔）的形式传入

```python
from yundownload import Resources

Resources(
    uri="sftp://ftpuser:password@127.0.0.1/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    save_path="0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip",
    retry_delay=3  # (5, 10)
)
```

### 自适应异步并发信号（HTTP 与 M3U8 可用）

目前可应用于 `http` 以及 `m3u8` 请求中，`min_concurrency` 默认为 2，`max_concurrency` 默认为 30，`window_size` 自适应并发窗口大小。

```python
from yundownload import Resources

Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="/test_files/http/DeepSeek-R1-AWQ/model-00074-of-00074.safetensors",
    min_concurrency=1,
    max_concurrency=30,
    window_size=100
)
```

## 日志

你可以通过引用 `yundownload.logger` 来获取日志对象，并且内置了一些日志方法，
你可以通过 `logger.resource_start`、`logger.resource_result`、`logger.resource_error`、`logger.resource_exist`、
`logger.resource_log` 来记录资源下载的日志。

```python
from yundownload import logger, Resources, Result

resource = Resources(
    uri="https://hf-mirror.com/cognitivecomputations/DeepSeek-R1-AWQ/resolve/main/model-00074-of-00074.safetensors?download=true",
    save_path="/test_files/http/DeepSeek-R1-AWQ/model-00074-of-00074.safetensors"
)

logger.info('log')
logger.resource_start(resource)
logger.resource_result(resource, Result.SUCCESS)
logger.resource_error(resource, ValueError('...'))
logger.resource_exist(resource)
logger.resource_log(resource, 'log')
```

## 拓展

你可以继承 `yundownload.network.base.BaseProtocolHandler` 来拓展下载协议，
然后通过 `Downloader().add_protocol(MyProtocolHandler)` 来注册协议，
具体实现你可以参考如下示例

```python
from yundownload.network.base import BaseProtocolHandler
from yundownload import Result


class MyProtocolHandler(BaseProtocolHandler):
    @staticmethod
    def check_protocol(uri: str) -> bool:
        """
        检查uri是否被当前下载协议支持，如果支持则返回 True
        """
        pass

    def download(self, resources: 'Resources') -> 'Result':
        """
        你可以在此实现下载逻辑，但你需要返回 Result，此处下载失败直接抛出错误即可，成功的话请返以下的 Result
        """
        return Result.SUCCESS

    def close(self):
        """
        清理服务残留
        """
        pass
```

## 锁定协议

你可以通过 `lock_protocol` 方法来锁定下载协议，这样就不会再去调用资源的check来判断该选择哪一个下载协议

```python
from yundownload import Downloader

with Downloader() as d:
    d.lock_protocol(MyProtocolHandler)
```

## 结果

你可以通过 `submit` 的返回来获取下载结果，来确定任务状态。

```python
from yundownload import Downloader, Resources

with Downloader() as d:
    result = d.submit(Resources(
        uri='ftp://yunhai:admin123@192.168.6.99/data/spider_temp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip',
        save_path=r'C:\Users\YUNHAI\Downloads\download-test/test_files/ftp/0f03dc87-57ec-4278-bf95-15d4a1ad90d3.zip'
    ))
    result.state.is_success()
    result.state.is_failure()
    result.state.is_exist()
    result.state.is_wait()
    print(result.resources.save_path)
    print(result.resources.uri)
```