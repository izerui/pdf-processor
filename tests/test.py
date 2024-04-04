import io
import logging
import math
import os
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from xml.etree.ElementTree import Element

import httpx
from fitz import fitz, Document
from prettytable import PrettyTable

from support import get_url_content_retry
from support.utils import get_properties_from_style


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
        # TODO 这里转成pixmap会不会定义一个引用，缩小pdf体积？
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

    def test_open_pdf(self):
        bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-03-26/28205N61101AAA.pdf')
        doc = fitz.open('pdf', bytes)
        for index, page in enumerate(doc):
            print(
                f'''第{index + 1}页
                rect cropbox mediabox 是否一致: {page.rect == page.cropbox == page.mediabox}
                原始矩形宽:{page.cropbox.width}  高:{page.cropbox.height}  旋转角度:{page.rotation}
                旋转矩阵:{page.rotation_matrix}
                变换矩阵:{page.transformation_matrix}''')
            print(doc.xref_object(page.xref))
        doc.close()

    # https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html
    def test_copy_annot(self):
        import xml.etree.ElementTree as ET
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-01/mt_04_24024_0_812.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-02/mt_04_24024_0_812-2.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-02/mt_04_24024_0_812-wps.pdf')
        bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-03/x.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-03/result-1366723231.pdf')
        target_doc: Document = fitz.open()
        doc = fitz.open('pdf', bytes)
        for index, page in enumerate(doc):
            page.clean_contents()
            # print(doc.xref_object(page.xref))
            new_page = target_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.set_rotation(page.rotation)
            # new_page.show_pdf_page(page.cropbox, doc, index, rotate=page.rotation, keep_proportion=True,
            #                        clip=page.cropbox)
            for annot_index, annot in enumerate(page.annots()):
                print('\r\t')
                # print(doc.xref_object(annot.xref))
                # print(annot.xref, annot.type, annot.info['content'], annot.colors["stroke"], annot.rotation)
                # print('Rotation:', doc.xref_get_key(annot.xref, 'Rotation'))
                # print('Contents:', doc.xref_get_key(annot.xref, 'Contents'))
                # print('Default Appearance:', doc.xref_get_key(annot.xref, 'DA'))
                print('Remote Control:', doc.xref_get_key(annot.xref, 'RC'))
                print('Default Style:', doc.xref_get_key(annot.xref, 'DS'))
                keys = doc.xref_get_keys(annot.xref)
                if annot.type[1] == 'FreeText':
                    # 以第一个块的第一行为例，取文字的方向、颜色、字体信息等
                    lines = annot.get_textpage().extractDICT()['blocks'][0]['lines']
                    dir_tuple = lines[0]['dir']
                    # 计算反正切值
                    # 注意：这里是-dir_tuple[1]， https://pymupdf.readthedocs.io/en/latest/textpage.html#f2
                    # MuPDF 和 PDF 的坐标系不同，MuPDF 使用页面的左上角点作为 (0, 0)。而在 PDF 中，这是左下点。
                    # 因此，MuPDF 的 y 轴的正方向是从上至下。这就导致了此处正弦值的符号变化：负值表示文本的逆时针旋转。
                    angle_radians = math.atan2(-dir_tuple[1], dir_tuple[0])
                    # 转换为度数(去掉小数点),并且默认只支持 0、90、180、270
                    rotation = int(angle_radians * 180 / math.pi)
                    if rotation < 0:
                        rotation = rotation + 360

                    # rect = doc.xref_get_key(annot.xref, 'Rect')[1]
                    styles = None
                    if 'RC' in keys:
                        style_json = doc.xref_get_key(annot.xref, 'RC')[1]
                        print('USE RC: ', style_json)
                        rc_xml: Element = ET.fromstring(style_json)
                        style_nodes = []
                        if 'style' in rc_xml.attrib:
                            style_nodes.append(rc_xml)
                        style_nodes.extend(rc_xml.findall(".//*[@style]"))
                        if style_nodes:
                            for node in style_nodes:
                                styles = get_properties_from_style(node.attrib['style'])
                    else:
                        default_style = doc.xref_get_key(annot.xref, 'DS')[1]
                        print('USE DS: ', default_style)
                        styles = get_properties_from_style(default_style)
                    # 复制注释到目标文档中
                    match annot.type[1]:
                        case 'FreeText':
                            annot_tbl = PrettyTable(
                                ['xref', '类型', '内容', '方向', '字体名称', '字体大小', '字体颜色', '对齐方式',
                                 '位置'])

                            annot_tbl.add_row([
                                annot.xref,
                                annot.type[1],
                                annot.get_text(),
                                rotation,
                                styles["font_name"],
                                styles["font_size"],
                                styles["color"],
                                styles["text_align"],
                                annot.rect
                            ])
                            print(annot_tbl)
                            _annot = new_page.add_freetext_annot(rect=annot.rect,
                                                                 text=annot.get_text(),
                                                                 fontname=styles["font_name"],
                                                                 fontsize=styles["font_size"],
                                                                 text_color=styles["color"],
                                                                 align=styles["text_align"],
                                                                 rotate=rotation)
                            # _annot.update(rotate=rotation, text_color= color)
            pass
        target_doc.save('111.pdf', garbage=4, deflate=True)
        doc.close()

    def test_bug_91(self):
        bytes = get_url_content_retry(
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-02/mt_04_24024_0_812-wps.pdf')
        target_doc: Document = fitz.open()
        doc = fitz.open('pdf', bytes)
        for index, page in enumerate(doc):
            page.clean_contents()
            # print(doc.xref_object(page.xref))
            new_page = target_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.set_rotation(page.rotation)
            # new_page.show_pdf_page(page.cropbox, doc, index, rotate=page.rotation, keep_proportion=True,
            #                        clip=page.cropbox)
            for annot_index, annot in enumerate(page.annots()):
                print('\n')
                print('Remote Control:', doc.xref_get_key(annot.xref, 'RC'))
                print('Default Style:', doc.xref_get_key(annot.xref, 'DS'))
                keys = doc.xref_get_keys(annot.xref)
                rotation = 0
                if 'Rotation' in keys:
                    rotation = int(doc.xref_get_key(annot.xref, 'Rotation')[1])
                if rotation < 0:
                    rotation = rotation + 360
                # 复制注释到目标文档中
                match annot.type[1]:
                    case 'FreeText':
                        _annot = new_page.add_freetext_annot(rect=annot.rect,
                                                             text=annot.get_text(),
                                                             rotate=rotation)
            pass
        target_doc.save('222.pdf', garbage=4, deflate=True)

    def test_add_annot_rotation(self):
        text = 'some text with breaks'
        bytes = httpx.get(
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-03/x.pdf').content
        doc = fitz.open('pdf', bytes)
        page = doc[0]
        page.add_freetext_annot((50, 100, 150, 200), text, rotate=90, text_color=(1, 0, 0))
        doc.ez_save('x.pdf')

    def test_get_annot_rotation(self):
        bytes = httpx.get(
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-03/x.pdf').content
        doc = fitz.open('pdf', bytes)
        page = doc[0]
        for annot in page.annots():
            # print(annot.xref, annot.get_text(), doc.xref_get_keys(annot.xref))
            # 以第一个块的第一行为例，取文字的方向、颜色、字体信息等
            line0 = annot.get_textpage().extractDICT()['blocks'][0]['lines'][0]
            dir_tuple = line0['dir']
            # 计算反正切值
            # 注意：这里是-dir_tuple[1]， https://pymupdf.readthedocs.io/en/latest/textpage.html#f2
            # MuPDF 和 PDF 的坐标系不同，MuPDF 使用页面的左上角点作为 (0, 0)。而在 PDF 中，这是左下点。
            # 因此，MuPDF 的 y 轴的正方向是从上至下。这就导致了此处正弦值的符号变化：负值表示文本的逆时针旋转。
            angle_radians = math.atan2(-dir_tuple[1], dir_tuple[0])
            # 转换为度数
            angle_degrees = angle_radians * 180 / math.pi
            # 打印旋转角度
            print(angle_degrees)
            # keys = doc.xref_get_keys(annot.xref)
            # if 'Rotate' in keys:
            #     rotation = int(doc.xref_get_key(annot.xref, 'Rotate')[1])
            #     print('Rotate: ', rotation)
            # if 'Rotation' in keys:
            #     rotation = int(doc.xref_get_key(annot.xref, 'Rotation')[1])
            #     print('Rotation: ', rotation)

    # def test_rotation(self):
    #     bytes = httpx.get('https://tfile.yj2025.com/pdf-processor/source/2024-04-04/竖图方向不正确-1.pdf').content
    #     doc = fitz.open('pdf', bytes)
    #     page = doc[0]
    #     text_page = page.get_textpage()
    #     dict = text_page.extractDICT()
    #     pass
