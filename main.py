# This is a sample Python script.
import concurrent
import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import fitz
import httpx
import uvicorn
from fastapi import FastAPI, Response, File, Form, UploadFile
from httpx import Timeout
from pydantic import BaseModel
from tqdm import tqdm

from pdf import Processor, Combiner
from utils import logger

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


def read_from_temp_file(callback):
    """
    使用自动删除的路径作为处理，并读取删除前的内容到文件byte数组
    :param callback: 参数为临时路径
    :return:
    """
    # 临时目录，自动删除
    with tempfile.TemporaryDirectory() as temp_folder:
        filepath = os.path.join(temp_folder, f'{uuid.uuid1()}.pdf')
        callback(filepath)
        with open(filepath, 'rb') as f:
            byte_data = bytes(f.read())
            return byte_data


@app.post('/generate/from-file', description='通过文件生成')
async def generate_from_file(files: List[bytes] = File(),
                             qr_code: str = Form(),
                             doc_no: str = Form(),
                             inventory_code: str = Form(),
                             inventory_name: str = Form(),
                             inventory_spec: str = Form(''),
                             quantity: str = Form(),
                             doc_date: str = Form(''),
                             process_flow: str = Form('')):
    try:
        processor = Processor(qr_code, doc_no, inventory_code, inventory_name, inventory_spec, quantity, doc_date, process_flow,
                              source_files=files,
                              horizontal_layout=True)

        byte_data = read_from_temp_file(lambda x: processor.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
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
    process_flow: str


@app.post('/generate/from-url', description='通过文件url生成')
async def generate_from_url(item: Item):
    try:
        processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name,
                              item.inventory_spec, item.quantity, item.doc_date, item.process_flow,
                              source_urls=item.file_urls,
                              horizontal_layout=True)

        byte_data = read_from_temp_file(lambda x: processor.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/generate/from-urls', description='通过多个文件url生成')
async def generate_from_url(items: List[Item]):
    try:
        documents = []
        for item in items:
            processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name,
                                  item.inventory_spec, item.quantity, item.doc_date, item.process_flow,
                                  source_urls=item.file_urls,
                                  horizontal_layout=True)
            document = processor.generate_document()
            documents.append(document)
        combiner = Combiner(documents)

        byte_data = read_from_temp_file(lambda x: combiner.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=merge-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
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


def _generate_document_thread(index, item, request, process_bar):
    processor = Processor(item.qr_code, item.doc_no, item.inventory_code, item.inventory_name,
                          item.inventory_spec, item.quantity, item.doc_date, item.process_flow,
                          source_urls=item.file_urls,
                          horizontal_layout=True)
    document = processor.generate_document()
    if request.process_url:
        process_data = {'total': len(request.items), 'complete': index + 1, 'request_id': request.request_id}
        thread = threading.Thread(target=async_post_process, args=(request.process_url, process_data))
        thread.start()
    process_bar.update(1)
    return document


def async_generated_with_callback(call_item: CallItem):
    """
    异步生成
    :param call_item:
    :return:
    """
    try:
        process_bar = tqdm(total=len(call_item.items))
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            begin_time = time.time()
            futures = []
            for index, item in enumerate(call_item.items):
                future = pool.submit(_generate_document_thread, index, item, call_item, process_bar)
                futures.append(future)
            documents = []
            for future in as_completed(futures):  # 并发执行
                pass
            for future in futures:
                documents.append(future.result())
            process_bar.close()
            logger.info(f'requestId:{call_item.request_id} 处理{len(documents)}个PDF耗时: {time.time() - begin_time}')
            begin_time = time.time()
            combiner = Combiner(documents)
            bytes = read_from_temp_file(lambda x: combiner.save_to_filepath(x))
            logger.info(f'requestId:{call_item.request_id} 合并{len(documents)}个PDF耗时: {time.time() - begin_time}')
            files = {'file': (f'result-{int(time.time())}.pdf', bytes, 'application/pdf')}
            data = {'request_id': call_item.request_id, 'total': len(call_item.items)}
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
    print('文档地址: http://localhost:8000/docs')
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)
