# This is a sample Python script.
import concurrent
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import fitz
import httpx
import uvicorn
from fastapi import FastAPI, Response, File, Form, UploadFile
from httpx import Timeout
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

executor = ThreadPoolExecutor(max_workers=4)


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
        bytes = processor.generate_pdf_bytes()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        return Response(content=repr(err), media_type="text/html", status_code=500)


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
        bytes = processor.generate_pdf_bytes()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/generate/from-urls', description='通过多个文件url生成')
async def generate_from_url(items: List[Item]):
    try:
        documents = []
        for item in items:
            processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name,
                                  item.inventory_spec,
                                  item.quantity, item.doc_date,
                                  source_urls=item.file_urls,
                                  horizontal_layout=True)
            document = processor.generate_document()
            documents.append(document)
        combiner = Combiner(documents)
        bytes = combiner.merge_to_pdf_bytes()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=merge-{int(time.time())}.pdf'}
        return Response(content=bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        return Response(content=repr(err), media_type="text/html", status_code=500)


class CallItem(BaseModel):
    items: List[Item]
    request_id: str
    process_url: str = None
    callback_url: str = 'http://localhost:8000/callback/file'


@app.post('/generate/async-callback-from-urls', description='通过多个文件url生成,并回调通知')
async def generate_from_url(call_item: CallItem):
    # thread = threading.Thread(target=async_generated_with_callback, args=(call_item,))
    # thread.start()
    executor.submit(async_generated_with_callback, call_item)
    return Response(content=f'已经开始处理,完成后回调地址: {call_item.callback_url}', media_type="text/html")


def _generate_document_thread(index, item, request):
    processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name,
                          item.inventory_spec,
                          item.quantity, item.doc_date,
                          source_urls=item.file_urls,
                          horizontal_layout=True)
    document = processor.generate_document()
    if re.match(r'^https?:/{2}\w.+$', request.process_url):
        process_data = {'total': len(request.items), 'complete': index + 1, 'request_id': request.request_id}
        thread = threading.Thread(target=async_post_process, args=(request.process_url, process_data))
        thread.start()
    return document


def async_generated_with_callback(call_item: CallItem):
    """
    异步生成
    :param call_item:
    :return:
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for index, item in enumerate(call_item.items):
                future = pool.submit(_generate_document_thread, index, item, call_item)
                futures.append(future)
            documents = []
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                documents.append(future.result())
            combiner = Combiner(documents)
            bytes = combiner.merge_to_pdf_bytes()
            files = {'file': (f'result-{int(time.time())}.pdf', bytes, 'application/pdf')}
            data = {'request_id': call_item.request_id}
            httpx.post(call_item.callback_url, files=files, data=data)
    except Exception as err:
        print(repr(err))
        data = {'request_id': call_item.request_id, 'err_msg': repr(err)}
        httpx.post(call_item.callback_url, files=files, data=data)


@app.post('/callback/file', description='接收文件上传')
async def generate_from_file(file: UploadFile = File(), request_id: str = Form()):
    print('接收到示例文件上传: ', request_id, file.filename, file.size)
    return Response(content=request_id, media_type="text/html")


def async_post_process(url, data):
    if url:
        httpx.post(url, data=data, timeout=Timeout(timeout=5.0, connect=5.0))


if __name__ == "__main__":
    # 解决 fitz 新旧别名映射的bug
    fitz.restore_aliases()
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)
