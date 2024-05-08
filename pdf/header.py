from io import BytesIO

import fitz
import qrcode
from fitz import *
from qrcode.image.pil import PilImage

from model import Item
from support import a4_width, header_height


def get_rect(p: Point, width: int = 200, height: int = 35):
    x1 = p.x + width
    y1 = p.y + height
    return fitz.Rect(p.x, p.y, x1, y1)


class IHeader(object):
    def __init__(self, header_doc: Document, item: Item):
        self.item = item
        self.header_doc = header_doc

    def generate_header_page(self):
        pass


class Header331(IHeader):

    def generate_header_page(self):
        page = self.header_doc.new_page(width=a4_width, height=header_height)

        # 二维码: 左上角坐标 80、10、宽高统一180
        img: PilImage = qrcode.make(data=self.item.qr_code)
        imagefile = BytesIO()
        img.save(imagefile)
        page.insert_image(
            rect=fitz.Rect(80, 10, 280,
                           10 + header_height),
            stream=imagefile,
            overlay=False)

        # 序号
        if self.item.item_no:
            page.insert_text(point=fitz.Point(1754 - 50, 50), text=f'{self.item.item_no}',
                             fontsize=18,
                             color=(30 / 255, 144 / 255, 255 / 255))
            # page.insert_htmlbox(
            #     rect=get_rect(fitz.Point(1754 - 50, 50), 50, 20),
            #     text=f'<b>{self.item.item_no}</b>',
            #     css='* {font-family: sans-serif;font-size:16px;color:blue;}'
            # )

        # https://pymupdf.readthedocs.io/en/latest/page.html#Page.insert_font
        # page.insert_font(fontname=chn_fontname,
        #                  fontbuffer=font.buffer)

        # 行高
        line_height = 40
        # 距离顶部距离
        top_padding = 30
        # 行间距
        line_space = 5
        # 标签与值间距
        column_space = 5

        # @logged(desc='插入表单项')
        def insert_form_item(label: str, value: str, x: float, label_width: float, value_width: float,
                             line_no: int = 0):
            """
            插入表单项
            """
            label_point = fitz.Point(x, top_padding + line_no * (line_height + line_space))
            value_point = fitz.Point(x + column_space + label_width,
                                     top_padding + line_no * (line_height + line_space))
            page.insert_htmlbox(
                rect=get_rect(label_point, label_width, line_height),
                text=f'<span style="font-size:18px;font-weight:bold;display:block;word-break:break-all;">{label}</span>'
            )
            # page.draw_rect(get_rect(label_point, label_width, line_height), color=(1, 0, 0))

            page.insert_htmlbox(
                rect=get_rect(value_point, value_width, line_height),
                text=f'<span style="font-size:18px;font-weight:bold;word-break:break-all;">{value}</span>'
            )
            # page.draw_rect(get_rect(value_point, value_width, line_height), color=(1, 0, 0))

        ########### 第一列
        # 工单号
        insert_form_item('工单号: ', self.item.doc_no, 280, 60, 330, 0)
        # 交期
        insert_form_item('交 期: ', self.item.doc_date, 280, 60, 330, 1)
        # 工艺路线
        insert_form_item('工艺路线: ', self.item.process_flow, 280, 80, 800, 2)

        ########### 第二列
        # 货品编码
        insert_form_item('货品编码: ', self.item.inventory_code, 680, 80, 320, 0)
        # 数量
        insert_form_item('数 量: ', self.item.quantity, 680, 80, 320, 1)

        ########### 第三列
        # 货品名称
        insert_form_item('货品名称: ', self.item.inventory_name, 1100, 80, 400, 0)
        # 规格型号
        insert_form_item('规格型号: ', self.item.inventory_spec, 1100, 80, 400, 1)



class Header221(IHeader):
    def generate_header_page(self):
        pass


class Header222(IHeader):
    def generate_header_page(self):
        pass


class Header333(IHeader):
    def generate_header_page(self):
        pass


class Header441(IHeader):
    def generate_header_page(self):
        pass
