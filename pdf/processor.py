import concurrent
import os
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from symtable import Function

import qrcode
from fitz import fitz, Font, Document
from qrcode.image.pil import PilImage

from model import Item, File
from pdf import Editor
from support import a4_width, a4_height, header_height, logger, get_url_content_retry, logged, read_bytes_from_file, \
    read_temp_file_instant

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
    """
    针对单个或多个文档处理类
    """

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
        fontsize = 16

        # 序号
        if item.item_no:
            page.insert_text(point=fitz.Point(1754 - 100, 50), text=f'{item.item_no}',
                             fontsize=fontsize,
                             fontname=chn_fontname, color=(30 / 255, 144 / 255, 255 / 255))

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
        page.insert_text(point=fitz.Point(680, 50), text=f'货品编码: {item.inventory_code}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(680, 100), text=f'数量: {item.quantity}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))

        # 第三列
        page.insert_text(point=fitz.Point(1080, 50), text=f'货品名称: {item.inventory_name}',
                         fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
        page.insert_text(point=fitz.Point(1080, 100), text=f'规格型号: {item.inventory_spec}',
                         fontsize=fontsize,
                         fontname=chn_fontname, color=(0, 0, 0))

        return header_doc

    @logged(desc='处理单个item_doc')
    def generate_from_item_without_close(self, item: Item) -> Document:
        """
        生成独立包含header和原页面的文档
        :param item: 生成需要的当前header头信息，并且包含的多个源文档files
        :return:
        """
        target_item_doc = fitz.open()
        # 每个item的头部区域pdf
        header_doc: Document = self.generate_header_doc_without_close(item)
        for file in item.files:

            #### 内部逻辑处理与 `generate_from_file_without_close` 方法处理逻辑保持一致 begin
            editor: Editor = Editor(file.data, False)
            rotations = editor.get_horizontal_transform_rotations(file.rotations)
            editor.clean_pages()
            if file.marks and len(file.marks) > 0:
                # 添加遮罩区域
                editor.wrap_doc_with_marks(rotations, file.zoom, file.marks)
            source_file_doc = editor.get_doc_without_close()
            #### 内部逻辑处理与 `generate_from_file_without_close` 方法处理逻辑保持一致 end

            # 合并到target_doc, 因为 rotations要复用，避免多次获取，所以上面file处理不复用`generate_from_file_without_close`
            self.wrap_target_doc_with_header(rotations, source_file_doc, header_doc, target_item_doc)
        header_doc.close()
        return target_item_doc

    @logged(desc='处理单个文档加遮罩')
    def generate_bytes_from_file(self, file: File) -> bytes:
        """
        单文档处理(该方法不复用),如果不涉及到字体添加，则不压缩
        :param file: 单个pdf文档
        :return:
        """
        editor: Editor = Editor(file.data, False)
        rotations = editor.get_horizontal_transform_rotations(file.rotations)
        editor.clean_pages()
        if file.marks and len(file.marks) > 0:
            # 添加遮罩区域
            editor.wrap_doc_with_marks(rotations, file.zoom, file.marks)
        source_file_doc = editor.get_doc_without_close()
        return self.get_doc_bytes_and_close(source_file_doc, auto_close=False)

    @logged(desc='合并头内容和源内容到新页面')
    def wrap_target_doc_with_header(self, rotations: list[float], source_file_doc: Document, header_doc: Document,
                                    target_doc: Document) -> None:
        """
        将头内容和源内容合并到target_doc文件中
        :param rotations: 源文件的旋转角度集合
        :param header_doc: 头文件
        :param target_doc: 目标文件
        :return:
        """
        for p_index, source_page in enumerate(source_file_doc):
            # 所以需要在二次转化前记录之前每页的旋转角度，并转换后再设置进去, 这里不可删除
            new_page = target_doc.new_page(width=a4_width, height=a4_height)
            # 顶部区域
            r1 = fitz.Rect(0, 0, a4_width, header_height)
            # 下部区域
            r2 = fitz.Rect(0, header_height, a4_width, a4_height)
            # 将header-pdf首页贴到顶部区域
            new_page.show_pdf_page(r1, header_doc, 0)
            # 记录原来的旋转角度
            _source_page_rotation = source_page.rotation
            # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
            source_page.set_rotation(0)
            new_page.show_pdf_page(r2, source_file_doc, p_index, rotate=rotations[p_index], keep_proportion=True,
                                   clip=source_page.cropbox)
            # 还原旋转角度
            source_page.set_rotation(_source_page_rotation)
            # usage_pdf.save('333.pdf')

    # @logged(desc='生成pdf文件的字节数组,并关闭文档已打开的句柄')
    def get_doc_bytes_and_close(self, doc: Document, auto_close: bool = True) -> bytes:
        """
        生成pdf文件的字节数组,并关闭文档已打开的句柄
        :param doc: 文档
        :param auto_close: 是否使用完自动关闭文档,如果是reader/editor对象返回的doc可以为False，因为实例消亡，文档会自动关闭
        :return:
        """

        # 不建议直接转二进制，会出现一些莫名其妙的问题
        # pdf_bytes = doc.convert_to_pdf()

        # https://pymupdf.readthedocs.io/en/latest/document.html#Document.save
        def write_file_path(filepath: str):
            doc.save(filepath, garbage=3, deflate=True)
            if auto_close:
                doc.close()

        pdf_bytes = read_temp_file_instant(write_file_path)
        return pdf_bytes

    @logged(desc='并发下载请求的多个item的多个文件')
    def wrap_file_data_for_items(self, items: list[Item]) -> None:
        """
        批量从请求的items中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for item in items:
                for f_index, file in enumerate(item.files):
                    future = pool.submit(self.wrap_file_data_for_file, file)
                    futures.append(future)
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}个文件')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                pass
        pass

    @logged(desc='并发下载请求的多个File的多个文件')
    def wrap_file_data_for_files(self, files: list[File]) -> None:
        """
        批量从请求的files中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for file in files:
                future = pool.submit(self.wrap_file_data_for_file, file)
                futures.append(future)
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}个文件')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                pass
        pass

    # @logged(desc='下载单个pdf文件')
    def wrap_file_data_for_file(self, file: File) -> None:
        """
        下载单个pdf文件
        :param file:
        :return:
        """
        file.data = get_url_content_retry(file.url, 5)
        pass

    def compress_doc(self, doc: Document) -> None:
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
    def merge_and_compress_docs(self, item_docs: list[Document], is_item_doc_close: bool = True) -> Document:
        """
        合并多个文档并压缩
        :param item_docs: 多个子文档
        :param is_item_doc_close: 是否关闭子文档
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
        return target_doc

    @logged(desc='通过多个items处理成一个结果文档')
    def generate_from_items_without_close(self, items: list[Item], item_call: Function = None) -> Document:
        """
        通过多个items处理成一个结果文档
        :param items: item任务列表
        :param item_call: 单个item处理完回调: `item_call(item_index, result, exception)`
        :return: result_doc
        """
        if not item_call:
            def _item_call(item_index, item_doc, exception):
                pass

            item_call = _item_call

        s_time = int(time.perf_counter() * 1000)
        file_count = 0
        # 并发下载文件,否则无法使用`file.byte_array`
        self.wrap_file_data_for_items(items)
        item_docs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for item in items:
                file_count += len(item.files)
                # 如果是测试 传入string则增加不同item之间的批次号
                item.wrap_batch_number_when_qr_string()
                # 开始多线程处理
                future = pool.submit(self.generate_from_item_without_close, item)
                futures.append(future)
            # 处理进度
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                pass
            # 按原始顺序添加页
            for index, future in enumerate(futures):
                exception = future.exception()
                if exception:
                    item_call(index, None, exception)
                    raise exception
                else:
                    result = future.result()
                    item_docs.append(result)
                    item_call(index, result, None)
        print(
            f'=======================================> 【{file_count}个pdf文件处理完毕】 耗时: {int(time.perf_counter() * 1000) - s_time}/ms <=======================================')
        target_doc = self.merge_and_compress_docs(item_docs)
        return target_doc
