import random
from typing import List

import fitz
from pydantic import BaseModel, Field


class Mark(BaseModel):
    """
    单个矩形遮罩区域
    坐标参考: 相对于pdf左上角的坐标区域
    """
    # 左上角x坐标
    x0: float = Field(
        title="左上角x坐标", examples=[0]
    )
    # 左上角y坐标
    y0: float = Field(
        title="左上角y坐标", examples=[0]
    )
    # 右下角x坐标
    x1: float = Field(
        title="右下角x坐标", examples=[200]
    )
    # 右下角y坐标
    y1: float = Field(
        title="右下角y坐标", examples=[300]
    )
    # 矩形区域如果是图片，则为图片网络url地址
    image_url: str | None = Field(
        None,
        title="矩形区域如果是图片，则为图片网络url地址,否则留空",
        examples=['https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg']
    )



class SimpleFile(BaseModel):
    # 文件名
    name: str = Field(
        title="文件名称", max_length=200, examples=['多页.pdf']
    )

    # pdf文件url地址
    url: str = Field(
        title="文件url", max_length=2000, examples=['https://file.yj2025.com/003.pdf']
    )


class File(BaseModel):
    # 文件名
    name: str = Field(
        title="文件名称", max_length=200, examples=['单页.pdf']
    )

    # pdf文件url地址
    url: str = Field(
        title="文件url", max_length=2000, examples=['https://file.yj2025.com/CH3600-1-M04003A%20搬运爪安装板-长.pdf']
    )

    # 每个页面统一的缩放大小 0 ~ 1 (0.8 表示缩小1/4)
    zoom: float | None = Field(
        None, title="页面缩放大小 0 ~ 1 (0.8 表示缩小1/4)", examples=[1]
    )

    # 每个页面都一样的遮罩区域列表
    marks: List[Mark] | None = Field(
        None, title="每个页面都一样的遮罩区域列表"
    )

    # 每个页面的旋转角度
    rotations: List[int] | None = Field(
        None, title="旋转角度", examples=[[0]]
    )


class Item(BaseModel):
    # 传入的原始pdf文件对象列表
    files: List[File]

    # 序号
    item_no: str = Field(
        None, title='序号', examples=['29']
    )

    # 当前请求的item的标识ID
    item_id: str = Field(
        None, title='当前请求的item的标识ID', examples=['当前请求的item的标识ID']
    )

    # 二维码内容
    qr_code: str = Field(
        None, title='二维码内容', examples=['二维码内容']
    )

    # 工单号
    doc_no: str = Field(
        None, title='工单号', examples=['卧室一个 DOC100']
    )

    # 货品编码
    inventory_code: str = Field(
        None, title='货品编码', examples=['你以为的是 Ivne002，。']
    )

    # 货品名称
    inventory_name: str = Field(
        None, title='货品名称', examples=['货品是 se名称！3']
    )

    # 货品规格型号
    inventory_spec: str | None = Field(
        None, title='货品规格型号', examples=['货品规 *6ds格型号']
    )

    # 数量
    quantity: str = Field(
        None, title='数量', examples=['数量 - 120']
    )

    # 交期
    doc_date: str = Field(
        None, title='交期', examples=['2024年03月24日']
    )

    # 工艺路线
    process_flow: str | None = Field(
        None, title='工艺路线', examples=['工艺路线1 》工艺路线 2']
    )

    def wrap_batch_number_when_qr_string(self):
        """
        如果是测试 传入string则增加不同item之间的批次号
        :return:
        """
        if 'string' == self.qr_code:
            rdm = f'{random.randrange(0, 101, 2)}'
            self.qr_code += rdm
            self.item_id += rdm
            self.doc_no += rdm
            self.inventory_code += rdm
            self.inventory_name += rdm
            self.inventory_spec += rdm
            self.quantity += rdm
            self.doc_date += rdm
            self.process_flow += rdm


class CallbackFile(BaseModel):
    file: File
    request_id: str
    callback_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/file']
    )

class CallbackItems(BaseModel):
    items: List[Item]
    request_id: str
    process_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/process']
    )
    callback_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/file']
    )


class CallbackProcess(BaseModel):
    total: int | None = None
    index: int | None = None
    request_id: str | None = None
    item_id: str | None = None
    success: bool | None = None
    err_msg: str | None = None
