# This is a sample Python script.

import time
from typing import List

import fitz
import uvicorn
from fastapi import FastAPI, Response, File, Form
from pydantic import BaseModel

from pdf import Processor, Combiner

app = FastAPI(
    title='pdf生成、合并服务',
    summary='文档地址: 开发: https://pdf-local.yj2025.com/docs、生产: https://pdf-aws.yj2025.com/docs',
    description='开发内网服务地址: http://10.96.28.247:8000、生产内网服务地址: http://10.100.244.136:8000',
    version='1.1',
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    }
)


@app.post('/generate/from-file', description='通过文件生成')
async def generate_from_file(files: List[bytes] = File(),
                             qr_code: str = Form(),
                             doc_no: str = Form(),
                             inventory_code: str = Form(),
                             inventory_name: str = Form(),
                             inventory_spec: str = Form(''),
                             quantity: str = Form(),
                             doc_date: str = Form('')):
    try:
        processor = Processor(qr_code, doc_no, inventory_code, inventory_name, inventory_spec, quantity, doc_date,
                              source_files=files,
                              horizontal_layout=True)
        bytes = processor.generate_merge_pdf()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        return Response(content=repr(err), headers=headers, media_type="text/html", status_code=500)


class Item(BaseModel):
    file_urls: List[str]
    qr_code: str
    doc_no: str
    inventory_code: str
    inventory_name: str
    inventory_spec: str | None = None
    quantity: str
    doc_date: str


@app.post('/generate/from-url', description='通过文件url生成')
async def generate_from_url(item: Item):
    try:
        processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name, item.inventory_spec,
                              item.quantity, item.doc_date,
                              source_urls=item.file_urls,
                              horizontal_layout=True)
        bytes = processor.generate_merge_pdf()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        return Response(content=repr(err), headers=headers, media_type="text/html", status_code=500)


@app.post('/generate/from-urls', description='通过多个文件url生成')
async def generate_from_url(items: List[Item]):
    try:
        pdfs = []
        for item in items:
            processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name, item.inventory_spec,
                                  item.quantity, item.doc_date,
                                  source_urls=item.file_urls,
                                  horizontal_layout=True)
            bytes = processor.generate_merge_pdf()
            pdfs.append(bytes)
        combiner = Combiner(pdfs)
        bytes = combiner.merge()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=merge-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        return Response(content=repr(err), headers=headers, media_type="text/html", status_code=500)


if __name__ == "__main__":
    # 解决 fitz 新旧别名映射的bug
    fitz.restore_aliases()
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)
