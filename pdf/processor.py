import concurrent
import os
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import qrcode
from fitz import fitz, Font, Document
from qrcode.image.pil import PilImage
from tqdm import tqdm

from model import Item, File
from pdf import Editor
from pdf import Reader
from support import a4_width, header_height, logger, log_time, get_url_content_retry

debugger = False

# 文件下载线程池
download_executor = ThreadPoolExecutor(max_workers=200)


class Processor(object):

    def __init__(self):
        """
        初始化处理器
        :param header_height:
        """
        self.current_file_path = os.path.abspath(os.path.dirname(__file__))

    @log_time
    def generate_header_doc_without_close(self, item: Item) -> Document:
        """
        生成header头信息pdf对象
        :param item: 生成需要的当前header头信息
        :return:
        """
        header_doc = fitz.open()
        page = header_doc.new_page(width=a4_width, height=header_height)
        img: PilImage = qrcode.make(data=item.qr_code)
        imagefile = BytesIO()
        img.save(imagefile)

        # page.insert_image(
        #     rect=fitz.Rect(10, 10, 200, 200),
        #     filename=os.path.join(self.current_file_path, 'logo', 'logo20220210-01.png'), overlay=False)

        # 二维码: 左上角坐标 80、10、宽高统一180
        page.insert_image(
            rect=fitz.Rect(80, 10, 280,
                           10 + header_height),
            stream=imagefile,
            overlay=False)

        # ms宋体下载: https://www.fontsaddict.com/font/ms-song.html
        # 其他字体下载: http://www.ae-sys.com/China/Fonts/
        # page.insert_font(fontname=chn_fontname,
        #                  fontfile=os.path.join(self.current_file_path, 'fonts', 'ms-song.ttf'))

        chn_fontname = 'chn'
        # https://pymupdf.readthedocs.io/en/latest/font.html#Font
        # 1. 使用默认嵌入字体，pdf大小最优,缺点: 中文支持不太好
        # 2. 使用第三方字体库, `pip install pymupdf-fonts` 大小一般, 缺点: 中文支持不够
        # 3. 手动安装字体,但是需要创建字体子集来减少字体大小。创建子集需要安装第三方库`pip install fonttools` (这里选用该方法, 中文支持较好)
        #   3.1. 参考: https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
        font = Font(fontname=chn_fontname,
                    fontfile=os.path.join(self.current_file_path, 'fonts', 'FangZhengHeiTiJianTi-1.ttf'),
                    language='zh-Hans')
        # https://pymupdf.readthedocs.io/en/latest/page.html#Page.insert_font
        page.insert_font(fontname=chn_fontname,
                         fontbuffer=font.buffer)

        # 字体大小
        fontsize = 20
        # 第一列
        page.insert_text(point=fitz.Point(280, 50), text=f'工单号: {item.doc_no}',
                         fontsize=fontsize,
                         fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(280, 100), text=f'交期: {item.doc_date}',
                         fontsize=fontsize,
                         fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(280, 150), text=f'工艺路线: {item.process_flow}',
                         fontsize=fontsize,
                         fontname=chn_fontname, color=(0, 0, 0))

        # 第二列
        page.insert_text(point=fitz.Point(580, 50), text=f'货品编码: {item.inventory_code}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(580, 100), text=f'数量: {item.quantity}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))

        # 第三列
        page.insert_text(point=fitz.Point(900, 50), text=f'货品名称: {item.inventory_name}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(900, 100), text=f'规格型号: {item.inventory_spec}',
                         fontsize=fontsize,
                         fontname=chn_fontname, color=(0, 0, 0))

        # # 创建字体的子集，减少文档大小
        # # https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
        # header_doc.subset_fonts()

        if debugger:
            folder = os.path.join(self.current_file_path, 'tmp')
            if not os.path.exists(folder):
                os.makedirs(folder)
            header_doc.save(os.path.join(folder, f"header-{int(time.time())}.pdf"))
        return header_doc
        # pdf_bytes = doc.convert_to_pdf()
        # return pdf_bytes

    def generate_item_doc_without_close(self, item: Item) -> Document:
        """
        生成独立包含header和原页面的文档
        :param item: 生成需要的当前header头信息，并且包含的多个源文档files
        :return:
        """
        target_item_doc = fitz.open()
        # 每个item的头部区域pdf
        header_doc: Document = self.generate_header_doc_without_close(item)
        for file in item.files:
            self.wrap_pdf_with_header(file, header_doc, target_item_doc)
        header_doc.close()
        return target_item_doc

    def wrap_pdf_with_header(self, file: File, header_doc: Document, target_doc: Document):
        """
        将file和 headerdoc 合并成一个新的页面
        :param file: 源文件
        :param header_doc: 头文件
        :param target_doc: 目标文件
        :return:
        """
        source_editor: Editor = self.create_editor(file)
        # 合并到target_doc
        source_editor.wrap_pdf_with_header(file, header_doc, target_doc)

    def create_reader(self, bytes: bytes) -> Reader:
        """
        创建一个pdf文件读取器
        对象销毁的时候会自动关闭文件打开的句柄
        :param bytes: pdf文件内容字节数组
        :return:
        """
        reader = Reader(bytes)
        return reader

    def create_editor(self, bytes: bytes) -> Editor:
        """
        创建一个pdf文件编辑器(包含查看器功能)
        对象销毁的时候会自动关闭文件打开的句柄
        :param bytes: pdf文件内容字节数组
        :return:
        """
        editor = Editor(bytes)
        return editor

    def get_doc_bytes_and_close(self, doc: Document):
        """
        生成pdf文件的字节数组,并关闭文档已打开的句柄
        :return:
        """
        try:
            # 创建字体的子集，减少文档大小 Package fontTools must be installed `pip install fonttools`
            # https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
            doc.subset_fonts()
        except BaseException as err:
            logger.warn(f'文档创建字体子集: {repr(err)}')
        pdf_bytes = doc.convert_to_pdf()
        # pdf_bytes = read_temp_file_instant(lambda x: doc.save(x))
        doc.close()
        return pdf_bytes

    @log_time
    def wrap_file_bytes_for_items(self, items: list[Item]):
        """
        批量从请求的items中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for item in items:
                for f_index, file in enumerate(item.files):
                    future = pool.submit(self.wrap_file_bytes_for_file, file)
                    futures.append(future)
            process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}个文件')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                process_bar.update(1)
                pass
        pass

    def wrap_file_bytes_for_file(self, file: File):
        file.byte_array = get_url_content_retry(file.url, 5)
        pass
