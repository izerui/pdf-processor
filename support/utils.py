import logging
import os
import tempfile
import threading
import time
import uuid
from functools import wraps

import httpx
import psutil

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger()

a4_dpi = 150
a4_width = 1754
a4_height = 1240
header_height = 180


def logged(desc=None):
    """
    Add logging to a function. desc is the name
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 在调用原始函数前添加新的功能，或在后面添加
            s_time = int(time.perf_counter() * 1000)
            # 调用原始函数
            result = func(*args, **kwargs)
            pid = os.getpid()
            pinfo = psutil.Process(pid)
            t = threading.current_thread()
            mem = psutil.virtual_memory()
            print(
                f'--->【pid:[{pid}] thread:[{t.name}] user_cpu_time:[{pinfo.cpu_times().user}] free_mem:[{mem.available / (1024 * 1024)}Mb]】【{repr(func)} {desc}】 耗时: {int(time.perf_counter() * 1000) - s_time}/ms')
            return result

        return wrapper

    return decorate


async def async_get_url_file_retry(url, retry_count: int = 5):
    """
    从url获取文件内容，重试5次
    :param url: 文件的url地址
    :return:
    """
    async with httpx.AsyncClient() as client:
        for _ in range(retry_count):
            try:
                resp = await client.get(url)
                return resp
            except Exception:
                continue
        raise RuntimeError(f'{url} 文件下载失败')


def get_url_content_retry(url, retry_count: int = 5):
    """
    从url获取文件内容，重试5次
    :param url: 文件的url地址
    :return:
    """
    for _ in range(retry_count):
        try:
            response = httpx.get(url)
            if not response.is_success:
                raise IOError(f'获取文件内容失败, url: {url}')
            return response.content
        except Exception:
            continue
    raise RuntimeError(f'{url} 获取文件内容失败')


def read_temp_file_instant(callback):
    """
    使用自动删除的路径作为处理，并读取删除前的内容到文件byte数组
    :param callback: 参数为临时路径
    :return:
    """
    # 临时目录，自动删除
    with tempfile.TemporaryDirectory() as temp_folder:
        filepath = os.path.join(temp_folder, f'{uuid.uuid1()}.pdf')
        callback(filepath)
        with open(filepath, 'rb') as f:
            byte_data = bytes(f.read())
            return byte_data

def read_bytes_from_file(file_path: str):
    """
    从文件路径读取二进制
    :param file_path:
    :return:
    """
    with open(file_path, 'rb') as f:
        byte_data = bytes(f.read())
        return byte_data