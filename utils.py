import logging
import time
import httpx
import os
import tempfile
import uuid

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger()


def log_time(func):
    def wrapper(*args, **kwargs):
        # 在调用原始函数前添加新的功能，或在后面添加
        s_time = time.time()
        # 调用原始函数
        result = func(*args, **kwargs)
        # 在结果之前或结果之后添加其他内容
        e_time = time.time()
        logger.info(f'统计耗时: {repr(func)} 耗时 ：{e_time - s_time}秒')
        return result

    return wrapper

def get_url_file_for_retry(url):
    """
    从url获取文件内容，重试5次
    :param url: 文件的url地址
    :return:
    """
    for _ in range(5):
        try:
            resp = httpx.get(url)
            return resp
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