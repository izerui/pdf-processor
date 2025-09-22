import concurrent
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from symtable import Function
from typing import Callable

import pymupdf
from pymupdf import Document, TEXT_ALIGN_LEFT, Page
from pymupdf.mupdf import PDF_PERM_PRINT, PDF_PERM_ACCESSIBILITY
from tqdm import tqdm

from model import Item, File, ItemRender
from pdf import Editor
from support import a4_width, a4_height, header_height, logger, get_url_content_retry, logged, \
    get_text_rotation_from_dir, get_page_rect_unrotate

# ms宋体下载: https://www.fontsaddict.com/font/ms-song.html
# 其他字体下载: http://www.ae-sys.com/China/Fonts/
# page.insert_font(fontname=chn_fontname,
#                  fontfile=os.path.join(self.current_file_path, 'fonts', 'ms-song.ttf'))

# chn_fontname = 'chn'
# # https://pymupdf.readthedocs.io/en/latest/font.html#Font
# # 1. 使用默认嵌入字体，pdf大小最优,缺点: 中文支持不太好
# # 2. 使用第三方字体库, `pip install pymupdf-fonts` 大小一般, 缺点: 中文支持不够
# # 3. 手动安装字体,但是需要创建字体子集来减少字体大小。创建子集需要安装第三方库`pip install fonttools` (这里选用该方法, 中文支持较好)
# #   3.1. 参考: https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
#
# font_buffer = read_bytes_from_file(
#     os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fonts', 'FangZhengHeiTiJianTi-1.ttf'))
#
# font = Font(fontname=chn_fontname,
#             fontbuffer=font_buffer,
#             language='zh-Hans')

# arch_fonts = pymupdf.Archive(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fonts'))

header_meta = __import__('pdf.header', globals(), locals(),
                         ['IHeader', 'Header331', 'Header221', 'Header222', 'Header333', 'Header441', 'Header551'])

alphabeticals = ['Γ', 'Δ', 'Θ', 'Ξ', 'Π', 'Ψ', 'Ω', 'α', 'β', 'γ', 'δ', 'θ', 'λ', 'μ', 'π', 'ρ', 'φ', 'χ', 'ω']


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

    @logged(desc='处理单个item_doc')
    def generate_from_item_without_close(self,
                                         index: int,
                                         item: Item,
                                         url_datas: dict,
                                         item_callback: Function = None) -> Document:
        """
        生成独立包含header和原页面的文档
        :param index: item的索引
        :param item: 生成需要的当前header头信息，并且包含的多个源文档files
        :param url_datas: url_data 对照表
        :param item_callback: 成功与失败回调
        :return:
        """
        try:
            header_doc = None
            if item.header_show and item.header_show == 'true':
                header_doc = self.generate_header_doc_without_close(item)
            target_item_doc = pymupdf.open()
            for file in item.files:

                #### 内部逻辑处理与 `generate_from_file_without_close` 方法处理逻辑保持一致 begin
                editor: Editor = Editor(url_datas[file.url], False)
                rotations = editor.get_horizontal_transform_rotations(file.rotations)
                editor.clean_pages()
                # editor.clone_doc_for_self()
                editor.bake_document()
                if file.marks and len(file.marks) > 0:
                    # 添加遮罩区域
                    editor.wrap_doc_with_marks(rotations, file.zoom, file.marks, url_datas)
                source_file_doc = editor.get_doc_without_close()
                # source_file_doc.ez_save('1111.pdf')
                #### 内部逻辑处理与 `generate_from_file_without_close` 方法处理逻辑保持一致 end
                # source_file_doc.page_xref(0)
                # source_file_doc.get_page_images()

                is_top = True
                if item.header_layout and item.header_layout == 'bottom':
                    is_top = False
                # 合并到target_doc, 因为 rotations要复用，避免多次获取，所以上面file处理不复用`generate_from_file_without_close`
                self.wrap_target_doc_with_header(rotations, source_file_doc, header_doc, target_item_doc, is_top)
                # 将源文件页面的注释原样copy到target_item_doc中
                # self.wrap_target_doc_with_annot(rotations, editor.generate_annot_doc_without_close(), target_item_doc)
                # self.wrap_target_doc_with_source_annots(rotations, source_file_doc, target_item_doc)
            if header_doc:
                header_doc.close()
            if item_callback:
                item_callback(index, item, target_item_doc, None)
            return target_item_doc
        except BaseException as err:
            logger.exception(err)
            if item_callback:
                item_callback(index, item, None, err)
            raise err

    @logged(desc='生成单个header头信息pdf对象(包括生成和压缩)')
    def generate_header_doc_without_close(self, item: Item) -> Document:
        """
        生成header头信息pdf对象
        :param item: 生成需要的当前header头信息
        :return:
        """
        # 每个item对应的header头文档集合
        header_doc = pymupdf.open()
        contains_latin = self._generate_header_page(item, header_doc)
        header_doc = self.subset_doc_and_return_new_doc(header_doc, contains_latin)
        return header_doc

    @logged(desc='生成多个header头信息pdf对象,暂时不用')
    def generate_headers_doc_without_close(self, items: list[Item]) -> Document:
        """
        生成headers头信息pdf对象
        :param items: 生成需要的当前header头信息集合
        :return:
        """
        # 每个item对应的header头文档集合
        header_doc = pymupdf.open()
        process_bar = tqdm(total=len(items), desc=f'生成header文档,共{len(items)}个页面.')
        # 是否存在特殊拉丁字符
        contains_latin = False
        for index, item in enumerate(items):
            _latin = self._generate_header_page(item, header_doc)
            if _latin:
                contains_latin = True
            process_bar.update(1)
        header_doc = self.subset_doc_and_return_new_doc(header_doc, contains_latin)
        return header_doc

    def _generate_header_page(self, item: Item, header_doc: Document) -> None:
        """
        生成header头信息pdf对象
        :param item: 生成需要的当前header头信息
        :return: 是否包含特殊的拉丁字符
        """
        # 通过名称动态加载类并执行
        header_class_meta = getattr(header_meta, item.header_model)
        header = header_class_meta(header_doc, item)
        header.generate_header_page()
        item_attrs = vars(item)
        # 交集
        intersection = False
        for attr in item_attrs:
            if intersection:
                break
            item_value = item_attrs[attr]
            if isinstance(item_value, ItemRender):
                item_chars = list(item_value.value)
                intersection = set(item_chars) & set(alphabeticals)
        return True if intersection else False

    @logged(desc='处理单个文档加遮罩并返回处理后的源文档')
    def generate_source_bytes_from_file(self, file: File, url_datas: dict) -> bytes:
        """
        单文档处理(该方法不复用),如果不涉及到字体添加，则不压缩
        :param file: 单个pdf文档
        :param url_datas: url_data对照表
        :return:
        """
        editor: Editor = Editor(url_datas[file.url], False)
        rotations = editor.get_horizontal_transform_rotations(file.rotations)
        editor.clean_pages()
        # editor.clone_doc_for_self()
        editor.bake_document()
        if file.marks and len(file.marks) > 0:
            # 添加遮罩区域
            editor.wrap_doc_with_marks(rotations, file.zoom, file.marks, url_datas)
        source_file_doc = editor.get_doc_without_close()
        return self.get_doc_bytes_and_close(source_file_doc, auto_close=False)

    @logged(desc='合并头内容和源内容到新页面')
    def wrap_target_doc_with_header(self, rotations: list[float], source_file_doc: Document, header_doc: Document,
                                    target_doc: Document, is_top: bool = True) -> None:
        """
        将头内容和源内容合并到target_doc文件中
        :param rotations: 源文件的旋转角度集合
        :param source_file_doc: 源文件
        :param header_doc: 头文件
        :param target_doc: 目标文件
        :return:
        """

        if not header_doc:
            target_doc.insert_pdf(docsrc=source_file_doc)
            return

        for p_index, source_page in enumerate(source_file_doc):
            # pymupdf.Matrix()
            # 有时会遇到 cropbox 和 rect 不一致的问题。cropbox 是 PDF 页面上显示的区域，而 rect 是页面的实际尺寸。故下面的注释代码只是参考
            # bottom_rect = source_page.cropbox.transform(page.derotation_matrix)
            if is_top:
                # 所以需要在二次转化前记录之前每页的旋转角度，并转换后再设置进去, 这里不可删除
                new_page: Page = target_doc.new_page(width=a4_width, height=a4_height)
                # 顶部header区域
                r1 = pymupdf.Rect(0, 0, a4_width, header_height)
                # 下部区域
                r2 = pymupdf.Rect(0, header_height, a4_width, a4_height)
                # 将header-pdf首页贴到顶部区域
                new_page.show_pdf_page(r1, header_doc, 0)
                # 记录原来的旋转角度
                _source_page_rotation = source_page.rotation
                # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
                source_page.set_rotation(0)
                # 这里将rotate按逆时针旋转指定度数,暂时有点疑惑(理论上如果是竖图,以后侧为底,-90度翻转为正确的横图)
                # 参考： https://github.com/pymupdf/PyMuPDF/discussions/2384
                new_page.show_pdf_page(r2, source_file_doc, p_index, rotate=-rotations[p_index], keep_proportion=True,
                                       clip=get_page_rect_unrotate(source_page))
                # 还原旋转角度
                source_page.set_rotation(_source_page_rotation)
            else:
                # 所以需要在二次转化前记录之前每页的旋转角度，并转换后再设置进去, 这里不可删除
                new_page = target_doc.new_page(width=a4_width, height=a4_height)
                # 上部区域
                r1 = pymupdf.Rect(0, 0, a4_width, a4_height - header_height)
                # 下部header区域
                r2 = pymupdf.Rect(0, a4_height - header_height, a4_width, a4_height)
                # 记录原来的旋转角度
                _source_page_rotation = source_page.rotation
                # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
                source_page.set_rotation(0)
                # 这里将rotate按逆时针旋转指定度数,暂时有点疑惑(理论上如果是竖图,以后侧为底,-90度翻转为正确的横图)
                # 参考： https://github.com/pymupdf/PyMuPDF/discussions/2384
                new_page.show_pdf_page(r1, source_file_doc, p_index, rotate=-rotations[p_index], keep_proportion=True,
                                       clip=get_page_rect_unrotate(source_page))
                # 还原旋转角度
                source_page.set_rotation(_source_page_rotation)

                # 将header-pdf首页贴到顶部区域
                new_page.show_pdf_page(r2, header_doc, 0)

            # usage_pdf.save('333.pdf')

    @logged(desc='将注释的蒙版页面复制到bottom区域')
    def wrap_target_doc_with_annot(self, rotations: list[float], annot_doc: Document, target_item_doc: Document):
        """
        将源文件页面的注释原样copy到target_item_doc中
        """
        # 下部区域
        r2 = pymupdf.Rect(0, header_height, a4_width, a4_height)
        for p_index, target_page in enumerate(target_item_doc):
            annot_page = annot_doc[p_index]
            _annot_page_rotation = annot_page.rotation
            annot_page.set_rotation(0)
            target_page.show_pdf_page(r2, annot_doc, p_index, rotate=rotations[p_index], keep_proportion=True,
                                      clip=annot_page.rect)
            annot_page.set_rotation(_annot_page_rotation)

    @logged(desc='复制源页面的注释内容到bottom区域')
    def wrap_target_doc_with_source_annots(self, rotations: list[float], source_file_doc, target_item_doc):
        """
        将源文件页面的注释原样copy到target_item_doc中
        """
        try:
            # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
            pymupdf.TOOLS.set_small_glyph_heights(True)
            # 下部区域
            r2 = pymupdf.Rect(0, header_height, a4_width, a4_height)
            for index, page in enumerate(source_file_doc):
                # 这里一定要先将原始页面角度设置为0，否则注释的字体方向不是以0为参考基准，因为之前合并到bottom区域的时候都是先设置原始页面为0再复制过去的
                _rotation = page.rotation
                page.set_rotation(0)
                annots = list(page.annots(types=[pymupdf.mupdf.PDF_ANNOT_FREE_TEXT, pymupdf.mupdf.PDF_ANNOT_LINE]))
                # print(doc.xref_object(page.xref))
                if len(annots) < 0:
                    continue
                # target_item_doc的新页面
                new_page = target_item_doc[index]

                # 计算缩放因子(针对target_item_doc的底部区域)
                h_scale_factor = r2.width / page.rect.width
                v_scale_factor = r2.height / page.rect.height
                scale_factor = min(h_scale_factor, v_scale_factor)
                # 以宽度为准进行等比例缩放
                is_h_scale_factor = h_scale_factor == scale_factor

                # print(rotations[index], is_h_scale_factor, scale_factor * page.cropbox.width,
                #       scale_factor * page.cropbox.height)

                # 页面复制是居中，故需要计算源页面到新的区域的适配方式
                # 如果以宽度来适配，则需要计算y轴的偏移量
                # 如果以高度来适配，则需要计算x轴的偏移量
                x_offset = 0
                y_offset = 0
                if not is_h_scale_factor:
                    x_offset = (r2.width - scale_factor * page.rect.width) / 2
                else:
                    y_offset = (r2.height - scale_factor * page.rect.height) / 2

                # 测试用，将原图贴过来
                # new_page.show_pdf_page(r2, source_file_doc, index, rotate=rotations[index], keep_proportion=True,
                #                        clip=page.cropbox)
                for annot_index, annot in enumerate(annots):
                    print('\r\t')
                    # print(source_file_doc.xref_object(annot.xref))
                    # print('Remote Control:', source_file_doc.xref_get_key(annot.xref, 'RC'))
                    # print('Default Style:', source_file_doc.xref_get_key(annot.xref, 'DS'))
                    if annot.type[1] == 'FreeText':
                        blocks = annot.get_textpage().extractDICT()['blocks']
                        for block in blocks:
                            lines = block['lines']
                            # 拆分后按每个span进行添加
                            for line in lines:
                                # 书写方向及书写方式（横/竖） 0 = horizontal, 1 = vertical
                                line_wmode = line['wmode']
                                line_rotation = get_text_rotation_from_dir(line['dir'])
                                line_rect = pymupdf.Rect(line['bbox'][0], line['bbox'][1], line['bbox'][2],
                                                         line['bbox'][3])
                                # line_rect = line_rect.transform(pymupdf.Matrix(1, 0, 0, 1, 0, 0).prerotate(90))
                                for span in line['spans']:
                                    span_size = span['size']
                                    span_flags = span['flags']
                                    span_font = span['font']
                                    # span_color = [((span['color'] >> 16) & 255) / 255, ((span['color'] >> 8) & 255) / 255, (span['color'] & 255) / 255]
                                    rgb_tuple = pymupdf.sRGB_to_pdf(span['color'])
                                    span_color = [rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]]
                                    span_ascender = span['ascender']
                                    span_descender = span['descender']
                                    span_text = span['text']

                                    # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
                                    a = span["ascender"]
                                    d = span["descender"]
                                    o = pymupdf.Point(span["origin"])
                                    r = pymupdf.Rect(span['bbox'])

                                    # 如果区域高度不足以包含字体的大小，则把字体大小设置为rect的高度
                                    if r.height < span_size:
                                        span_size = r.height

                                    # rect 区域向外部区域延伸的数值
                                    x0_outer_extend = 2
                                    y0_outer_extend = 2
                                    x1_outer_extend = 2
                                    y1_outer_extend = 2

                                    # 源注释的span区域在新页面的区域位置，除了偏移量，向外延伸，还要考虑header头区域的高度
                                    r = pymupdf.Rect(r[0] * scale_factor + x_offset - x0_outer_extend,
                                                     r[1] * scale_factor + y_offset - y0_outer_extend + header_height,
                                                     r[2] * scale_factor + x_offset + x1_outer_extend,
                                                     r[3] * scale_factor + y_offset + y1_outer_extend + header_height)

                                    # r = r.transform(pymupdf.Matrix(1, 0, 0, 1, 0, 0).prerotate(180))
                                    # print('line rotation: ', line_rotation)
                                    _annot = new_page.add_freetext_annot(rect=r,
                                                                         text=span_text,
                                                                         fontname=span_font,
                                                                         fontsize=(span_size) * scale_factor,
                                                                         text_color=span_color,
                                                                         align=TEXT_ALIGN_LEFT)
                                    _annot.set_flags(span_flags)
                                    _annot.set_opacity(1)
                                    _annot.update(rotate=line_rotation, text_color=span_color, fill_color=[1, 1, 1])
                    elif annot.type[1] == 'Line':
                        annot_pixmap = annot.get_pixmap(alpha=True)
                        r = annot.rect
                        # 源注释的span区域在新页面的区域位置，除了偏移量，向外延伸，还要考虑header头区域的高度
                        r = pymupdf.Rect(r[0] * scale_factor + x_offset,
                                         r[1] * scale_factor + y_offset + header_height,
                                         r[2] * scale_factor + x_offset,
                                         r[3] * scale_factor + y_offset + header_height)
                        # 跟随页面旋转角度进行旋转，否则图片方向不对
                        new_page.insert_image(r, pixmap=annot_pixmap, keep_proportion=True, alpha=0, xref=0,
                                              rotate=rotations[index])
                        pass
                page.set_rotation(_rotation)
        except BaseException as err:
            logger.exception(err)

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
            doc.save(filepath, garbage=4, deflate=True, use_objstms=1)

        # 对象流提供额外的压缩效果 https://github.com/pymupdf/PyMuPDF/discussions/3383
        try:
            logger.info(f'【压缩转换doc文件到字节数组】')
            pdf_bytes = doc.tobytes(garbage=4, deflate=True, use_objstms=1, permissions=PDF_PERM_ACCESSIBILITY | PDF_PERM_PRINT)
            # pdf_bytes = read_temp_file_instant(write_file_path)
            if auto_close:
                doc.close()
            return pdf_bytes
        except BaseException as err:
            logger.exception(err)
            raise err

    def download_urls_from_items(self, items: list[Item], item_error_callback: Callable[[str, object, Exception], None] = None):
        """
        批量从请求的items中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        urls = []
        url_owner_map = {}
        for item in items:
            for file in item.files:
                assert file.url, f'{file.name} 的url不能为空!'
                if file.url not in urls:
                    urls.append(file.url)
                    url_owner_map[file.url] = item
                if file.marks:
                    for mark in file.marks:
                        if mark.image_url and mark.image_url not in urls:
                            urls.append(mark.image_url)
                            url_owner_map[mark.image_url] = item
        return self.download_urls(urls, url_owner_map = url_owner_map, owner_error_callback=item_error_callback)

    def download_urls_from_files(self, files: list[File]):
        """
        批量从请求的items中所有的文件url地址，以多线程的形式下载文件，并补全到bytes_array
        :param items:
        :return:
        """
        urls = []
        for file in files:
            assert file.url, f'{file.name} 的url不能为空!'
            if file.url not in urls:
                urls.append(file.url)
            if file.marks:
                for mark in file.marks:
                    if mark.image_url and mark.image_url not in urls:
                        urls.append(mark.image_url)
        return self.download_urls(urls)

    @logged(desc='批量下载网络文件及图片')
    def download_urls(self, urls: list[str], url_owner_map: object = None, owner_error_callback: Callable[[str, object, Exception], None] = None):

        def append_url_data(url: str, url_datas: dict, owner: object = None):
            try:
                data = get_url_content_retry(url)
                if url not in url_datas:
                    url_datas[url] = data
            except BaseException as err:
                return url, owner, err

        url_datas = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for url in urls:
                if url_owner_map and len(url_owner_map) > 0:
                    owner = url_owner_map[url]
                else:
                    owner = None
                futures.append(pool.submit(append_url_data, url, url_datas, owner))
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                result = future.result()
                if result:
                    url, owner, exception = result
                    if exception:
                        if owner_error_callback:
                            owner_error_callback(url, owner, exception)
                        logger.exception(exception)
                        raise exception
                pass
        return url_datas

    @logged(desc='压缩并返回新的文档')
    def subset_doc_and_return_new_doc(self, doc: Document, contains_latin: bool = False) -> Document:
        """
        创建字体的子集，减少文档大小，前提必须在主线程中调用,否则会导致文件找不到异常
        参考：https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
        :param doc:
        :return:
        """
        tmp_file_path = None
        try:
            # doc.subset_fonts(verbose=True)
            # https://pymupdf.readthedocs.io/en/latest/tools.html#Tools.set_subset_fontnames
            if contains_latin:
                doc.subset_fonts(
                    fallback=True)  # 支持拉丁字符，不过效率会慢.  use doc.subset_fonts(fallback=True) which will use the mechanism of the fontTools package.
            else:
                doc.subset_fonts()
            # doc.subset_fonts(fallback=True)

            # 参考: https://github.com/pymupdf/PyMuPDF/discussions/3383
            # pdf = pymupdf._as_pdf_document(doc)  # access underlying PDF-specific level
            # pymupdf.mupdf.pdf_subset_fonts2(pdf, list(range(doc.page_count)))

            tmp_dir = tempfile.gettempdir()
            tmp_file_path = os.path.join(tmp_dir, f"{tmp_dir}/{int(time.perf_counter() * 1000)}.pdf")
            doc.ez_save(tmp_file_path)
            doc.close()
            return pymupdf.open(tmp_file_path)
        except Exception:
            logger.warn(f'压缩文档处理进程冲突!')
        finally:
            if tmp_file_path:
                os.remove(tmp_file_path)

    @logged(desc='压缩合并多个item文档到一个结果文档')
    def merge_and_compress_docs(self, item_docs: list[Document], is_item_doc_close: bool = True,
                                item_call: Function = None) -> Document:
        """
        合并多个文档并压缩
        :param item_docs: 多个子文档
        :param is_item_doc_close: 是否关闭子文档
        :return: 一个文档
        """
        try:
            target_doc = pymupdf.open()
            for index, item_doc in enumerate(item_docs):
                # 每个item生成独立的document，然后插入到target中
                target_doc.insert_pdf(docsrc=item_doc)
                if item_call:
                    item_call(index, item_doc)
                if is_item_doc_close:
                    item_doc.close()
            return target_doc
        except BaseException as exception:
            logger.exception(exception)
            raise exception

    @logged(desc='通过多个items处理成一个结果文档')
    def generate_from_items_without_close(self, items: list[Item], url_datas: dict,
                                          item_callback: Function = None) -> Document:
        """
        通过多个items处理成一个结果文档
        :param items: item任务列表
        :param url_datas: url_data的对照表
        :param item_callback: 单个item处理完回调: `item_callback(item_index, item, result, exception)`
        :return: result_doc
        """
        s_time = int(time.perf_counter() * 1000)
        file_count = 0

        # 合并后的item最终文档集合
        item_docs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for index, item in enumerate(items):
                file_count += len(item.files)
                # 开始多线程处理
                future = pool.submit(self.generate_from_item_without_close, index, item, url_datas, item_callback)
                futures.append(future)
            # 处理进度
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                pass
            # 按原始顺序添加页
            for index, future in enumerate(futures):
                exception = future.exception()
                if exception:
                    logger.exception(exception)
                    raise exception
                else:
                    item_docs.append(future.result())
        logger.info(
            f'=======================================> 【{file_count}个pdf文件处理完毕】 耗时: {int(time.perf_counter() * 1000) - s_time}/ms <=======================================')
        # header_doc.close()
        target_doc = self.merge_and_compress_docs(item_docs)
        return target_doc

    def bake_document(self, doc: Document) -> None:
        """
        可立即在 PyMuPDF 中使用。有一个功能可以将注释和字段（！！！）“烘焙”到 PDF 中 - 这意味着它将这些项目转换为正常的页面内容。
        解释：https://github.com/pymupdf/PyMuPDF/discussions/3356
        """
        source_file_pdf = pymupdf.mupdf.pdf_document_from_fz_document(doc)
        pymupdf.mupdf.pdf_bake_document(source_file_pdf, 1, 1)
        pass

    def merge_url_pdfs(self, urls, item_call: Function = None):
        """
        合并多个pdf到一个pdf中
        :param urls: 文件url列表
        """
        url_datas = self.download_urls(urls)
        docs = []
        for url in urls:
            doc = pymupdf.open("pdf", url_datas[url])
            if not doc.is_pdf:
                doc = pymupdf.open('pdf', doc.convert_to_pdf())
            docs.append(doc)
        return self.merge_and_compress_docs(docs, is_item_doc_close=True, item_call=item_call)
