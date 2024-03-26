import concurrent
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from fitz import fitz

from support import get_url_content_retry


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

    def test_open_save_new(self):
        url = 'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/mt_03_22318er_0_806.pdf'
        bytes = get_url_content_retry(url)
        doc = fitz.open('pdf', bytes)
        for page in doc:
            page.clean_contents()
        doc.save(f'result-new-{int(time.perf_counter() * 1000)}.pdf')
        doc.close()

    def test_open_show_page_new(self):
        url = 'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/mt_03_22318er_0_806.pdf'
        bytes = get_url_content_retry(url)
        target = fitz.open()
        doc = fitz.open('pdf', bytes)
        # doc = fitz.open('pdf', doc.convert_to_pdf())
        for page in doc:
            page.clean_contents()

            mark_img_url = 'https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg'
            mark_img_bytes = get_url_content_retry(mark_img_url)
            img_pixmap = fitz.Pixmap(mark_img_bytes)
            rect = fitz.Rect(0, 0, 200, 300)
            page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0)

            new_page = target.new_page(width=page.cropbox.width, height=page.cropbox.height)
            new_page.show_pdf_page(page.cropbox, doc, keep_proportion=True,
                                   clip=new_page.cropbox)
            new_page.set_rotation(page.rotation)
        target.save(f'result-new-show-{int(time.perf_counter() * 1000)}.pdf')
        doc.close()
        target.close()
