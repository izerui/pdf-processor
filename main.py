# This is a sample Python script.

import time
from typing import List

import fitz
import uvicorn
from fastapi import FastAPI, Response, File, Form
from pydantic import BaseModel

from pdf import Processor

app = FastAPI()


@app.post('/generate/from-file')
def generate_from_file(files: List[bytes] = File(),
                       qr_code: str = Form(),
                       doc_no: str = Form(),
                       inventory_code: str = Form(),
                       inventory_name: str = Form(),
                       inventory_spec: str = Form(''),
                       quantity: str = Form(),
                       doc_date: str = Form('')):
    processor = Processor(qr_code, doc_no, inventory_code, inventory_name, inventory_spec, quantity, doc_date,
                          source_files=files,
                          horizontal_layout=True)
    bytes = processor.generate_merge_pdf()
    headers = {"content-type": "application/pdf",
               "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
    return Response(content=bytes, headers=headers, media_type="application/pdf")


class Item(BaseModel):
    file_urls: List[str]
    qr_code: str
    doc_no: str
    inventory_code: str
    inventory_name: str
    inventory_spec: str | None = None
    quantity: str
    doc_date: str


@app.post('/generate/from-url')
def generate_from_url(item: Item):
    processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name, item.inventory_spec,
                          item.quantity, item.doc_date,
                          source_urls=item.file_urls,
                          horizontal_layout=True)
    bytes = processor.generate_merge_pdf()
    headers = {"content-type": "application/pdf",
               "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
    return Response(content=bytes, headers=headers, media_type="application/pdf")


if __name__ == "__main__":
    # 解决 fitz 新旧别名映射的bug
    fitz.restore_aliases()
    uvicorn.run(app, host="127.0.0.1", port=8000)
