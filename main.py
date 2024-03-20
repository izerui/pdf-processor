import concurrent
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import fitz
import httpx
import uvicorn
from fastapi import FastAPI, Response, File, Form, UploadFile
from fastapi.responses import ORJSONResponse
from httpx import Timeout
from pydantic import BaseModel
from tqdm import tqdm

from pdf import Processor, Combiner
from utils import logger, read_temp_file_instant

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


@app.post('/generate/from-files', description='通过文件生成(仅做测试)')
async def generate_from_file(files: List[bytes] = File(),
                             qr_code: str = Form('code001', description='二维码内容'),
                             doc_no: str = Form('SO202305240001', description='工单号'),
                             inventory_code: str = Form('20120527003_001', description='货品编码'),
                             inventory_name: str = Form('ios数据线_001', description='货品名称'),
                             inventory_spec: str = Form('型号008_001', description='规格型号'),
                             quantity: str = Form(12, description='数量'),
                             doc_date: str = Form('2024-02-02', description='交期'),
                             process_flow: str = Form('生产->包装->装箱', description='工艺路线'),
                             marks_str: str = Form(
                                 '22➍23➍182➍103➍https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg',
                                 description='多文件,多页,多遮罩区域: 坐标及图片url以➍连接[x0➍y0➍x1➍y1➍img_url], 多个遮罩块以➌连接[rect0➌rect1], 每页的遮罩数组以➋连接[page0➋page1], 每个文件以➊连接[file0➊file1]!'),
                             rotates_str: str = Form('', description='多文件,每页的旋转角度, 每页以➋连接, 每文件以➊连接')):
    try:
        processor = Processor(source_files=files)
        processor.set_generate_config(
            qr_code=qr_code,
            doc_no=doc_no,
            inventory_code=inventory_code,
            inventory_name=inventory_name,
            inventory_spec=inventory_spec,
            quantity=quantity,
            doc_date=doc_date,
            process_flow=process_flow,
            marks_str=marks_str,
            rotates_str=rotates_str,
            horizontal_layout=True
        )
        byte_data = read_temp_file_instant(lambda x: processor.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/rotate/from-files', description='通过文件列表获取旋转角度(仅做测试)', response_class=ORJSONResponse)
async def rotate_from_file(files: List[bytes] = File()):
    try:
        processor = Processor(source_files=files)
        docs_rotates = processor.get_rotates_from_docs()
        return ORJSONResponse(docs_rotates)
    except Exception as err:
        print(repr(err))
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/rotate/from-urls', description='通过文件url列表获取旋转角度', response_class=ORJSONResponse)
async def rotate_from_urls(file_urls: List[str]):
    try:
        processor = Processor(source_urls=file_urls)
        docs_rotates = processor.get_rotates_from_docs()
        return ORJSONResponse(docs_rotates)
    except Exception as err:
        print(repr(err))
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


class Item(BaseModel):
    file_urls: List[str]
    item_id: str
    qr_code: str
    doc_no: str
    inventory_code: str
    inventory_name: str
    inventory_spec: str | None = None
    quantity: str
    doc_date: str
    process_flow: str | None = None
    marks_str: str | None = None
    rotates_str: str | None = None


@app.post('/generate/from-url', description='通过文件url生成')
async def generate_from_url(item: Item):
    try:
        processor = Processor(source_urls=item.file_urls)
        processor.set_generate_config(
            qr_code=item.qr_code,
            doc_no=item.doc_no,
            inventory_code=item.inventory_code,
            inventory_name=item.inventory_name,
            inventory_spec=item.inventory_spec,
            quantity=item.quantity,
            doc_date=item.doc_date,
            process_flow=item.process_flow,
            marks_str=item.marks_str,
            rotates_str=item.rotates_str,
            horizontal_layout=True
        )
        byte_data = read_temp_file_instant(lambda x: processor.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/generate/from-urls', description='通过多个item(单个item可能包含多个文件)生成')
async def generate_from_url(items: List[Item]):
    try:
        documents = []
        for item in items:
            processor = Processor(source_urls=item.file_urls)
            processor.set_generate_config(
                qr_code=item.qr_code,
                doc_no=item.doc_no,
                inventory_code=item.inventory_code,
                inventory_name=item.inventory_name,
                inventory_spec=item.inventory_spec,
                quantity=item.quantity,
                doc_date=item.doc_date,
                process_flow=item.process_flow,
                marks_str=item.marks_str,
                rotates_str=item.rotates_str,
                horizontal_layout=True
            )
            document = processor.generate_document()
            documents.append(document)
        combiner = Combiner(documents)

        byte_data = read_temp_file_instant(lambda x: combiner.save_to_filepath(x))
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=merge-{int(time.time())}.pdf'}
        return Response(content=byte_data, headers=headers, media_type="application/pdf")
    except Exception as err:
        print(repr(err))
        logger.exception(err)
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
    """
    处理单个pdf
    :param index:
    :param item:
    :param request:
    :param process_bar:
    :return:
    """
    processor = Processor(source_urls=item.file_urls)
    success_state = True
    error_msg = None
    try:
        processor.set_generate_config(
            qr_code=item.qr_code,
            doc_no=item.doc_no,
            inventory_code=item.inventory_code,
            inventory_name=item.inventory_name,
            inventory_spec=item.inventory_spec,
            quantity=item.quantity,
            doc_date=item.doc_date,
            process_flow=item.process_flow,
            marks_str=item.marks_str,
            rotates_str=item.rotates_str,
            horizontal_layout=True
        )
        document = processor.generate_document()
        return document
    except BaseException as error:
        error_msg = repr(error)
        logger.warn(error_msg)
        success_state = False
        return None
    finally:
        process_bar.update(1)
        if request.process_url:
            process_data = {'total': len(request.items), 'index': index, 'request_id': request.request_id,
                            'item_id': item.item_id, 'success': success_state, 'err_msg': error_msg}
            thread = threading.Thread(target=async_post_process, args=(request.process_url, process_data))
            thread.start()


def async_generated_with_callback(call_item: CallItem):
    """
    异步生成item的pdf，并合并推送到callbackurl
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
            for future in futures:  # 按原始顺序添加页
                documents.append(future.result())
            process_bar.close()
            logger.info(
                f'合并pdf: requestId:{call_item.request_id} 处理{len(documents)}个PDF耗时: {time.time() - begin_time}')
            begin_time = time.time()
            combiner = Combiner(documents)
            bytes = read_temp_file_instant(lambda x: combiner.save_to_filepath(x))
            logger.info(f'requestId:{call_item.request_id} 合并{len(documents)}个PDF耗时: {time.time() - begin_time}')
            files = {'file': (f'result-{int(time.time())}.pdf', bytes, 'application/pdf')}
            data = {'request_id': call_item.request_id, 'total': len(call_item.items)}
            httpx.post(call_item.callback_url, files=files, data=data)
    except Exception as err:
        print(f'合并pdf出错: {repr(err)}')
        logger.exception(err)
        data = {'request_id': call_item.request_id, 'err_msg': repr(err)}
        httpx.post(call_item.callback_url, data=data)


@app.post('/callback/file', description='接收文件上传')
async def generate_from_file(file: UploadFile = File(), request_id: str = Form()):
    print('接收到示例文件上传: ', request_id, file.filename, file.size)
    return Response(content=request_id, media_type="text/html")


def async_post_process(url, data):
    if url:
        httpx.post(url, data=data, timeout=Timeout(timeout=30.0, connect=10.0))


if __name__ == "__main__":
    # 解决 fitz 新旧别名映射的bug
    fitz.restore_aliases()
    print('文档地址: http://localhost:8000/docs')
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)
