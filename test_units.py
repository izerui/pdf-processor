import os
import unittest

import fitz
from fitz import Page, Document
from fitz.utils import Shape

from utils import get_url_file_for_retry


# 测试主入口
class TestTable(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self) -> None:
        pass

    # 插入图片
    def test_insert_image(self):
        dir = '扫码报工PDF/遮罩有问题'
        for filename in os.listdir(dir):
            if filename.startswith('_'):
                os.remove(os.path.join(dir, filename))
        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            if not os.path.isfile(file_path) or not file_path.endswith('.pdf'):
                continue
            # 遮罩doc
            mark_pdf: Document = fitz.open()
            # 遮罩页
            mark_page: Page = None
            with fitz.open(file_path) as doc:
                for index, page in enumerate(doc):
                    page: Page = page
                    # 如果未初始化遮罩页面，用该doc的第一页的长宽来初始化
                    if not mark_page:
                        mark_page = mark_pdf.new_page(width=page.cropbox.width, height=page.cropbox.height)
                        mark_page.set_rotation(page.rotation)
                        # 页面传递进来的缩放倍数,这里使用的时候要进行反向缩放，才能适配原始页面的坐标系
                        zoom = 1
                        # 矩形的左上、右下坐标数组 [x0,y0,x1,y1]
                        p = []
                        for i in [0, 0, 500, 500]:
                            p.append(i / zoom)

                        rect = fitz.Rect(float(p[0]), float(p[1]), float(p[2]), float(p[3]))
                        img_url = None
                        # img_url = 'https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg'
                        if img_url:
                            response = get_url_file_for_retry(img_url)
                            if not response.is_success:
                                raise IOError(f'图片下载失败, url: {img_url}')
                            # page.set_rotation(0)
                            img_pixmap = fitz.Pixmap(response.content)
                            mark_page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0)
                        else:
                            shape: Shape = mark_page.new_shape()
                            shape.draw_rect(rect=rect)
                            shape.finish(
                                fill=0,  # fill color
                                color=0  # line color
                            )
                            shape.commit()
                    page.show_pdf_page(mark_page.rect, mark_pdf, rotate=page.rotation, keep_proportion=True, clip=page.cropbox)

                doc.save(os.path.join(dir, f'__|{p[0]}|{p[1]}|{p[2]}|{p[3]}|_{filename}'))

    pass
