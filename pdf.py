import os
import time
from io import BytesIO
from typing import List

import fitz
import httpx
import qrcode
from fitz import Document, Font, Page
from fitz.utils import Shape
from numpy import ndarray
from qrcode.image.pil import PilImage
import numpy as np

from utils import logger

## All Index: https://pymupdf.readthedocs.io/en/latest/genindex-all.html
debugger = False


def _retry_get_file(url):
    for _ in range(5):
        try:
            resp = httpx.get(url)
            return resp
        except Exception:
            continue
    raise RuntimeError(f'{url} 文件下载失败')


class Processor(object):
    def __init__(self,
                 qr_code: str,
                 doc_no: str,
                 inventory_code: str,
                 inventory_name: str,
                 inventory_spec: str,
                 quantity: str,
                 doc_date: str,
                 process_flow: str = '',
                 source_files: List[bytes] = None,
                 source_urls: List[str] = None,
                 marks_str: str = None,
                 rotates: List[int] = None,
                 horizontal_layout: str = False):
        """
        :param file: 待处理的pdf文件
        :param qr_code: 二维码
        :param doc_no: 工单号
        :param inventory_name: 货品名称
        :param quantity: 工单数量
        :param doc_date: 订单交期
        :param process_flow: 工艺路线
        :param horizontal_layout: 是否横向
        """
        super().__init__()
        self.current_file_path = os.path.abspath(os.path.dirname(__file__))
        self.qr_code = qr_code
        self.doc_no = doc_no
        self.inventory_code = inventory_code
        self.inventory_name = inventory_name
        self.inventory_spec = inventory_spec
        self.quantity = quantity
        self.doc_date = doc_date
        self.process_flow = process_flow
        self.source_files = source_files
        self.source_urls = source_urls
        self.marks = None
        if marks_str:
            # page之间空格
            # rect之间;
            # 坐标之间,
            # sample = '10,2,4,5;4,2,1,6 100,20,40,50;14,22,11,16 102,23,44,55;41,22,13,64'
            self.marks = list(
                map(
                    lambda x: list(
                        map(
                            lambda y: list(
                                map(
                                    lambda z: z,
                                    y.split(',')
                                )
                            ),
                            x.split(';')
                        )
                    ),
                    marks_str.split(' ')
                )
            )
        self.horizontal_layout = horizontal_layout
        _wh = self._get_width_height()
        self.layout_width = _wh[0]
        self.layout_height = _wh[1]
        self.header_height = 180

    def _get_width_height(self):
        """
        获取页面宽高
        :return:
        """
        # DPI: 150
        a4_width = 1240
        a4_height = 1754
        return (a4_height, a4_width) if self.horizontal_layout else (a4_width, a4_height)

    def _with_header_document(self, callback):
        """
        生成header头信息pdf
        :param horizontal_layout: 是否横向
        :return:
        """
        with fitz.open() as header_doc:
            page = header_doc.new_page(width=self.layout_width, height=self.header_height)
            img: PilImage = qrcode.make(data=self.qr_code)
            imagefile = BytesIO()
            img.save(imagefile)

            # page.insert_image(
            #     rect=fitz.Rect(10, 10, 200, 200),
            #     filename=os.path.join(self.current_file_path, 'logo', 'logo20220210-01.png'), overlay=False)

            # 二维码: 左移80、下移10、宽高统一180
            page.insert_image(
                rect=fitz.Rect(80, 10, 280,
                               10 + self.header_height),
                stream=imagefile,
                overlay=False)

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

            # ms宋体下载: https://www.fontsaddict.com/font/ms-song.html
            # 其他字体下载: http://www.ae-sys.com/China/Fonts/
            # page.insert_font(fontname=chn_fontname,
            #                  fontfile=os.path.join(self.current_file_path, 'fonts', 'ms-song.ttf'))

            # 字体大小
            fontsize = 20
            # 第一列
            page.insert_text(point=fitz.Point(280, 50), text=f'工单号: {self.doc_no}',
                             fontsize=fontsize,
                             fontname=chn_fontname, color=(0, 0, 0))
            page.insert_text(point=fitz.Point(280, 100), text=f'交期: {self.doc_date}',
                             fontsize=fontsize,
                             fontname=chn_fontname, color=(0, 0, 0))
            page.insert_text(point=fitz.Point(280, 150), text=f'工艺路线: {self.process_flow}',
                             fontsize=fontsize,
                             fontname=chn_fontname, color=(0, 0, 0))

            # 第二列
            page.insert_text(point=fitz.Point(580, 50), text=f'货品编码: {self.inventory_code}',
                             fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
            page.insert_text(point=fitz.Point(580, 100), text=f'数量: {self.quantity}',
                             fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))

            # 第三列
            page.insert_text(point=fitz.Point(900, 50), text=f'货品名称: {self.inventory_name}',
                             fontsize=fontsize, fontname=chn_fontname, color=(0, 0, 0))
            page.insert_text(point=fitz.Point(900, 100), text=f'规格型号: {self.inventory_spec}',
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
            return callback(header_doc)
            # pdf_bytes = doc.convert_to_pdf()
            # return pdf_bytes

    def _merge_document(self, header_document):
        sources = self.source_files
        if not sources:
            sources = []
            for source_url in self.source_urls:
                response = _retry_get_file(source_url)
                if not response.is_success:
                    raise IOError(f'文件下载失败, url: {source_url}')
                sources.append(response.content)
        if not sources:
            raise RuntimeError(f'没有可转换的文件')
        # pdfs = list(map(lambda x: fitz.open('pdf', x), sources))
        # pages = list(map(lambda pdf: pdf[0], pdfs))
        target_pdf = fitz.open()
        for s_index, source in enumerate(sources):
            source_pdf: Document = fitz.open("pdf", source)

            # 注释掉不再单独判断image类型进行pdf转换
            # if source_pdf.metadata['format'] == 'Image':
            #     source_pdf = fitz.open("pdf", source_pdf.convert_to_pdf())

            # 如果是图片重新转换一次，以适配完整对象的正常使用
            # 比如is_fast_webaccess属性为True会影响合并效果: https://pymupdf.readthedocs.io/en/latest/document.html#Document.is_fast_webaccess
            if not source_pdf.is_pdf:
                try:
                    source_pdf = fitz.open("pdf", source_pdf.convert_to_pdf())
                except BaseException as err:
                    logger.warn(repr(err))

            # 最终使用的pdf对象来进行裁切拼接, 如果有注释，则为转化后的新pdf 问题fixed: https://pymupdf.readthedocs.io/en/latest/page.html#f6
            usage_pdf: Document = source_pdf
            # 判断页面是否包含注释,如果包含注释则转换成另一个pdf再利用
            # 注意: 如果发生了二次转换, 页面会丢失旋转角度
            if source_pdf.has_annots():
                try:
                    copy_pdf = fitz.open('pdf', source_pdf.convert_to_pdf())
                    usage_pdf = copy_pdf
                except BaseException as e:
                    logger.warn(f'处理注释失败: {repr(e)}')
            for p_index, usage_page in enumerate(usage_pdf):
                # 标记遮罩区域
                self._mask_page_content(p_index, usage_page)
                # source_page = source_pdf[p_index]
                # print(usage_page.rect.width, usage_page.rect.height)
                new_page = target_pdf.new_page(width=self.layout_width, height=self.layout_height)
                r1 = fitz.Rect(0, 0, new_page.rect.width, self.header_height)
                r2 = fitz.Rect(0, self.header_height, new_page.rect.width,
                               new_page.rect.height)
                new_page.show_pdf_page(r1, header_document, 0)
                # 获取页面应该回正的旋转角度
                rotate = self._get_rotate_from_page(usage_page, p_index, s_index)
                # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
                usage_page.set_rotation(0)
                new_page.show_pdf_page(r2, usage_pdf, p_index, rotate=rotate, keep_proportion=True,
                                       clip=usage_page.cropbox)
                # self._mask_page_content(new_page)

                if debugger:
                    # ######### 增加输出原页面 测试用
                    # 按原页面宽高设置新页面
                    sWidth = usage_page.bound().width
                    sHeight = usage_page.bound().height
                    print(f'f:{s_index + 1} p:{p_index + 1} w:{sWidth} h:{sHeight}')
                    sPage = target_pdf.new_page(width=sWidth, height=sHeight)
                    # 按源页面旋转度数复制
                    # cropbox 页面裁剪框
                    # fitz.Rect(0, 0, sWidth, sHeight) 也可以换成 usage_page.bound()
                    # https://pymupdf.readthedocs.io/en/latest/page.html#Page.show_pdf_page
                    sPage.show_pdf_page(fitz.Rect(0, 0, sWidth, sHeight), usage_pdf, p_index, keep_proportion=True,
                                        rotate=usage_page.rotation, clip=usage_page.bound())
                    ######### 增加输出原页面 测试用
            if debugger:
                folder = os.path.join(self.current_file_path, 'tmp')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                ## 测试获取第一页的线条，并画在新的页面上 begin
                # page0 = usage_pdf[0]
                # paths = page0.get_drawings()
                #
                # page1 = usage_pdf.new_page(width=page0.rect.width, height=page0.rect.height)
                # shape = page1.new_shape()
                # for path in paths:
                #     # ------------------------------------
                #     # draw each entry of the 'items' list
                #     # ------------------------------------
                #     for item in path["items"]:  # these are the draw commands
                #         if item[0] == "l":  # line
                #             shape.draw_line(item[1], item[2])
                #         elif item[0] == "re":  # rectangle
                #             shape.draw_rect(item[1])
                #         elif item[0] == "qu":  # quad
                #             shape.draw_quad(item[1])
                #         elif item[0] == "c":  # curve
                #             shape.draw_bezier(item[1], item[2], item[3], item[4])
                #         else:
                #             raise ValueError("unhandled drawing", item)
                #     shape.finish(
                #         fill=path["fill"],  # fill color
                #         color=path["color"],  # line color
                #         dashes=path["dashes"],  # line dashing
                #         even_odd=path.get("even_odd", True),  # control color of overlaps
                #         closePath=path["closePath"],  # whether to connect last and first point
                #         lineJoin=path["lineJoin"],  # how line joins should look like
                #         lineCap=max(path["lineCap"]),  # how line ends should look like
                #         width=path["width"],  # line width
                #         stroke_opacity=path.get("stroke_opacity", 1)  # same value for both
                #     )
                # # all paths processed - commit the shape to its page
                # shape.commit()
                ## 测试获取第一页的线条，并画在新的页面上 end
                usage_pdf.save(os.path.join(folder, f"source-{int(time.time())}.pdf"))

            # 关闭文档
            source_pdf.close()
            if source_pdf != usage_pdf:
                usage_pdf.close()
        if debugger:
            folder = os.path.join(self.current_file_path, 'tmp')
            if not os.path.exists(folder):
                os.makedirs(folder)
            # # 创建字体的子集，减少文档大小
            # # https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
            target_pdf.subset_fonts()
            target_pdf.save(os.path.join(folder, f"target-{int(time.time())}.pdf"))
        return target_pdf

    def _mask_page_content(self, index: int, page: Page):
        """
        遮罩页面内容
        :param index: 页码
        :param page: 要遮罩的页面
        :return:
        """
        marks: list = self.marks
        if marks and len(marks) > index:
            # 当前页的多个遮罩区域list
            page_marks: list = marks[index]
            if page_marks and len(page_marks) > 0:
                for rect_mark in page_marks:
                    assert len(
                        rect_mark) >= 4, '遮罩格式不对,坐标以逗号连接[x0,y0,x1,y1], 多个遮罩块以;连接[rect0;rect1], 每页的遮罩数组以空格连接[page0 page1]! 示例: 10,2,4,5;4,2,1,6 100,20,40,50;14,22,11,16 102,23,44,55;41,22,13,64'
                    rect = fitz.Rect(float(rect_mark[0]), float(rect_mark[1]), float(rect_mark[2]), float(rect_mark[3]))
                    if len(rect_mark) == 4:  # 添加遮罩矩形区域
                        shape: Shape = page.new_shape()
                        shape.draw_rect(rect=rect)
                        shape.finish(
                            fill=0,  # fill color
                            color=0  # line color
                        )
                        shape.commit()
                    elif len(rect_mark) == 5:
                        img_url = rect_mark[4]
                        response = _retry_get_file(img_url)
                        if not response.is_success:
                            raise IOError(f'图片下载失败, url: {img_url}')
                        # img = fitz.open(stream=response.content)
                        page.insert_image(rect, stream=response.content, keep_proportion=False)
        pass

    def _get_rotate_from_page(self, source_page: Page, page_index, source_index):
        """
        从源页面获取旋转角度
        :param source_page: 源页面
        :param page_index: 原页面索引
        :param source_index: 原文件索引
        :return: 旋转角度
        """
        # Maxtrix 解析: https://pymupdf.readthedocs.io/en/latest/matrix.html
        # 其他解析(通俗易懂):
        # * https://docs.godotengine.org/zh-cn/4.x/tutorials/math/matrices_and_transforms.html (这个先看完，把变换矩阵理解透)
        # * https://github.com/alvarto/blog/issues/1  (建议看这个更明白)
        # * https://docs.aspose.com/svg/zh/net/drawing-basics/transformation-matrix/  (这个可以尝试自己获取一个svg进行修改测试) 参看文件: `transform2d.svg`
        # a: x方向缩放(宽度)。例如，如果值为0.5，则将宽度缩小2倍。如果a < 0，将(额外地)发生左右翻转。
        # b: 产生剪切效果: 每个点(x, y)将变成点(x, y - b * x)。因此，水平线会“倾斜”。
        # c: 产生剪切效果: 每个点(x, y)都会变成点(x - c * y, y)，因此垂直线会“倾斜”。
        # d: y方向缩放(高度)。例如，如果值为1.5，则将高度拉伸50 %。如果d < 0，将(额外地)发生上下翻转。
        # e: 产生水平偏移效果: 每个Point(x, y)都会变成Point(x + e, y)， e的正(负)值会向右(左)偏移。
        # f: 产生垂直位移效应: 每个Point(x, y)都会变成Point(x, y - f)， f的正(负)值会向下(上)移动。
        # 其他一些资料:
        # 四元数在线可视化转换网站: https://quaternions.online/
        # 三维在线旋转变换网站: https://www.andre-gaschler.com/rotationconverter/
        # 二维 Rotation Conversion Tool: https://danceswithcode.net/engineeringnotes/quaternions/conversion_tool.html

        print(
            f'文件{source_index + 1}  第{page_index + 1}页  宽:{source_page.mediabox.width}  高:{source_page.mediabox.height}  旋转:{source_page.rotation}  rotation_matrix:{source_page.rotation_matrix}  transformation_matrix:{source_page.transformation_matrix}')

        # 原始页面的长宽  注意： cropbox 为原始页面，  page.bound() 为set_rotation后的看到的页面，所以不能用bound() 因为外部使用页面拼接的时候是使用原始页面，最后合并时候才旋转
        page_rect = source_page.cropbox

        # 原页面是否是横版
        is_horizontal: bool = page_rect.width > page_rect.height
        rotate = 0
        # 如果默认是横版，不做90转换, 如果是竖版，需要旋转90度的奇数倍数
        if not is_horizontal:
            if (int(source_page.rotation / 90)) % 2 == 1:
                rotate = -source_page.rotation
            else:
                rotate = -source_page.rotation
                rotate += -90  # 竖版一以右侧为底， 如果是+90 则是以竖版的左侧为底

        # 如果发生了基于x轴的上线翻转，则额外加180度
        if source_page.rotation_matrix.d < 0:
            rotate += 180

        if rotate != 0:
            print(f'    > 转横版,需旋转 {rotate}')
        return rotate

    def generate_pdf_bytes(self):
        """
        生成pdf文件的字节数组
        :return:
        """
        document: Document = self._with_header_document(self._merge_document)
        pdf_bytes = document.convert_to_pdf()
        document.close()
        return pdf_bytes

    def generate_document(self):
        """
        返回文档对象
        :return:
        """
        document: Document = self._with_header_document(self._merge_document)
        return document

    def save_to_filepath(self, file_path):
        """
        保存pdf到指定的文件路径
        :param file_path:
        :return:
        """
        with self.generate_document() as document:
            document.save(filename=file_path)


class Combiner(object):

    def __init__(self, documents: List[Document]):
        self.documents = documents

    def merge_to_pdf_bytes(self):
        """
        合并多个pdf文件,返回合并后的文件字节数组
        :return:
        """
        with fitz.open() as target_pdf:
            for index, document in enumerate(self.documents):
                if not document:
                    raise BaseException(f'第{index + 1}个文件出错!')
                target_pdf.insert_pdf(document)
                document.close()
            # target_pdf.save(os.path.join(self.current_file_path, "output", f"newpdf-{int(time.time())}.pdf"))
            pdf_bytes = target_pdf.convert_to_pdf()
            return pdf_bytes

    def save_to_filepath(self, file_path):
        """
        合并多个pdf文件, 并写入到file_path中
        :return:
        """
        # 输出文档的包含字体文件列表
        self._output_fonts(self.documents)
        with fitz.open() as target_pdf:
            for index, document in enumerate(self.documents):
                # 另一种实现:
                # for index, page in enumerate(document):
                #     page_bound = page.bound()
                #     new_page: Page = target_pdf.new_page(width=page_bound.width, height=page_bound.height)
                #     new_page.show_pdf_page(page_bound, document, index, keep_proportion=True,
                #                         rotate=page.rotation, clip=page_bound)
                #     pass
                if not document:
                    raise BaseException(f'第{index + 1}个文件出错!')
                try:
                    # 创建字体的子集，减少文档大小 Package fontTools must be installed `pip install fonttools`
                    document.subset_fonts()
                except BaseException as err:
                    logger.warn(f'文档创建字体子集: {repr(err)}')

                target_pdf.insert_pdf(docsrc=document)  # , annots=False, links=False
                document.close()
            # 创建字体的子集，减少文档大小 Package fontTools must be installed `pip install fonttools`
            # https://pymupdf.readthedocs.io/en/latest/document.html#Document.subset_fonts
            try:
                target_pdf.subset_fonts()
            except BaseException as err:
                logger.warn(f'合并后的文档创建字体子集: {repr(err)}')
            target_pdf.save(file_path)
            if debugger:
                folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tmp')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                target_pdf.save(os.path.join(folder, f"combiner-{int(time.time())}.pdf"))

    def _output_fonts(self, documents):
        for d_index, document in enumerate(documents):
            print(f'文档{d_index + 1}:')
            for p_index, page in enumerate(document):
                # 输出页面字体列表
                fonts = document.get_page_fonts(pno=p_index, full=True)
                print(f'    页面{p_index + 1},包含的字体:')
                for font in fonts:
                    print(f'        {font}')
