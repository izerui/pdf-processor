import concurrent
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from fitz import fitz


# 测试主入口
class TestTable(unittest.TestCase):

    def test_rotation(self):
        doc = fitz.open('扫码报工PDF/CS01-P3-001-竖向-右侧.pdf')
        for page in doc:
            print(page.rotation)

    def test_file_lock(self):

        def counter(index: int, count: list[int]):
            time.sleep(random.randint(1, 5))
            t = threading.current_thread()
            count[0] += 1
            print(f'[{t.name}]: ', index , count[0])


        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as pool:
            count = [0]
            for i in range(1000):
                # 开始多线程处理
                pool.submit(counter, i, count)
            pool.shutdown(wait=True)
            print('全部执行完毕.')
