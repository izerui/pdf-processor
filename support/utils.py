import logging
import os
import tempfile
import threading
import time
import uuid
from functools import wraps

import httpx
import psutil
from PIL import ImageColor
from fitz import TEXT_ALIGN_LEFT, TEXT_ALIGN_RIGHT, TEXT_ALIGN_CENTER

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
            logger.info(
                f'【pid:[{pid}] thread:[{t.name}] user_cpu_time:[{pinfo.cpu_times().user}] free_mem:[{mem.available / (1024 * 1024)}Mb]】【{repr(func)} {desc}】 耗时: {int(time.perf_counter() * 1000) - s_time}/ms')
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


def get_properties_from_style(style: str):
    """
    解析style字符串，并返回符合pymupdf渲染的属性值对象
    """
    font_size = None
    font_name = None
    color = [0, 0, 0]
    text_align = TEXT_ALIGN_LEFT
    for style in style.split(';'):
        s = style.split(':')
        if s[0] == 'color':
            _color = ImageColor.getcolor(s[1], "RGB")
            color = [_color[0] / 255, _color[1] / 255, _color[2] / 255]
        if s[0] == 'font-size':
            font_size = int(s[1].replace('pt', ''))
        if s[0] == 'font-family':
            font_name = s[1]
        if s[0] == 'text-align':
            match s[1]:
                case 'left':
                    text_align = TEXT_ALIGN_LEFT
                case 'right':
                    text_align = TEXT_ALIGN_RIGHT
                case 'center':
                    text_align = TEXT_ALIGN_CENTER
    return {'font_size': font_size, 'font_name': font_name, 'color': color, 'text_align': text_align}
