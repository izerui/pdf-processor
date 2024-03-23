import os
import unittest

import fitz
from fitz import Page, Document
from fitz.utils import Shape

from support import get_url_content_retry


@unittest.expectedFailure
def convert_doc(doc: Document):
    result = doc
    # try:
    #     result = fitz.open('pdf', doc.convert_to_pdf())
    # except BaseException as e:
    #     pass
    return result


# 测试主入口
class TestTable(unittest.TestCase):

    def __init__(self) -> None:
        self.dir = '扫码报工PDF/遮罩有问题'
        files = []
        for filename in os.listdir(self.dir):
            if filename.startswith('_'):
                os.remove(os.path.join(self.dir, filename))
            else:
                file_path = os.path.join(self.dir, filename)
                if not (os.path.isfile(file_path) and (file_path.endswith('.pdf') or file_path.endswith('.PDF'))):
                    continue
                files.append((filename, fitz.open(file_path)))
        self.sources = []
        for file in files:
            self.sources.append((file[0], convert_doc(file[1])))
        pass

    def setUp(self):
        pass

    def tearDown(self) -> None:
        for source in self.sources:
            source.close()
        pass

    # 插入图片
    def test_insert_image_01(self):
        for filename, doc in self.sources:
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
                    response = get_url_content_retry(img_url)
                    if not response.is_success:
                        raise IOError(f'图片下载失败, url: {img_url}')
                    # page.set_rotation(0)
                    img_pixmap = fitz.Pixmap(response.content)
                    page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0)
                else:
                    shape: Shape = page.new_shape()
                    shape.draw_rect(rect=rect)
                    shape.finish(
                        fill=0,  # fill color
                        color=0  # line color
                    )
                    shape.commit()
            doc.save(os.path.join(self.dir, f'__|{p[0]}|{p[1]}|{p[2]}|{p[3]}|_{filename}'))

    # 插入图片
    def test_insert_image_02(self):
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
            with fitz.open(file_path) as doc:
                for index, page in enumerate(doc):
                    page: Page = page
                    # 遮罩页, 使用源页面未旋转前的矩形区域
                    mark_page: Page = mark_pdf.new_page(width=page.cropbox.width, height=page.cropbox.height)
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
                        response = get_url_content_retry(img_url)
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

                    # page.show_pdf_page(mark_page.cropbox, mark_pdf, rotate=page.rotation, keep_proportion=True, clip=page.cropbox, overlay=True)
                    rotation = page.rotation
                    # 合并前设置两个页面旋转为0，保证页面一致
                    page.set_rotation(0)
                    mark_page.show_pdf_page(rect=page.cropbox, src=doc, pno=index, keep_proportion=True, rotate=0,
                                            clip=mark_page.cropbox)
                    # 合并后页面恢复原来的旋转角度
                    page.set_rotation(rotation)
                    mark_page.set_rotation(page.rotation)

                    # # 获取页面图像
                    # pixmap = mark_page.get_pixmap()
                    # # 保存图像
                    # pixmap.save("page.png")

                # doc.save(os.path.join(dir, f'__doc_|{p[0]}|{p[1]}|{p[2]}|{p[3]}|_{filename}'))
            mark_pdf.save(os.path.join(dir, f'__mark_|{p[0]}|{p[1]}|{p[2]}|{p[3]}|_{filename}'), garbage=3,
                          deflate=True)
            mark_pdf.close()
