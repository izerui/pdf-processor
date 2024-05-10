from io import BytesIO

import fitz
import qrcode
from fitz import *
from qrcode.image.pil import PilImage

from model import Item, ItemRender
from support import a4_width, header_height, a4_height


def get_rect(p: Point, width: int = 200, height: int = 35):
    x1 = p.x + width
    y1 = p.y + height
    return fitz.Rect(p.x, p.y, x1, y1)


class IHeader(object):
    def __init__(self, header_doc: Document, item: Item):
        self.item = item
        self.header_doc = header_doc
        self.page = header_doc.new_page(width=a4_width, height=header_height)
        # 行高
        self.line_height = 40
        # 距离顶部距离
        self.top_padding = 30
        # 行间距
        self.line_space = 5
        # 标签与值间距
        self.column_space = 2

    # @logged(desc='插入表单项')
    def insert_form_item(self, form_item: ItemRender, x: float, label_width: float, value_width: float,
                         line_no: int = 0):
        """
        插入表单项
        """
        if not form_item or not (form_item.label and not form_item.value):
            return
        label_point = fitz.Point(x, self.top_padding + line_no * (self.line_height + self.line_space))
        value_point = fitz.Point(x + self.column_space + label_width,
                                 self.top_padding + line_no * (self.line_height + self.line_space))
        self.page.insert_htmlbox(
            rect=get_rect(label_point, label_width, self.line_height),
            text=f'<span style="font-size:18px;font-weight:bold;display:block;word-break:break-all;">{form_item.label}</span>'
        )
        # page.draw_rect(get_rect(label_point, label_width, line_height), color=(1, 0, 0))

        self.page.insert_htmlbox(
            rect=get_rect(value_point, value_width, self.line_height),
            text=f'<span style="font-size:18px;font-weight:bold;word-break:break-all;">{form_item.value}</span>'
        )
        # page.draw_rect(get_rect(value_point, value_width, line_height), color=(1, 0, 0))

    def generate_header_page(self):
        # 二维码: 左上角坐标 80、10、宽高统一180
        img: PilImage = qrcode.make(data=self.item.qr_code)
        imagefile = BytesIO()
        img.save(imagefile)
        self.page.insert_image(
            rect=fitz.Rect(80, 10, 280,
                           10 + header_height),
            stream=imagefile,
            overlay=False)

        # 序号
        if self.item.item_no:
            is_top = True if self.item.header_layout and self.item.header_layout == 'top' else False
            no_p = fitz.Point(a4_width - 50, 50) if is_top else fitz.Point(a4_width - 50, header_height - 50)
            self.page.insert_text(point=no_p, text=f'{self.item.item_no}',
                                  fontsize=18,
                                  color=(30 / 255, 144 / 255, 255 / 255))
            # page.insert_htmlbox(
            #     rect=get_rect(fitz.Point(1804 - 50, 50), 50, 20),
            #     text=f'<b>{self.item.item_no}</b>',
            #     css='* {font-family: sans-serif;font-size:16px;color:blue;}'
            # )
        pass


class Header331(IHeader):

    def generate_header_page(self):
        super().generate_header_page()

        # https://pymupdf.readthedocs.io/en/latest/page.html#Page.insert_font
        # page.insert_font(fontname=chn_fontname,
        #                  fontbuffer=font.buffer)

        # 第一列
        self.insert_form_item(self.item.form_item1, 270, 80, 320, 0)
        self.insert_form_item(self.item.form_item4, 270, 80, 320, 1)
        self.insert_form_item(self.item.form_item7, 270, 80, 800, 2)

        # 第二列  + 410
        self.insert_form_item(self.item.form_item2, 680, 80, 330, 0)
        self.insert_form_item(self.item.form_item5, 680, 80, 330, 1)

        # 第三列  + 420
        self.insert_form_item(self.item.form_item3, 1100, 80, 320, 0)
        self.insert_form_item(self.item.form_item6, 1100, 80, 320, 1)


class Header221(IHeader):
    def generate_header_page(self):
        super().generate_header_page()

        # 第一列
        self.insert_form_item(self.item.form_item1, 270, 80, 600, 0)
        self.insert_form_item(self.item.form_item3, 270, 80, 600, 1)
        self.insert_form_item(self.item.form_item5, 270, 80, 800, 2)

        # 第二列  + 710
        self.insert_form_item(self.item.form_item2, 980, 80, 600, 0)
        self.insert_form_item(self.item.form_item4, 980, 80, 600, 1)


class Header222(IHeader):
    def generate_header_page(self):
        super().generate_header_page()

        # 第一列
        self.insert_form_item(self.item.form_item1, 270, 80, 600, 0)
        self.insert_form_item(self.item.form_item3, 270, 80, 600, 1)
        self.insert_form_item(self.item.form_item5, 270, 80, 600, 2)

        # 第二列  + 710
        self.insert_form_item(self.item.form_item2, 980, 80, 600, 0)
        self.insert_form_item(self.item.form_item4, 980, 80, 600, 1)
        self.insert_form_item(self.item.form_item6, 980, 80, 600, 2)


class Header333(IHeader):
    def generate_header_page(self):
        super().generate_header_page()

        # 第一列
        self.insert_form_item(self.item.form_item1, 270, 80, 320, 0)
        self.insert_form_item(self.item.form_item4, 270, 80, 320, 1)
        self.insert_form_item(self.item.form_item7, 270, 80, 320, 2)

        # 第二列 + 410
        self.insert_form_item(self.item.form_item2, 680, 80, 330, 0)
        self.insert_form_item(self.item.form_item5, 680, 80, 330, 1)
        self.insert_form_item(self.item.form_item8, 680, 80, 330, 2)

        # 第三列 + 420
        self.insert_form_item(self.item.form_item3, 1100, 80, 330, 0)
        self.insert_form_item(self.item.form_item6, 1100, 80, 330, 1)
        self.insert_form_item(self.item.form_item9, 1100, 80, 330, 2)


class Header441(IHeader):
    def generate_header_page(self):
        super().generate_header_page()

        # 第一列
        self.insert_form_item(self.item.form_item1, 270, 80, 240, 0)
        self.insert_form_item(self.item.form_item5, 270, 80, 240, 1)
        self.insert_form_item(self.item.form_item9, 270, 80, 800, 2)

        # 第二列 + 330
        self.insert_form_item(self.item.form_item2, 600, 80, 240, 0)
        self.insert_form_item(self.item.form_item6, 600, 80, 240, 1)

        # 第三列 + 320
        self.insert_form_item(self.item.form_item3, 920, 80, 240, 0)
        self.insert_form_item(self.item.form_item7, 920, 80, 240, 1)

        # 第四列 + 320
        self.insert_form_item(self.item.form_item4, 1240, 80, 240, 0)
        self.insert_form_item(self.item.form_item8, 1240, 80, 240, 1)
