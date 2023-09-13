# This is a sample Python script.

import time

import fitz
import uvicorn
from fastapi import FastAPI, Response, File, Form

from pdf import Processor

app = FastAPI()


@app.post('/generate')
def generate(file: bytes = File(),
             qr_code: str = Form(),
             doc_no: str = Form(),
             inventory_code: str = Form(),
             inventory_name: str = Form(),
             inventory_spec: str = Form(''),
             quantity: str = Form(),
             doc_date: str = Form('')):
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
