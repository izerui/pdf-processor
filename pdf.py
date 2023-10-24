import os
import time
from io import BytesIO
from typing import List

import fitz
import httpx
import qrcode
from fitz import Document
from qrcode.image.pil import PilImage

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
                 source_files: List[bytes] = None,
                 source_urls: List[str] = None,
                 horizontal_layout: str = False):
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
        self.source_files = source_files
        self.source_urls = source_urls
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

            page.insert_font(fontname="chn",
                             fontfile=os.path.join(self.current_file_path, 'fonts', 'FangZhengHeiTiJianTi-1.ttf'))
            # 字体大小
            fontsize = 20
            # 第一列
            page.insert_text(point=fitz.Point(300, 50), text=f'工单号: {self.doc_no}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300, 100), text=f'订单交期: {self.doc_date}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(300, 150), text=f'工单数量: {self.quantity}',
                             fontsize=fontsize,
                             fontname='chn', color=(0, 0, 0))
            # 第二列
            page.insert_text(point=fitz.Point(600, 50), text=f'货品编码: {self.inventory_code}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(600, 100), text=f'货品名称: {self.inventory_name}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            page.insert_text(point=fitz.Point(600, 150), text=f'规格型号: {self.inventory_spec}',
                             fontsize=fontsize, fontname='chn', color=(0, 0, 0))
            if debugger:
                header_doc.save(os.path.join(self.current_file_path, "tmp", f"header-{int(time.time())}.pdf"))
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
        target_pdf = fitz.open()
        for source in sources:
            with fitz.open("pdf", source) as source_pdf:
                if source_pdf.metadata['format'] == 'Image':
                    source_pdf = fitz.open("pdf", source_pdf.convert_to_pdf())
                for p_index, source_page in enumerate(source_pdf):
                    # print(source_page.rect.width, source_page.rect.height)
                    new_page = target_pdf.new_page(width=self.layout_width, height=self.layout_height)
                    r1 = fitz.Rect(0, 0, new_page.rect.width, self.header_height)
                    r2 = fitz.Rect(0, self.header_height, new_page.rect.width,
                                   new_page.rect.height)
                    new_page.show_pdf_page(r1, header_document, 0)
                    rotate = 0 if source_page.rect.width > source_page.rect.height else 90
                    # 如果原页面有旋转的话,进行自适应
                    if rotate == 0 and source_page.rotation > 0:
                        rotate = source_page.rotation
                    new_page.show_pdf_page(r2, source_pdf, p_index, rotate=rotate, keep_proportion=True)
                if debugger:
                    source_pdf.save(os.path.join(self.current_file_path, "tmp", f"source-{int(time.time())}.pdf"))
        if debugger:
            target_pdf.save(os.path.join(self.current_file_path, "tmp", f"target-{int(time.time())}.pdf"))
        return target_pdf

    def generate_pdf_bytes(self):
        document: Document = self._with_header_document(self._merge_document)
        pdf_bytes = document.convert_to_pdf()
        document.close()
        return pdf_bytes

    def generate_document(self):
        document: Document = self._with_header_document(self._merge_document)
        return document

    def save_to_filepath(self, file_path):
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
            for document in self.documents:
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
        with fitz.open() as target_pdf:
            for document in self.documents:
                target_pdf.insert_pdf(document)
                document.close()
            target_pdf.save(file_path)
