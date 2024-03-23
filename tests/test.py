import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def random_wait_return(index, item):
    rd = random.randint(1, 5)
    time.sleep(rd)
    return f'{item}_{rd}'


if __name__ == '__main__':
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
