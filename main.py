import concurrent.futures
import datetime
import threading
import time
import tracemalloc
from typing import List

import httpx
import pymupdf
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Response, UploadFile, Form
from fastapi.responses import ORJSONResponse
from httpx import Timeout
from pymupdf import Document

from model import File, SimpleFile, Item, ItemsRequest, CallbackProcess, FileRequest, urlsRequest
from model.request import ThumbnailRequest, CallbackThumbnail
from pdf import Reader, Processor
from support import logger, logged, QiniuClient, get_url_content_retry

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


@app.post('/file/upload-url', summary='测试示例-上传文件到测试公有空间并返回url等信息')
async def file_url(file: UploadFile):
    profile = 'test'
    client = QiniuClient()
    data = await file.read()
    key = f'pdf-processor/source/{datetime.datetime.now().strftime("%Y-%m-%d")}/{file.filename}'
    rest = client.upload_data(profile, True, key, data)
    rest['url'] = client.get_download_url(profile, True, key)
    print(rest)
    return Response(content=rest['url'], media_type="text/html")


@logged(desc='接收url转pdf')
@app.post('/convert/from-url', summary='接收url转成pdf文档')
def generate_from_urls(file_url: str):
    try:
        data = get_url_content_retry(file_url)
        doc = pymupdf.open("pdf", data)
        if not doc.is_pdf:
            doc = pymupdf.open('pdf', doc.convert_to_pdf())
        pdf_bytes = doc.tobytes(garbage=4, deflate=True, use_objstms=1)
        doc.close()
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=convert-{int(time.perf_counter() * 1000)}.pdf'}
        return Response(content=pdf_bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/rotations/from-urls', summary='通过文件url列表获取旋转角度', response_class=ORJSONResponse)
def rotate_from_urls(files: List[SimpleFile]):
    try:
        results = []
        processor = Processor()
        down_files = list(map(lambda x: File(name=x.name, url=x.url), files))
        url_datas = processor.download_urls_from_files(down_files)
        for index, file in enumerate(down_files):
            reader: Reader = Reader(url_datas[file.url], False)
            rotations = reader.get_horizontal_transform_rotations()
            file_rotations = {'name': file.name, 'url': file.url, 'rotations': rotations}
            results.append(file_rotations)
        return ORJSONResponse(results)
    except BaseException as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='接收多个文档url，合并成一个文档')
@app.post('/merge/from-urls', summary='接收多个文档url，合并成一个文档')
def generate_from_urls(file_urls: List[str]):
    try:
        processor = Processor()
        target_doc = processor.merge_url_pdfs(file_urls)
        target_doc_bytes = processor.get_doc_bytes_and_close(target_doc, auto_close=True)
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=merge-{int(time.perf_counter() * 1000)}.pdf'}
        return Response(content=target_doc_bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='处理多个pdf文件,并返回结果文档')
@app.post('/generate/from-urls', summary='处理多个pdf文件,并返回结果文档')
def generate_from_urls(items: List[Item]):
    try:
        processor = Processor()
        url_datas = processor.download_urls_from_items(items)
        target_doc = processor.generate_from_items_without_close(items, url_datas, None)
        target_doc_bytes = processor.get_doc_bytes_and_close(target_doc, auto_close=True)
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=result-{int(time.perf_counter() * 1000)}.pdf'}
        return Response(content=target_doc_bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='接收多个文档url，合并成一个文档，并回调通知')
@app.post('/merge/async-callback-from-urls', summary='接收多个文档url，合并成一个文档')
def merge_from_urls(urls_request: urlsRequest):
    try:

        def item_callback(index, doc):
            if urls_request.process_url:
                process_data = {'total': len(urls_request.urls),
                                'index': index,
                                'request_id': urls_request.request_id,
                                'success': True,
                                'err_msg': None}
                thread = threading.Thread(target=async_post_process, args=(urls_request.process_url, process_data))
                thread.start()
                pass

        def async_post_process(url, data):
            if url:
                httpx.post(url, json=data, timeout=Timeout(timeout=60.0, connect=30.0))

        def async_merge_and_callback(callback_urls: urlsRequest):
            """
            异步开启合并线程
            """
            try:
                processor = Processor()
                target_doc = processor.merge_url_pdfs(callback_urls.urls, item_callback)
                target_doc_bytes = processor.get_doc_bytes_and_close(target_doc, auto_close=True)
                files = {'file': (f'result-{int(time.perf_counter() * 1000)}.pdf', target_doc_bytes, 'application/pdf')}
                data = {'request_id': callback_urls.request_id, 'total': len(callback_urls.urls)}
                # 暂时不考虑上传结果接口异常,出现异常，由业务方重新调用即可。
                response = httpx.post(callback_urls.callback_url, files=files, data=data,
                                      timeout=Timeout(timeout=60.0, connect=30.0))
                if response.is_success:
                    logger.info(f'【上传pdf返回结果】: {response.content}')

            except BaseException as err:
                logger.exception(err)
                data = {'request_id': callback_urls.request_id, 'total': len(callback_urls.items),
                        'err_msg': repr(err)}
                httpx.post(callback_urls.callback_url, data=data, timeout=Timeout(timeout=60.0, connect=30.0))
                pass

        thread = threading.Thread(target=async_merge_and_callback, args=(urls_request,))
        thread.start()
        return Response(content=f'已经开始合并,待合并完成后回调地址: {urls_request.callback_url}',
                        media_type="text/html")
    except Exception as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='处理多个pdf文件,并回调通知')
@app.post('/generate/async-callback-from-urls', summary='处理多个pdf文件,并回调通知')
def callback_from_urls(items_request: ItemsRequest):
    try:

        def item_callback(index: int, item: Item, doc: Document, exception):
            if items_request.process_url:
                process_data = {'total': len(items_request.items), 'index': index,
                                'request_id': items_request.request_id,
                                'item_id': item.item_id, 'success': True, 'err_msg': None}
                if exception:
                    process_data['success'] = False
                    process_data['err_msg'] = repr(exception)
                thread = threading.Thread(target=async_post_process, args=(items_request.process_url, process_data))
                thread.start()
                pass

        def async_post_process(url, data):
            logger.info(f'【进度通知】{repr(data)}')
            if url:
                httpx.post(url, json=data, timeout=Timeout(timeout=60.0, connect=30.0))

        def async_generate_and_callback(items_request: ItemsRequest):
            """
            异步开启处理线程
            """
            try:
                processor = Processor()
                url_datas = processor.download_urls_from_items(items_request.items)
                target_doc = processor.generate_from_items_without_close(items_request.items, url_datas, item_callback)
                target_doc_bytes = processor.get_doc_bytes_and_close(target_doc, auto_close=True)
                files = {'file': (f'result-{int(time.perf_counter() * 1000)}.pdf', target_doc_bytes, 'application/pdf')}
                data = {'request_id': items_request.request_id, 'total': len(items_request.items)}
                # 暂时不考虑上传结果接口异常,出现异常，由业务方重新调用即可。
                logger.info(f'【开始上传结果文档到业务应用】')
                response = httpx.post(items_request.callback_url, files=files, data=data,
                                      timeout=Timeout(timeout=300.0, connect=30.0))
                if response.is_success:
                    logger.info(f'【上传pdf返回结果】: {response.content}')

            except BaseException as err:
                logger.exception(err)
                data = {'request_id': items_request.request_id, 'total': len(items_request.items),
                        'err_msg': repr(err)}
                httpx.post(items_request.callback_url, data=data, timeout=Timeout(timeout=60.0, connect=30.0))
                pass

        thread = threading.Thread(target=async_generate_and_callback, args=(items_request,))
        thread.start()
        return Response(content=f'已经开始处理,待完成后回调地址: {items_request.callback_url}', media_type="text/html")
    except BaseException as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='处理单个源pdf文件，返回加遮罩后的源文档')
@app.post('/generate/from-file', summary='处理单个pdf文件，返回加遮罩后的文档')
def generate_from_file(file: File):
    try:
        processor = Processor()
        url_datas = processor.download_urls_from_files([file])
        file_doc_bytes = processor.generate_source_bytes_from_file(file, url_datas)
        headers = {"content-type": "application/pdf",
                   "content-disposition": f'attachment;filename=file-{int(time.perf_counter() * 1000)}.pdf'}
        return Response(content=file_doc_bytes, headers=headers, media_type="application/pdf")
    except Exception as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='处理单个源pdf文件, 加遮罩后, 异步回调')
@app.post('/generate/async-callback-from-file', summary='处理单个pdf文件, 加遮罩后, 异步回调')
def callback_from_urls(file_request: FileRequest):
    try:

        def async_post_process(url, data):
            if url:
                httpx.post(url, json=data, timeout=Timeout(timeout=60.0, connect=30.0))

        def async_generate_and_callback(callback_items: ItemsRequest):
            """
            异步开启处理线程
            """
            try:
                processor = Processor()
                url_datas = processor.download_urls_from_files([file_request.file])
                file_doc_bytes = processor.generate_source_bytes_from_file(file_request.file, url_datas)
                files = {'file': (f'file-{int(time.perf_counter() * 1000)}.pdf', file_doc_bytes, 'application/pdf')}
                data = {'request_id': callback_items.request_id}
                # 暂时不考虑上传结果接口异常,出现异常，由业务方重新调用即可。
                response = httpx.post(callback_items.callback_url, files=files, data=data,
                                      timeout=Timeout(timeout=60.0, connect=30.0))
                if response.is_success:
                    logger.info(f'【上传单个处理的原pdf返回结果】: {response.content}')

            except BaseException as err:
                logger.exception(err)
                data = {'request_id': callback_items.request_id, 'err_msg': repr(err)}
                httpx.post(callback_items.callback_url, data=data, timeout=Timeout(timeout=60.0, connect=30.0))
                pass

        thread = threading.Thread(target=async_generate_and_callback, args=(file_request,))
        thread.start()
        return Response(content=f'已经开始处理,待完成后回调地址: {file_request.callback_url}', media_type="text/html")
    except BaseException as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@logged(desc='接收多个pdf文件,获取每个pdf文件的首页截图并异步通知回调')
@app.post('/thumbnail/async-callback-from-urls', summary='接收多个pdf文件,获取每个pdf文件的首页截图并异步通知回调')
def thumbnail_callback_from_urls(thumbnail: ThumbnailRequest):
    try:
        def get_first_page_thumbnail_base64(url: str, url_datas: dict):
            reader = Reader(url_datas[url])
            image_base64 = reader.get_first_page_thumbnail_base64()
            return {
                'url': url,
                'image_base64': image_base64,
            }

        def async_thumbnail_and_callback(thumbnail: ThumbnailRequest):
            """
            异步开启处理线程
            """
            try:
                processor = Processor()
                url_datas = processor.download_urls(thumbnail.urls)
                url_images = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                    futures = []
                    for url in thumbnail.urls:
                        futures.append(pool.submit(get_first_page_thumbnail_base64, url, url_datas))
                    for future in concurrent.futures.as_completed(futures):  # 并发执行
                        exception = future.exception()
                        if exception:
                            logger.exception(exception)
                            raise exception
                        else:
                            url_images.append(future.result())
                        pass

                data = {
                    'request_id': thumbnail.request_id,
                    'url_images': url_images
                }
                response = httpx.post(thumbnail.callback_url, json=data, timeout=Timeout(timeout=60.0, connect=30.0))
                if response.is_success:
                    logger.info(f'【上传多个pdf文件首页的缩略图返回结果】: {response.content}')

            except BaseException as err:
                logger.exception(err)
                data = {'request_id': thumbnail.request_id, 'err_msg': repr(err)}
                httpx.post(thumbnail.callback_url, data=data, timeout=Timeout(timeout=60.0, connect=30.0))
                pass

        thread = threading.Thread(target=async_thumbnail_and_callback, args=(thumbnail,))
        thread.start()
        return Response(content=f'已经开始处理,待完成后回调地址: {thumbnail.callback_url}', media_type="text/html")
    except BaseException as err:
        logger.exception(err)
        return Response(content=repr(err), media_type="text/html", status_code=500)


@app.post('/callback/process', summary='回调示例-接收进度信息')
def callback_process(callback_process: CallbackProcess):
    logger.info(
        f'<--- 【接收到处理进度】: 共{callback_process.total}个item, 当前第{callback_process.index}个, request_id:{callback_process.request_id}, item_id:{callback_process.item_id} success: {callback_process.success} err_msg:{callback_process.err_msg}')
    return Response(content='success', media_type="text/html")


@app.post('/callback/thumbnail', summary='回调示例-接收缩略图信息')
def callback_process(callback_thumbnail: CallbackThumbnail):
    logger.info(
        f'<--- 【接收到缩略图】: 共{len(callback_thumbnail.url_images)}个缩略图, 内容: {callback_thumbnail.url_images} request_id:{callback_thumbnail.request_id}, err_msg:{callback_thumbnail.err_msg}')
    return Response(content='success', media_type="text/html")


@app.post('/callback/file', summary='回调示例-接收文件上传')
async def callback_file(file: UploadFile | None = None,
                        request_id: str | None = Form(None),
                        total: int | None = Form(None),
                        err_msg: str | None = Form(None)):
    if file:
        logger.info(f'<--- 【接收到回调文件】: request_id:{request_id} filename:{file.filename} filesize:{file.size}')
        with open(f'/Users/liuyuhua/Downloads/pdf/{file.filename}', 'wb') as f:
            data = await file.read()
            f.write(data)
    else:
        print(f'<--- 【接收到回调文件】: request_id:{request_id} 错误信息:{err_msg}')
    return Response(content='success', media_type="text/html")


def start_memory_monitor():
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    logger.info('==================================内存分析==================================')
    logger.info("| [ Top 10 ]")
    for stat in top_stats[:10]:
        logger.info(f'| {stat}')


tracemalloc.start()
scheduler = BackgroundScheduler()
scheduler.add_job(start_memory_monitor, 'interval', seconds=300, replace_existing=True)
scheduler.start()

if __name__ == "__main__":
    # 解决 pymupdf 新旧别名映射的bug
    pymupdf.restore_aliases()
    print('文档地址: http://localhost:8000/docs')
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)
