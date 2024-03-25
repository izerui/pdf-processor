import concurrent
import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import qrcode
from fitz import fitz, Font, Document
from qrcode.image.pil import PilImage

from model import Item, File
from pdf import Editor
from pdf import Reader
from support import a4_width, header_height, logger, get_url_content_retry, logged, read_bytes_from_file

debugger = False

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

font_buffer = read_bytes_from_file(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fonts', 'FangZhengHeiTiJianTi-1.ttf'))

font = Font(fontname=chn_fontname,
            fontbuffer=font_buffer,
            language='zh-Hans')


class Processor(object):

    def __init__(self):
        """
        初始化处理器
        :param header_height:
        """
        self.current_file_path = os.path.abspath(os.path.dirname(__file__))

    @logged(desc='生成header头信息pdf对象')
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

        return header_doc

    @logged(desc='处理单个item_doc')
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
            source_editor: Editor = self.create_editor(file.byte_array, True)
            if file.marks and len(file.marks) > 0:
                # 添加遮罩区域
                source_editor.wrap_doc_with_marks(file.zoom, file.marks)
            # 合并到target_doc
            source_editor.wrap_target_doc_with_header(file.rotations, header_doc, target_item_doc)
            source_editor.close()
        header_doc.close()
        return target_item_doc

    @logged(desc='初始化一个pdf文件读取器')
    def create_reader(self, bytes: bytes, is_rewrap: bool) -> Reader:
        """
        初始化一个pdf文件读取器
        对象销毁的时候会自动关闭文件打开的句柄
        :param is_rewrap: 是否针对文档进行二次包装处理
        :param bytes: pdf文件内容字节数组
        :return:
        """
        reader = Reader(bytes, is_rewrap)
        return reader

    @logged(desc='初始化源pdf文件编辑器实例')
    def create_editor(self, bytes: bytes, is_rewrap: bool) -> Editor:
        """
        初始化一个pdf文件编辑器(包含查看器功能)
        对象销毁的时候会自动关闭文件打开的句柄
        :param is_rewrap: 是否针对文档进行二次包装处理
        :param bytes: pdf文件内容字节数组
        :return:
        """
        editor = Editor(bytes, is_rewrap)
        return editor

    # @logged(desc='生成pdf文件的字节数组,并关闭文档已打开的句柄')
    def get_doc_bytes_and_close(self, doc: Document):
        """
        生成pdf文件的字节数组,并关闭文档已打开的句柄
        :return:
        """
        pdf_bytes = doc.convert_to_pdf()
        # pdf_bytes = read_temp_file_instant(lambda x: doc.save(x) and doc.close())
        return pdf_bytes

    @logged(desc='并发下载请求的多个item的多个文件')
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
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}个文件')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                pass
        pass

    @logged(desc='批量从请求的files的url列表中下载文件并补全到bytes_array中')
    def wrap_file_bytes_for_files(self, files: list[File]):
        """
        批量从请求的files中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for file in files:
                future = pool.submit(self.wrap_file_bytes_for_file, file)
                futures.append(future)
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}个文件')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                pass
        pass

    # @logged(desc='下载单个pdf文件')
    def wrap_file_bytes_for_file(self, file: File):
        """
        下载单个pdf文件
        :param file:
        :return:
        """
        file.byte_array = get_url_content_retry(file.url, 5)
        pass

    def compress_doc(self, doc: Document):
        """
        创建字体的子集，减少文档大小，前提必须在主线程中调用,否则会导致文件找不到异常
        参考：https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
        :param doc:
        :return:
        """
        # TODO 考虑使用本地文件做进程间全局锁
        for _ in range(5):
            try:
                doc.subset_fonts()
                return
            except Exception:
                logger.warn(f'压缩文档处理进程冲突: 第{_}次')
                continue
        logger.warn(f'5次重试未成功压缩!')

    @logged(desc='压缩合并多个item文档到一个结果文档')
    def get_bytes_by_merge_and_compress_docs(self, item_docs: list[Document], is_item_doc_close: bool = True):
        """
        合并多个文档并压缩
        :param docs: 多个文档
        :return: 一个文档
        """
        target_doc = fitz.open()
        for item_doc in item_docs:
            # 先压缩item文档
            self.compress_doc(item_doc)
            # 每个item生成独立的document，然后插入到target中
            target_doc.insert_pdf(docsrc=item_doc)
            if is_item_doc_close:
                item_doc.close()
        # 再次压缩结果文档
        self.compress_doc(target_doc)
        return self.get_doc_bytes_and_close(target_doc)
