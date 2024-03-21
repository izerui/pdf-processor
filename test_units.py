import os
import unittest

import fitz
from fitz import Page
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
            with fitz.open(file_path) as doc:
                for index, page in enumerate(doc):
                    page: Page = page
                    # 页面传递进来的缩放倍数,这里使用的时候要进行反向缩放，才能适配原始页面的坐标系
                    zoom = 1
                    # 矩形的左上、右下坐标数组 [x0,y0,x1,y1]
                    p = []
                    for i in [0, 0, 500, 500]:
                        p.append(i / zoom)

                    rect = fitz.Rect(float(p[0]), float(p[1]), float(p[2]), float(p[3]))

                    # 矩阵旋转 https://pymupdf.readthedocs.io/en/latest/page.html#Page.rotation_matrix
                    # rect = rect.transform(page.transformation_matrix)
                    # 等同于: rect = rect * page.transformation_matrix

                    print(filename, f'旋转:【{page.rotation}】')
                    print(f'    页面宽高:{page.bound()}')
                    print(f'    插入坐标矩形:{rect}')
                    print(f'    变换矩阵:{page.transformation_matrix}')
                    print(f'    旋转矩阵:{page.rotation_matrix}')
                    print(f'    反旋矩阵:{page.derotation_matrix}')

                    # 获取可见页面大小
                    media_box = page.mediabox
                    # 获取缩放量和偏移量
                    scale = media_box.width / media_box.height
                    offset_x = media_box.x0
                    offset_y = media_box.y0

                    print("         缩放量：", scale)
                    print("         偏移量 X：", offset_x)
                    print("         偏移量 Y：", offset_y)
                    print("         rect cropbox mediabox 是否一致：", page.rect == page.cropbox == page.mediabox)

                    # img_url = None
                    img_url = 'https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg'
                    if img_url:
                        response = get_url_file_for_retry(img_url)
                        if not response.is_success:
                            raise IOError(f'图片下载失败, url: {img_url}')
                        # page.set_rotation(0)
                        img_pixmap = fitz.Pixmap(response.content)
                        page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0)
                    else:
                        shape: Shape = page.new_shape()
                        shape.draw_rect(rect=rect)
                        shape.finish(
                            fill=0,  # fill color
                            color=0  # line color
                        )
                        shape.commit()
                doc.save(os.path.join(dir, f'__|{p[0]}|{p[1]}|{p[2]}|{p[3]}|_{filename}'))
    pass
