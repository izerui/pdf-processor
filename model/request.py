import random
from typing import List

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
        title="右下角x坐标", examples=[500]
    )
    # 右下角y坐标
    y1: float = Field(
        title="右下角y坐标", examples=[500]
    )
    # 矩形区域如果是图片，则为图片网络url地址
    image_url: str | None = Field(
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

    # 不需要传值,内容会自动通过url下载
    byte_array: bytes | None = Field(
        default=None, title="文件内容字节数组,不需要传值", exclude=True
    )

    # 每个页面统一的缩放大小 0 ~ 1 (0.8 表示缩小1/4)
    zoom: float | None = Field(
        default=1, title="页面缩放大小 0 ~ 1 (0.8 表示缩小1/4)", examples=[1]
    )

    # 每个页面都一样的遮罩区域列表
    marks: List[Mark] | None = Field(
        title="每个页面都一样的遮罩区域列表"
    )

    # 每个页面的旋转角度
    rotations: List[float] | None = Field(
        title="页面缩放大小 0 ~ 1 (0.8 表示缩小1/4)", examples=[[0]]
    )


class Item(BaseModel):
    # 传入的原始pdf文件对象列表
    files: List[File]

    # 当前请求的item的标识ID
    item_id: str = Field(
        title='当前请求的item的标识ID', examples=['当前请求的item的标识ID']
    )

    # 二维码内容
    qr_code: str = Field(
        title='二维码内容', examples=['二维码内容']
    )

    # 工单号
    doc_no: str = Field(
        title='工单号', examples=['卧室一个 DOC100']
    )

    # 货品编码
    inventory_code: str = Field(
        title='货品编码', examples=['你以为的是 Ivne002，。']
    )

    # 货品名称
    inventory_name: str = Field(
        title='货品名称', examples=['货品是 se名称！3']
    )

    # 货品规格型号
    inventory_spec: str | None = Field(
        title='货品规格型号', examples=['货品规 *6ds格型号']
    )

    # 数量
    quantity: str = Field(
        title='数量', examples=['数量 - 120']
    )

    # 交期
    doc_date: str = Field(
        title='交期', examples=['2024年03月24日']
    )

    # 工艺路线
    process_flow: str | None = Field(
        title='工艺路线', examples=['工艺路线1 》工艺路线 2']
    )

    def wrap_batch_number_when_qr_string(self):
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


class CallbackItem(BaseModel):
    items: List[Item]
    request_id: str
    process_url: str = None
    callback_url: str = 'http://localhost:8000/callback/file'
