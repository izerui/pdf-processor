import logging
import os
import tempfile
import time
import uuid

import httpx

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger()

a4_dpi = 150
a4_width = 1754
a4_height = 1240
header_height = 180


def log_time(func):
    def wrapper(*args, **kwargs):
        # 在调用原始函数前添加新的功能，或在后面添加
        s_time = time.time()
        # 调用原始函数
        result = func(*args, **kwargs)
        # 在结果之前或结果之后添加其他内容
        e_time = time.time()
        logger.info(f'=======================================> 【{repr(func)}】 耗时: {e_time - s_time}秒')
        return result

    return wrapper


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
                raise IOError(f'文件下载失败, url: {url}')
            return response.content
        except Exception:
            continue
    raise RuntimeError(f'{url} 文件下载失败')


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
