import concurrent
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from support import logger


def wait_random_return_index(index: int) -> int:
    time.sleep(random.randint(1, 5))
    return index


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for index in range(10):
            # 开始多线程处理
            future = pool.submit(wait_random_return_index, index)
            futures.append(future)
        # 处理进度
        for future in concurrent.futures.as_completed(futures):  # 并发执行
            print(future.result())
            pass
        print('------------------------------------------------')
        # 按原始顺序添加页
        for index, future in enumerate(futures):
            print(future.result())


def test_print():
    def print_tmp_dir(index):
        import tempfile
        tmp_dir = tempfile.gettempdir()
        time.sleep(random.uniform(1, 3))
        os.remove(tmp_dir)
        return f'{index} -> {tmp_dir}'

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = []
        for index in range(100):
            # 开始多线程处理
            future = pool.submit(print_tmp_dir, index)
            futures.append(future)
        for future in as_completed(futures):
            exception = future.exception()
            if exception:
                print(repr(exception))
            else:
                print(future.result())
            pass
