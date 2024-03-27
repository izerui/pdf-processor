import concurrent
import os
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from fitz import Shape, fitz

from support import get_url_content_retry, read_bytes_from_file


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
            print(f'[{t.name}]: ', index, count[0])

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
        url = 'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/CS01-P3-001.pdf'
        bytes = get_url_content_retry(url)
        target = fitz.open()
        doc = fitz.open('pdf', bytes)
        # doc = fitz.open('pdf', doc.convert_to_pdf())
        for page in doc:
            page.clean_contents()
            mark_img_url = 'https://tfile.yj2025.com/360826a9-27d4-4121-8ede-b3938a2ed6be.jpg'
            mark_img_bytes = get_url_content_retry(mark_img_url)
            img_pixmap = fitz.Pixmap(mark_img_bytes)
            rect = fitz.Rect(140 / 0.2, 561 / 0.2, 290 / 0.2, 652 / 0.2)

            # 记录原来的旋转角度
            _rotation = page.rotation
            # 传入的旋转角度
            rotation = 90
            # 设置为传入的旋转角度，防止显示效果不一致
            page.set_rotation(rotation)
            # 通过设置的旋转角度通过反向计算区域块实际位置
            rect = rect.transform(page.derotation_matrix)
            # 跟随页面旋转角度进行旋转，否则图片方向不对
            page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0, rotate=rotation)

            new_page = target.new_page(width=page.cropbox.width, height=page.cropbox.height)

            page.set_rotation(0)
            new_page.show_pdf_page(page.cropbox, doc, keep_proportion=True, rotate=rotation,
                                   clip=new_page.cropbox)
            # 还原原来的旋转角度
            page.set_rotation(0)

            # 新页面使用原来的旋转角度
            new_page.set_rotation(_rotation)
        target.save(f'result-new-show-{int(time.perf_counter() * 1000)}.pdf')
        doc.close()
        target.close()

    def test_hui(self):

        hui_img_buffer = read_bytes_from_file(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'gray.png'))

        hui_pixmap = fitz.Pixmap(hui_img_buffer)

        url = 'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/CS01-P3-001.pdf'
        bytes = get_url_content_retry(url)
        target = fitz.open()
        doc = fitz.open('pdf', bytes)
        # doc = fitz.open('pdf', doc.convert_to_pdf())
        for page in doc:
            page.clean_contents()
            rect = fitz.Rect(200 / 0.2, 300 / 0.2, 400 / 0.2, 600 / 0.2)

            # 记录原来的旋转角度
            _rotation = page.rotation
            # 传入的旋转角度
            rotation = 90
            # 设置为传入的旋转角度，防止显示效果不一致
            page.set_rotation(rotation)
            # 通过设置的旋转角度通过反向计算区域块实际位置
            rect = rect.transform(page.derotation_matrix)

            # 跟随页面旋转角度进行旋转，否则图片方向不对
            # page.insert_image(rect, pixmap=hui_pixmap, keep_proportion=False, alpha=0, xref=0, rotate=rotation, overlay=True)

            shape: Shape = page.new_shape()
            shape.draw_rect(rect=rect)
            shape.finish(
                fill=(217 / 255, 217 / 255, 217 / 255),  # fill color
                color=(217 / 255, 217 / 255, 217 / 255),  # line color
            )
            shape.commit()

            new_page = target.new_page(width=page.cropbox.width, height=page.cropbox.height)

            page.set_rotation(0)
            new_page.show_pdf_page(page.cropbox, doc, keep_proportion=True, rotate=rotation,
                                   clip=new_page.cropbox)
            # 还原原来的旋转角度
            page.set_rotation(0)

            # 新页面使用原来的旋转角度
            new_page.set_rotation(_rotation)
        target.save(f'result-new-show-{int(time.perf_counter() * 1000)}.pdf')
        doc.close()
        target.close()
