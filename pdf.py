import os
from io import BytesIO

import fitz
import httpx
import qrcode
from qrcode.image.pil import PilImage

from utils import log_time


class Processor(object):
    def __init__(self,
                 qr_code: str,
                 doc_no: str,
                 inventory_code: str,
                 inventory_name: str,
                 inventory_spec: str,
                 quantity: str,
                 doc_date: str,
                 source_bytes: bytes = None,
                 source_url: str = None,
                 horizontal_layout: str = False,
                 zoom: int = 2):
        """
        :param file: 待处理的pdf文件
        :param qr_code: 二维码
        :param doc_no: 工单号
        :param inventory_name: 货品名称
        :param quantity: 工单数量
        :param doc_date: 订单交期
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
        self.source_bytes = source_bytes
        self.source_url = source_url
        self.horizontal_layout = horizontal_layout
        self.zoom = zoom
        _wh = self._get_width_height()
        self.layout_width = _wh[0] * self.zoom
        self.layout_height = _wh[1] * self.zoom
        self.header_height = 90 * self.zoom

    def _get_width_height(self):
        """
        获取页面宽高
        :return:
        """
        fmt = fitz.paper_size("A4")
        a4_width = fmt[0]
        a4_height = fmt[1]
        return (a4_height, a4_width) if self.horizontal_layout else (a4_width, a4_height)

    def with_header_pdf(self, callback):
        """
        生成header头信息pdf
        :param horizontal_layout: 是否横向
        :return:
        """
        with fitz.open() as doc:
            page = doc.new_page(width=self.layout_width, height=self.header_height)
            img: PilImage = qrcode.make(data=self.qr_code)
            imagefile = BytesIO()
            img.save(imagefile)

            # page.insert_image(
            #     rect=fitz.Rect(5 * self.zoom, 5 * self.zoom, 100 * self.zoom, 100 * self.zoom),
            #     filename=os.path.join(self.current_file_path, 'logo', 'logo20220210-01.png'), overlay=False)

            # 二维码: 左移80、下移10、宽高统一180
            page.insert_image(
                rect=fitz.Rect(40 * self.zoom, 5 * self.zoom, (50 + 90) * self.zoom,
                               5 * self.zoom + self.header_height),
                stream=imagefile,
                overlay=False)

            page.insert_font(fontname="chn",
                             fontfile=os.path.join(self.current_file_path, 'fonts', 'FangZhengHeiTiJianTi-1.ttf'))
            # 字体大小
            fontsize = 10 * self.zoom
            # 第一列
            page.insert_text(point=fitz.Point(150 * self.zoom, 25 * self.zoom), text=f'工单号: {self.doc_no}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(150 * self.zoom, 50 * self.zoom), text=f'订单交期: {self.doc_date}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(150 * self.zoom, 75 * self.zoom), text=f'工单数量: {self.quantity}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            # 第二列
            page.insert_text(point=fitz.Point(300 * self.zoom, 25 * self.zoom), text=f'货品编码: {self.inventory_code}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300 * self.zoom, 50 * self.zoom), text=f'货品名称: {self.inventory_name}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300 * self.zoom, 75 * self.zoom), text=f'规格型号: {self.inventory_spec}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            # doc.save(os.path.join(self.current_file_path, "header", f"header-{int(time.time())}.pdf"))
            return callback(doc)
            # pdf_bytes = doc.convert_to_pdf()
            # return pdf_bytes

    @log_time
    def generate_merge_pdf(self):
        def callback(header_pdf):
            source_bytes = self.source_bytes
            if not source_bytes:
                response = httpx.get(self.source_url)
                pass
            with fitz.open() as target_pdf, fitz.open("pdf", source_bytes) as source_pdf:
                for p_index, source_page in enumerate(source_pdf):
                    new_page = target_pdf.new_page(width=self.layout_width, height=self.layout_height)
                    r1 = fitz.Rect(0, 0, new_page.rect.width, self.header_height)
                    r2 = r1 + (0, self.header_height, 0, new_page.rect.height - self.header_height)
                    new_page.show_pdf_page(r1, header_pdf, 0)
                    new_page.show_pdf_page(r2, source_pdf, p_index)
                # target_pdf.save(os.path.join(self.current_file_path, "output", f"newpdf-{int(time.time())}.pdf"))
                pdf_bytes = target_pdf.convert_to_pdf()
                return pdf_bytes

        return self.with_header_pdf(callback)
