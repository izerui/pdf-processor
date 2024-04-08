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

import httpx
from fitz import fitz, Document

from support import get_url_content_retry, get_text_rotation_from_dir, a4_width, a4_height, header_height


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
        # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
        fitz.TOOLS.set_small_glyph_heights(True)
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

            # 初始化一张A4纸张大小的新页面
            new_page = target_doc.new_page(width=a4_width, height=a4_height)

            # 计算缩放因子
            scale_factor = min(a4_width / page.cropbox.width, a4_height / page.cropbox.height)

            new_page.set_rotation(page.rotation)
            # 新的底部区域的自身rect大小(即剪切掉header区域后，剩余的底部区域的整个rect)
            bottom_self_rect = fitz.Rect(0, 0, a4_width, a4_height - header_height)
            new_height = a4_width * page.cropbox.height / page.cropbox.width
            bottom_scale_matrix = fitz.Matrix(1, 0, 0, new_height / page.cropbox.height, 0, 0)

            # 底部区域在整个A4纸张的新页面的rect区域
            # bottom_rect = fitz.Rect(0, header_height, a4_width, a4_height)
            new_page.show_pdf_page(new_page.cropbox, doc, index, rotate=page.rotation, keep_proportion=True,
                                   clip=page.cropbox)
            for annot_index, annot in enumerate(page.annots()):
                # if annot.xref != 25:
                #     continue
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
                    content = doc.xref_get_key(annot.xref, 'Contents')[1]
                    fontname = None
                    fontsize = 12
                    #     # 以第一个块的第一行为例，取文字的方向、颜色、字体信息等
                    lines = annot.get_textpage().extractDICT()['blocks'][0]['lines']
                    color = [0, 0, 0]
                    ##### 拆分后按每个span进行添加
                    for line in lines:
                        # 书写方向及书写方式（横/竖） 0 = horizontal, 1 = vertical
                        line_wmode = line['wmode']
                        line_rotation = get_text_rotation_from_dir(line['dir'])
                        line_rect = fitz.Rect(line['bbox'][0], line['bbox'][1], line['bbox'][2], line['bbox'][3])
                        for span in line['spans']:
                            span_size = span['size']
                            fontsize = span_size
                            span_flags = span['flags']
                            span_font = span['font']
                            fontname = span_font
                            # span_color = [((span['color'] >> 16) & 255) / 255, ((span['color'] >> 8) & 255) / 255, (span['color'] & 255) / 255]
                            rgb_tuple = fitz.sRGB_to_pdf(span['color'])
                            span_color = [rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]]
                            color = span_color
                            span_ascender = span['ascender']
                            span_descender = span['descender']
                            span_text = span['text']

                            # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
                            a = span["ascender"]
                            d = span["descender"]
                            o = fitz.Point(span["origin"])
                            r = fitz.Rect(span['bbox'])

                            # a = span["ascender"]
                            # d = span["descender"]
                            # o = fitz.Point(span["origin"])  # its y-value is the baseline
                            # r.y1 = o.y - span["size"] * scale_factor * d / (a - d)
                            # r.y0 = r.y1 - span["size"]

                            r = fitz.Rect(r[0] * scale_factor,
                                          r[1] * scale_factor,
                                          r[2] * scale_factor,
                                          r[3] * scale_factor)
                            _annot = new_page.add_freetext_annot(rect=r,
                                                                 text=span_text,
                                                                 fontname=span_font,
                                                                 fontsize=(span_size) * scale_factor,
                                                                 text_color=span_color,
                                                                 # fill_color=[1, 1, 1],
                                                                 # align=TEXT_ALIGN_LEFT,
                                                                 rotate=line_rotation)
                            _annot.set_flags(span_flags)
                            _annot.set_opacity(1)
                            _annot.update(rotate=line_rotation, text_color=span_color, fill_color=[1, 1, 1])
                            pass

                        pass

                    #### 未拆分span，直接整个字符串添加
                    # dir_tuple = lines[0]['dir']
                    # # 计算反正切值
                    # # 注意：这里是-dir_tuple[1]， https://pymupdf.readthedocs.io/en/latest/textpage.html#f2
                    # # MuPDF 和 PDF 的坐标系不同，MuPDF 使用页面的左上角点作为 (0, 0)。而在 PDF 中，这是左下点。
                    # # 因此，MuPDF 的 y 轴的正方向是从上至下。这就导致了此处正弦值的符号变化：负值表示文本的逆时针旋转。
                    # angle_radians = math.atan2(-dir_tuple[1], dir_tuple[0])
                    # #
                    # rotation = int(angle_radians * 180 / math.pi)
                    # if rotation < 0:
                    #     rotation = rotation + 360
                    #
                    # # rect = doc.xref_get_key(annot.xref, 'Rect')[1]
                    # styles = None
                    # if 'RC' in keys:
                    #     style_json = doc.xref_get_key(annot.xref, 'RC')[1]
                    #     print('USE RC: ', style_json)
                    #     rc_xml: Element = ET.fromstring(style_json)
                    #     style_nodes = []
                    #     if 'style' in rc_xml.attrib:
                    #         style_nodes.append(rc_xml)
                    #     style_nodes.extend(rc_xml.findall(".//*[@style]"))
                    #     if style_nodes:
                    #         for node in style_nodes:
                    #             styles = get_properties_from_style(node.attrib['style'])
                    # else:
                    #     default_style = doc.xref_get_key(annot.xref, 'DS')[1]
                    #     print('USE DS: ', default_style)
                    #     styles = get_properties_from_style(default_style)
                    # rect = fitz.Rect(annot.rect)
                    # rect = fitz.Rect(rect[0] * scale_factor, rect[1] * scale_factor, rect[2] * scale_factor, rect[3] * scale_factor)
                    # # 复制注释到目标文档中
                    # match annot.type[1]:
                    #     case 'FreeText':
                    #         annot_tbl = PrettyTable(
                    #             ['类型', 'xref', '内容', '方向', '字体名称', '字体大小', '字体颜色', '对齐方式',
                    #              '位置'])
                    #
                    #         annot_tbl.add_row([
                    #             annot.type[1],
                    #             annot.xref,
                    #             content,
                    #             rotation,
                    #             fontname,
                    #             fontsize,
                    #             color,
                    #             styles["text_align"],
                    #             rect
                    #         ])
                    #         print(annot_tbl)
                    # _annot = new_page.add_freetext_annot(rect=rect,
                    #                                      text=content,
                    #                                      fontname=fontname,
                    #                                      fontsize=fontsize,
                    #                                      text_color=color,
                    #                                      fill_color=[1,1,1],
                    #                                      align=styles["text_align"],
                    #                                      rotate=rotation)
                    # # _annot.update(rotate=rotation, text_color= color)
            pass
        target_doc.save('mt_04_24024_0_812--1---annot.pdf', garbage=4, deflate=True)
        doc.close()

    def test_copy_annot2(self):
        # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
        fitz.TOOLS.set_small_glyph_heights(True)
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-01/mt_04_24024_0_812.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-02/mt_04_24024_0_812-2.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-02/mt_04_24024_0_812-wps.pdf')
        # bytes = get_url_content_retry('https://tfile.yj2025.com/pdf-processor/source/2024-04-03/x.pdf')
        bytes = get_url_content_retry('https://file.yj2025.com/工程图纸0940-竖向.pdf')
        target_doc: Document = fitz.open()
        doc = fitz.open('pdf', bytes)
        for index, page in enumerate(doc):
            page.clean_contents()
            _page_rotation = page.rotation
            page.set_rotation(0)
            # 初始化一张A4纸张大小的新页面
            new_page = target_doc.new_page(width=page.cropbox.width, height=page.cropbox.height)

            new_page.show_pdf_page(new_page.cropbox, doc, index, rotate=page.rotation, keep_proportion=True,
                                   clip=page.cropbox)

            for annot_index, annot in enumerate(page.annots(types=[fitz.mupdf.PDF_ANNOT_FREE_TEXT])):
                if annot.type[1] == 'FreeText':
                    blocks = annot.get_textpage().extractDICT()['blocks']
                    for block in blocks:
                        for line in block['lines']:
                            # 书写方向及书写方式（横/竖） 0 = horizontal, 1 = vertical
                            line_wmode = line['wmode']
                            line_rotation = get_text_rotation_from_dir(line['dir'])
                            line_rect = fitz.Rect(line['bbox'][0], line['bbox'][1], line['bbox'][2], line['bbox'][3])
                            for span in line['spans']:
                                span_size = span['size']
                                span_flags = span['flags']
                                span_font = span['font']
                                # span_color = [((span['color'] >> 16) & 255) / 255, ((span['color'] >> 8) & 255) / 255, (span['color'] & 255) / 255]
                                rgb_tuple = fitz.sRGB_to_pdf(span['color'])
                                span_color = [rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]]
                                span_ascender = span['ascender']
                                span_descender = span['descender']
                                span_text = span['text']

                                # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
                                a = span["ascender"]
                                d = span["descender"]
                                o = fitz.Point(span["origin"])
                                r = fitz.Rect(span['bbox'])

                                # 通过设置的旋转角度通过反向计算区域块实际位置
                                # r = r.transform(page.derotation_matrix)

                                _annot = new_page.add_freetext_annot(rect=r,
                                                                     text=span_text,
                                                                     fontname=span_font,
                                                                     fontsize=span_size,
                                                                     text_color=span_color)
                                _annot.set_flags(span_flags)
                                _annot.set_opacity(1)
                                _annot.update(rotate=line_rotation, text_color=span_color, fill_color=[1, 1, 1])
            page.set_rotation(_page_rotation)
            new_page.set_rotation(_page_rotation)
        target_doc.save('xxx.pdf', garbage=4, deflate=True)
        doc.close()
        target_doc.close()

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

    def test_scale(self):
        s_w = 400
        s_h = 210
        t_w = 200
        t_h = 100
        w_scale_factor = t_w / s_w
        h_scale_factor = t_h / s_h
        print(w_scale_factor, h_scale_factor)
        if s_h * w_scale_factor < t_h:
            print('按宽度缩放：', w_scale_factor)
        else:
            print('按高度缩放：', h_scale_factor)
        pass

    def test_ghost(self):
        bytes = httpx.get(
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-07/mt_04_24024_0_812--1.pdf').content
        doc = fitz.open('pdf', bytes)
        for page in doc:
            page.clean_contents()
        doc = fitz.open('pdf', doc.tobytes(garbage=4, clean=True, deflate=True))
        # doc = fitz.open('pdf', doc.convert_to_pdf())
        doc.save('xxx.pdf')

    def test_bakes(self):
        """
        解释：https://github.com/pymupdf/PyMuPDF/discussions/3356
        将注释等转换成页面内容，这样可以使用show_pdf_page 复制这些内容到别的地方
        """
        bytes = httpx.get(
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-07/mt_04_24024_0_812--1.pdf').content
        doc = fitz.open('pdf', bytes)
        for page in doc:
            page.clean_contents()
        pdf = fitz.mupdf.pdf_document_from_fz_document(doc)
        fitz.mupdf.pdf_bake_document(pdf, 1, 1)
        doc.save('xxx.pdf')

    def test_clean_pages(self):
        """
        clean_contents 后导致内容丢失，但是通过mac的 preview.app 可以查看
        """
        files = [
            'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/mt_03_22318er_0_806.pdf',
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-08/丢失大量内容401-020605-00.pdf'
        ]
        docs = []
        for file in files:
            bytes = httpx.get(file).content
            doc = fitz.open('pdf', bytes)
            docs.append(doc)

        from PIL import Image
        img = Image.open(io.BytesIO(
            httpx.get('https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg').content)).convert("RGB")
        img_stream = io.BytesIO()
        img.save(img_stream, format='JPEG')

        rect = [0, 0, 200, 300]

        target_doc = fitz.open()
        for doc in docs:
            for index, page in enumerate(doc):
                print(
                    f'''第{index + 1}页
                                rect cropbox mediabox 是否一致: {page.rect == page.cropbox == page.mediabox}
                                原始矩形宽:{page.cropbox.width}  高:{page.cropbox.height}  旋转角度:{page.rotation}
                                旋转矩阵:{page.rotation_matrix}
                                变换矩阵:{page.transformation_matrix}''')


                # TODO If you use clean_contents, the content of the second page will be lost and the image will not be displayed.
                # page.clean_contents()

                # TODO If wrap_contents is used, it will cause the image on the first page to be displayed in the wrong position
                page.wrap_contents()

                # TODO If both clean_contents and wrap_contents are not used, the first page content will be lost and the image will not be displayed.

                page.insert_image(rect, stream=img_stream, keep_proportion=False, alpha=0, xref=0,
                                  rotate=0)
                new_page = target_doc.new_page(width=page.cropbox.width, height=page.cropbox.height)
                new_page.show_pdf_page(rect=page.cropbox, src=doc, pno=index, keep_proportion=True, rotate=0,
                                       clip=new_page.cropbox)
            doc.close()
        target_doc.save('x.pdf')
        target_doc.close()

    def test_insert_pdf(self):
        """
        内容丢失问题解决
        """
        files = [
            'https://tfile.yj2025.com/pdf-processor/source/2024-03-26/mt_03_22318er_0_806.pdf',
            'https://tfile.yj2025.com/pdf-processor/source/2024-04-08/丢失大量内容401-020605-00.pdf'
        ]
        from PIL import Image
        img = Image.open(io.BytesIO(
            httpx.get('https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg').content)).convert("RGB")
        img_stream = io.BytesIO()
        img.save(img_stream, format='JPEG')

        rect = [0, 0, 200, 300]

        target_doc = fitz.open()
        for file in files:
            bytes = httpx.get(file).content
            doc = fitz.open('pdf', bytes)

            target_doc.insert_pdf(docsrc=doc)

            for index, page in enumerate(target_doc):
                page.insert_image(rect, stream=img_stream, keep_proportion=False, alpha=0, xref=0,
                                  rotate=0)
            doc.close()
        target_doc.save('x.pdf')
        target_doc.close()

    # https://github.com/pymupdf/PyMuPDF/discussions/2384  show_pdf_page 需要按照逆时针旋转
    def test_rotation(self):
        # doc = fitz.open('扫码报工PDF/图档不正确/图档倒转/打开方向正确-打印翻转了180°-20231205-明信达.pdf')
        # doc = fitz.open('扫码报工PDF/图档不正确/竖图/竖图方向不正确-1.pdf')
        doc = fitz.open('扫码报工PDF/图档不正确/竖图/竖图-0度-左侧为底.pdf')
        # doc = fitz.open('扫码报工PDF/图档不正确/竖图/横图-90度.pdf')
        # doc = fitz.open('扫码报工PDF/图档不正确/竖图/竖图右侧-0度.pdf')
        page = doc[0]
        print(page.rotation)
        page.set_rotation(90)
        doc.save('90.pdf')

        result_doc = fitz.open()
        new_page = result_doc.new_page(width=page.cropbox.width, height=page.cropbox.height)
        _rotation = page.rotation
        page.set_rotation(0)
        new_page.show_pdf_page(rect=new_page.cropbox, src=doc, pno=0, keep_proportion=True, rotate=-90, clip=page.cropbox)

        result_doc.save('show_pdf_rotaion_result.pdf')