import os
import time
from io import BytesIO

import fitz
import qrcode
from qrcode.image.pil import PilImage

current_file_path = os.path.abspath(os.path.dirname(__file__))


class Processor(object):
    def __init__(self,
                 source_pdf: bytes,
                 qr_code: str,
                 doc_no: str,
                 inventory_code: str,
                 inventory_name: str,
                 inventory_spec: str,
                 quantity: str,
                 doc_date: str,
                 horizontal_layout=False):
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
        self.source_pdf = source_pdf
        self.qr_code = qr_code
        self.doc_no = doc_no
        self.inventory_code = inventory_code
        self.inventory_name = inventory_name
        self.inventory_spec = inventory_spec
        self.quantity = quantity
        self.doc_date = doc_date
        self.horizontal_layout = horizontal_layout
        _wh = self._get_width_height()
        self.layout_width = _wh[0] * 2
        self.layout_height = _wh[1] * 2
        self.header_height = 90 * 2

    def _get_width_height(self):
        """
        获取页面宽高
        :return:
        """
        fmt = fitz.paper_size("A4")
        a4_width = fmt[0]
        a4_height = fmt[1]
        return (a4_height, a4_width) if self.horizontal_layout else (a4_width, a4_height)

    def generate_header_pdf(self):
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
            # 二维码: 左移80、下移10、宽高统一180
            page.insert_image(rect=fitz.Rect(80, 10, 100 + 180, 10 + self.header_height), stream=imagefile,
                              overlay=False)

            # red = (1, 0, 0)
            # gold = (1, 1, 0)
            # blue = (0, 0, 1)
            # r1 = fitz.Rect(820, 60, 820 + 100, 60 + 40)
            # t1 = f'工单数量: {self.quantity}'
            # shape = page.new_shape()
            # shape.draw_rect(r1)
            # shape.finish(width=0.3, color=red, fill=gold)
            # shape.insert_textbox(r1, t1, color=blue, fontname='Droid Sans Fallback Regular')
            # shape.commit()

            page.insert_font(fontname="chn", fontfile=os.path.join(current_file_path, 'fonts', 'FangZhengHeiTiJianTi-1.ttf'))

            # 第一列
            page.insert_text(point=fitz.Point(300, 50), text=f'工单号: {self.doc_no}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300, 100), text=f'订单交期: {self.doc_date}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300, 150), text=f'工单数量: {self.quantity}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))

            # 第二列
            page.insert_text(point=fitz.Point(620, 50), text=f'货品编码: {self.inventory_code}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(620, 100), text=f'货品名称: {self.inventory_name}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(620, 150), text=f'规格型号: {self.inventory_spec}', fontsize=24,
                             fontname='chn', color=(0, 0, 0))

            # doc.save(os.path.join(current_file_path, "header", f"header-{int(time.time())}.pdf"))
            pdf_bytes = doc.convert_to_pdf()
            return pdf_bytes

    def generate_merge_pdf(self):
        with fitz.open() as target_pdf, fitz.open('pdf', self.generate_header_pdf()) as header_pdf, fitz.open("pdf",
                                                                                                              self.source_pdf) as source_pdf:
            for p_index, source_page in enumerate(source_pdf):
                new_page = target_pdf.new_page(width=self.layout_width, height=self.layout_height)
                r1 = fitz.Rect(0, 0, new_page.rect.width, self.header_height)
                r2 = r1 + (0, self.header_height, 0, new_page.rect.height - self.header_height)
                new_page.show_pdf_page(r1, header_pdf, 0)
                new_page.show_pdf_page(r2, source_pdf, p_index)
            # target_pdf.save(os.path.join(current_file_path, "output", f"newpdf-{int(time.time())}.pdf"))
            pdf_bytes = target_pdf.convert_to_pdf()
            return pdf_bytes
