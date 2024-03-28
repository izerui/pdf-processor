import fcntl
import io
import logging
import os
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import httpx

from fitz import fitz

from support import get_url_content_retry


def random_wait_return(index, item):
    rd = random.randint(1, 5)
    time.sleep(rd)
    return f'{item}_{rd}'


def running_only_one(counter: int):
    with open('access.log', 'w+') as file:
        try:
            t = threading.current_thread()
            now = datetime.now()
            # 转换为指定的格式:
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f'[{now_str}] [{t.name}] : {counter}')
            # 加锁
            # fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            file.write(f'[{now_str}] [{t.name}] : {counter} \r')
            time.sleep(random.randint(1, 2))
            content = file.read()
            assert content.endswith(f'{counter}'), f'文件最后写入不是当前: {counter}'
            pass
        except BaseException as err:
            logging.exception(err)
        finally:
            # 释放锁
            # fcntl.flock(file.fileno(), fcntl.LOCK_UN)
            pass


class TestTable(unittest.TestCase):

    def test_thread(self):
        array = [1, 2, 3, 4, 5, 6, 7, 8]
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for index, item in enumerate(array):
                future = pool.submit(random_wait_return, index, item)
                futures.append(future)
            results = []
            for future in as_completed(futures):  # 并发执行
                pass
            for future in futures:
                results.append(future.result())
            for result in results:
                print(result)

    def test_file_lock(self):
        os.remove('access.log')
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for counter in range(100):
                future = pool.submit(running_only_one, counter)
                futures.append(future)
            # pool.shutdown(wait=True)
            for future in as_completed(futures):
                print('完成一个')
                pass

    def test_open_image(self):
        """
        从网络加载图片
        https://xujinzh.github.io/2022/02/24/python-load-online-image/index.html
        :return:
        """
        from PIL import Image

        url = 'https://file.yj2025.com/77cefac1-b5a2-48b8-a880-1da6fbefa46e.jpg'
        # url = 'https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg'
        # url = 'https://dfile.yj2025.com/zoo-8378189_1280.jpg'

        # PIL加载网络图片，并转换成统一jpeg格式的二进制
        img = Image.open(io.BytesIO(get_url_content_retry(url))).convert("RGB")
        img_stream = io.BytesIO()
        img.save(img_stream, format='JPEG')
        #TODO 这里转成pixmap会不会定义一个引用，缩小pdf体积？
        img_pixmap = fitz.Pixmap(img_stream)

        # img_pixmap = fitz.Pixmap()
        # img_pixmap = fitz.Pixmap(image_array)

        bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-03-26/28205N61101AAA.pdf')
        doc = fitz.open('pdf', bytes)
        for page in doc:
            rect = fitz.Rect(0, 0, 400, 300)
            # https://pymupdf.readthedocs.io/en/latest/page.html#Page.insert_image
            page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0, overlay=True)
        doc.save('11111111.pdf', garbage=3, deflate=True)
        doc.close()