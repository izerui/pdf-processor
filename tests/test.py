import fcntl
import logging
import os
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


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
