# This is a sample Python script.

import logging
import time

import fitz
import uvicorn
from fastapi import FastAPI, Response, File, Form

from pdf import Processor

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()

def log_time(func):
    def wrapper(*args, **kwargs):
        # 在调用原始函数前添加新的功能，或在后面添加
        s_time = time.time()
        # 调用原始函数
        result = func(*args, **kwargs)
        # 在结果之前或结果之后添加其他内容
        e_time = time.time()
        logger.info(f'统计耗时: {repr(func)} 耗时 ：{e_time - s_time}秒')
        return result

    return wrapper


@app.post('/generate')
def generate(file: bytes = File(),
             qr_code: str = Form(),
             doc_no: str = None,
             inventory_code: str = None,
             inventory_name: str = None,
             inventory_spec: str = None,
             quantity: str = None,
             doc_date: str = None):
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
