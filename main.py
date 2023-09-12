# This is a sample Python script.

import logging

import fitz
import time
import uvicorn
from fastapi import FastAPI, Response, File, Form
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse

from pdf import Processor

# Press ⇧F10 to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
#
# zoom = 100
#
#
# def output_pngs(pdf_file):
#     with fitz.open(pdf_file) as pdf:
#         for page in pdf:
#             mat = fitz.Matrix(zoom / 100.0, zoom / 100.0)
#             pixmap = page.get_pixmap(matrix=mat, alpha=False)
#             pixmap.save(f'images/page-{int(time.time())}.png')
#
#
# def output_png0(pdf_file):
#     with fitz.open(pdf_file) as pdf:
#         page = pdf.load_page(0)
#         # pixmap = page.get_pixmap(alpha=False)
#         # fmt = fitz.paper_size("A4")
#         # a4_width = fmt[0]
#         # a4_height = fmt[1]
#         # scale_w = a4_width / pixmap.height
#         # scale_h = a4_height / pixmap.width
#         # mat = fitz.Matrix(scale_w * 2, scale_h * 2)  # 旋转 .prerotate(270)
#         mat = fitz.Matrix(zoom / 100.0, zoom / 100.0)
#         pixmap = page.get_pixmap(matrix=mat, alpha=False)
#         pixmap.save(f'images/png-{int(time.time())}.png')
#
#
# def add_watermark(pdf_file, watermark):
#     with fitz.open(pdf_file) as pdf:
#         for page in pdf:
#             # page.insert_image(page.bound(), filename=watermark, overlay=False)
#             new_page = pdf.new_page()
#             rect = fitz.Rect(200, 200, 600, 600)
#             page.insert_image(rect, filename=watermark, overlay=False)
#             # page.insert_text((800, 800), '少时诵诗书', fontname="HT", fontsize=86, color=(0, 0, 0, 1), fill=None,
#             #                  render_mode=0, border_width=1, rotate=0, morph=None, overlay=True)
#         pdf.save(os.path.join("output", f"watermark-{int(time.time())}.pdf"))
#
#
# def output_svg(pdf_file):
#     with fitz.open(pdf_file) as pdf:
#         page = pdf.load_page(0)
#         svg = page.get_svg_image(matrix=0.17)
#         print(svg)
#
#
# def output_page(pdf_file):
#     with fitz.open(pdf_file) as pdf:
#         for page in pdf:
#             pix = page.get_pixmap(alpha=False)
#             print(pix.width, pix.height)
#
#

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()


@app.post('/generate')
def generate(file: bytes = File(),
             qr_code: str = Form(),
             doc_no: str = Form(),
             inventory_code: str = Form(),
             inventory_name: str = Form(),
             inventory_spec: str = Form(),
             quantity: str = Form(),
             doc_date: str = Form()):
    processor = Processor(file, qr_code, doc_no, inventory_code, inventory_name, inventory_spec, quantity, doc_date,
                          horizontal_layout=True)
    bytes = processor.generate_merge_pdf()
    headers = {"content-type": "application/pdf",
               "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
    return Response(content=bytes, headers=headers, media_type="application/pdf")


if __name__ == "__main__":
    # 解决 fitz 新旧别名映射的bug
    fitz.restore_aliases()
    uvicorn.run(app, host="127.0.0.1", port=8000)
