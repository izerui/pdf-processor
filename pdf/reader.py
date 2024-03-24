import time

from fitz import Document, Page, fitz

from model import File
from support import logger, get_url_content_retry, log_time, logged


class Reader(object):
    """
    pdf读取器
    """

    def __init__(self, bytes: bytes):
        """
        构造函数
        :param bytes: 单个pdf对象的内容字节数组
        """
        self.doc = fitz.open("pdf", bytes)

    async def get_doc_by_url(self, url: str) -> Document:
        """
        通过url下载pdf，并返回document对象
        :param url: pdf文件下载url
        :return: document
        """
        response = await get_url_content_retry(url)
        if not response.is_success:
            raise IOError(f'文件下载失败, url: {url}')
        pdf: Document = fitz.open("pdf", response.content)
        return pdf

    def __del__(self):
        try:
            if self.doc:
                self.doc.close()
        except BaseException as err:
            logger.warn(repr(err))
            pass

    # @logged(desc='获取单个页面转成横版所需的角度')
    def get_page_roration_for_cropbox(self, index: int) -> float:
        """
        通过指定索引的页面,获取其针对未旋转前的`cropbox`区域,转成横版所需的角度
        :param index: 页面索引
        :return: 旋转角度
        """

        # Maxtrix 解析: https://pymupdf.readthedocs.io/en/latest/matrix.html
        # 其他解析(通俗易懂):
        # * https://docs.godotengine.org/zh-cn/4.x/tutorials/math/matrices_and_transforms.html (这个先看完，把变换矩阵理解透)
        # * https://github.com/alvarto/blog/issues/1  (建议看这个更明白)
        # * https://docs.aspose.com/svg/zh/net/drawing-basics/transformation-matrix/  (这个可以尝试自己获取一个svg进行修改测试) 参看文件: `transform2d.svg`
        # a: x方向缩放(宽度)。例如，如果值为0.5，则将宽度缩小2倍。如果a < 0，将(额外地)发生左右翻转。
        # b: 产生剪切效果: 每个点(x, y)将变成点(x, y - b * x)。因此，水平线会“倾斜”。
        # c: 产生剪切效果: 每个点(x, y)都会变成点(x - c * y, y)，因此垂直线会“倾斜”。
        # d: y方向缩放(高度)。例如，如果值为1.5，则将高度拉伸50 %。如果d < 0，将(额外地)发生上下翻转。
        # e: 产生水平偏移效果: 每个Point(x, y)都会变成Point(x + e, y)， e的正(负)值会向右(左)偏移。
        # f: 产生垂直位移效应: 每个Point(x, y)都会变成Point(x, y - f)， f的正(负)值会向下(上)移动。
        # 其他一些资料:
        # 四元数在线可视化转换网站: https://quaternions.online/
        # 三维在线旋转变换网站: https://www.andre-gaschler.com/rotationconverter/
        # 二维 Rotation Conversion Tool: https://danceswithcode.net/engineeringnotes/quaternions/conversion_tool.html

        page: Page = self.doc[index]

        # 注意： cropbox 为原始页面，  page.bound() 为set_rotation后的看到的页面，所以不能用bound()、rect 因为外部使用页面拼接的时候是使用原始页面，最后合并时候才旋转
        # print(
        #     f'''文件{self.file.name}  第{index + 1}页
        #     rect cropbox mediabox 是否一致: {page.rect == page.cropbox == page.mediabox}
        #     原始矩形宽:{page.cropbox.width}  高:{page.cropbox.height}  旋转角度:{page.rotation}
        #     旋转矩阵:{page.rotation_matrix}
        #     变换矩阵:{page.transformation_matrix}''')

        # 原页面是否是横版
        is_horizontal: bool = page.cropbox.width > page.cropbox.height
        rotate_for_cropbox = 0
        # 如果原始页面是横版，不做90转换, 如果原始页面是竖版，需要旋转90度的奇数倍数
        if not is_horizontal:
            # 如果默认旋转角度后看到的页面是横版，则使用默认的旋转角度
            if (int(page.rotation / 90)) % 2 == 1:
                rotate_for_cropbox = page.rotation
            else:
                # 否则，竖版的话，在原始旋转角度的基础上再次旋转90度
                rotate_for_cropbox = page.rotation + 90

                # 如果发生了基于x轴的上线翻转，则额外加180度
        if page.rotation_matrix.d < 0:
            rotate_for_cropbox += 180

        # if rotate_for_cropbox != 0:
        #     print(f'    > 转横版,需旋转 {rotate_for_cropbox}')
        return rotate_for_cropbox

    @logged(desc='获取所有页面转成横版所需的角度')
    def get_rotations_for_cropbox(self) -> list[float]:
        """
        获取每页针对未旋转前的`cropbox`区域,转成横版所需的角度
        :return: 旋转角度数组
        """
        # 如果不是pdf，一般情况下都是图片，所以默认返回0
        if not self.doc.is_pdf:
            return [0.0]
        rotations = []
        for index, page in enumerate(self.doc):
            rotations.append(self.get_page_roration_for_cropbox(index))
        return rotations
