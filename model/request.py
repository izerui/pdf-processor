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
        examples=['https://tfile.yj2025.com/pdf-processor/source/2024-03-28/2.jpg',
                  'https://cdn.pixabay.com/photo/2023/11/09/19/36/zoo-8378189_1280.jpg']
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
        title="文件名称", max_length=200, examples=['示例.pdf']
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
        None, title="旋转角度", examples=[[]]
    )


class ItemRender(BaseModel):
    label: str = Field(
        None, title='标签', examples=['标签标签:']
    )
    value: str = Field(
        None, title='输出内容', examples=[
            '输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容输出内容']
    )
    # label_width: float = Field(
    #     default=None, title='标签宽度,三列建议: 两个字60、三个字80', examples=[60.0, 80.0]
    # )
    # value_width: float = Field(
    #     default=None, title='内容宽度,两列建议列宽分别为 600, 三列建议列宽分别为: 330、320、400, 独立行宽可为800',
    #     examples=[330.0, 320.0, 400.0, 800.0]
    # )


class Item(BaseModel):
    # 传入的原始pdf文件对象列表
    files: List[File]

    header_show: str = Field(
        None, title='是否显示头部区域布局',
        examples=['true', 'false']
    )

    header_model: str = Field(
        None, title='头部区域表单模版',
        examples=['Header331', 'Header333', 'Header221', 'Header222', 'Header333', 'Header441', 'Header551']
    )

    header_layout: str = Field(
        None, title='头部区域布局',
        examples=['top', 'bottom']
    )

    qr_code_size: int | None = Field(
        default=180, title='二维码宽度', examples=[180]
    )

    header_padding_left: int = Field(
        default=0, title='头部区域距离左侧间隙,或者理解为右偏移量', examples=[0]
    )

    # 序号
    item_no: str | None = Field(
        None, title='序号', examples=['29']
    )

    # 当前请求的item的标识ID
    item_id: str | None = Field(
        None, title='当前请求的item的标识ID', examples=['当前请求的item的标识ID']
    )

    # 二维码内容
    qr_code: str | None = Field(
        None, title='二维码内容', examples=['二维码内容']
    )

    form_item1: ItemRender | None = Field(
        None, title='表单项1'
    )
    form_item2: ItemRender | None = Field(
        None, title='表单项2'
    )
    form_item3: ItemRender | None = Field(
        None, title='表单项3'
    )
    form_item4: ItemRender | None = Field(
        None, title='表单项4'
    )
    form_item5: ItemRender | None = Field(
        None, title='表单项5'
    )
    form_item6: ItemRender | None = Field(
        None, title='表单项6'
    )
    form_item7: ItemRender | None = Field(
        None, title='表单项7'
    )
    form_item8: ItemRender | None = Field(
        None, title='表单项8'
    )
    form_item9: ItemRender | None = Field(
        None, title='表单项9'
    )
    form_item10: ItemRender | None = Field(
        None, title='表单项9'
    )
    form_item11: ItemRender | None = Field(
        None, title='表单项9'
    )


class FileRequest(BaseModel):
    file: File
    request_id: str
    callback_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/file']
    )


class ThumbnailRequest(BaseModel):
    urls: List[str] = Field(
        None, examples=[['https://file.yj2025.com/CH3600-1-M04003A%20搬运爪安装板-长.pdf', 'https://file.yj2025.com/003.pdf']]
    )
    request_id: str
    callback_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/thumbnail']
    )


class urlsRequest(BaseModel):
    urls: List[str]
    request_id: str
    process_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/process']
    )
    callback_url: str | None = Field(
        None, examples=['http://localhost:8000/callback/file']
    )


class ItemsRequest(BaseModel):
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


class CallbackThumbnail(BaseModel):
    request_id: str | None = None
    url_images: list | None = None
    err_msg: str | None = None
