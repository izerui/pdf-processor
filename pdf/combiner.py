import os
import time
from typing import List

import fitz
from fitz import Document

from utils import logger

## All Index: https://pymupdf.readthedocs.io/en/latest/genindex-all.html
debugger = False


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
