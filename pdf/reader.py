from pymupdf import Document
from pymupdf import Page, pymupdf

from support import logger, logged, get_text_rotation_from_dir


class Reader(object):
    """
    pdf读取器, 会跟随实例消亡自动关闭文档
    """

    def __init__(self, data: bytes, is_convert: bool = False):
        """
        构造函数
        :param data: 单个pdf对象的内容字节数组
        :param is_convert: 单个pdf对象的内容字节数组
        """
        self.doc = pymupdf.open("pdf", data)
        # 如果doc不是pdf或者强制进行二次转换
        if is_convert or not self.doc.is_pdf:
            self.doc = self.convert_doc(self.doc)

    def get_doc_without_close(self) -> Document:
        """
        获取当前的doc文档
        """
        return self.doc

    # @logged(desc='重新包装当前的doc')
    def convert_doc(self, document: Document) -> Document:
        """
        重新包装转换当前的doc,避免一些识别处理问题, 注意这里转换后文档页面的rotation会重置为0
        :return:
        """
        try:
            # 转换前先记录下原始pdf的rotations, 因为发生`convert_to_pdf`后，旋转角度会丢失
            rotations = []
            for index, page in enumerate(document):
                # 考虑下面两个方法的区别：貌似第二个快，但是会清理不完整，导致坐标还是存在偏差
                # 1. https://pymupdf.readthedocs.io/en/latest/functions.html#Page.clean_contents
                # 2. https://pymupdf.readthedocs.io/en/latest/functions.html#Page.wrap_contents
                # page.wrap_contents()

                # 循环每页清理：
                # 清理并连接与此页面关联的所有contents对象
                # 参考：https: // pymupdf.readthedocs.io / en / latest / functions.html  # Page.clean_contents
                # page.clean_contents()
                rotations.append(page.rotation)

            # 将原pdf重新转换下，保证注释可见
            # 问题fixed: https://pymupdf.readthedocs.io/en/latest/page.html#f6
            convert_pdf = pymupdf.open('pdf', document.convert_to_pdf())
            # 还原转换前的旋转角度
            for index, page in enumerate(document):
                page.set_rotation(rotations[index])
            return convert_pdf
        except BaseException as e:
            logger.warn(f'重新包装转换失败: {repr(e)}')
            return convert_pdf

    def __del__(self):
        try:
            self.doc.close()
        except BaseException as err:
            logger.warn(f'关闭文件: {repr(err)}')
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

        #################  优化页面的上下颠倒的方向问题 begin #############
        # 将页面设置成计算的旋转角度，然后通过字体的方向，自动矫正
        # 暂时记录原始旋转角度
        # _rotation = page.rotation
        # page.set_rotation(rotate_for_cropbox)
        # # 正确的字体方向个数
        # right_rotation_count = 0
        # # 上下颠倒的字体方向个数
        # wrong_rotation_count = 0
        # # 通过获取字体的方向，判断是否上下颠倒了
        # blocks = page.get_textpage().extractDICT()['blocks']
        # for block in blocks:
        #     lines = block['lines']
        #     for line in lines:
        #         # 书写方向及书写方式（横/竖） 0 = horizontal, 1 = vertical
        #         line_wmode = line['wmode']
        #         line_rotation = get_text_rotation_from_dir(line['dir'])
        #         # 90度的字体排除，因为这些可能是一些图示标记字体，只判断是否上下颠倒的字体
        #         if line_rotation == 0:
        #             right_rotation_count += 1
        #         elif line_rotation == 180:
        #             wrong_rotation_count += 1
        # # 如果错误的字体方向个数大于正确的字体方向个数，则表示页面按上面计算后的旋转后为上下颠倒的页面
        # if wrong_rotation_count > right_rotation_count:
        #     if rotate_for_cropbox < 180:
        #         rotate_for_cropbox += 180
        #     else:
        #         rotate_for_cropbox -= 180
        # # 还原原始旋转角度
        # page.set_rotation(_rotation)
        #################  优化页面的上下颠倒的方向问题 end #############

        return rotate_for_cropbox

    @logged(desc='获取所有页面转成横版所需的角度')
    def get_horizontal_transform_rotations(self, input_rotations: list[float] = None) -> list[float]:
        """
        获取每页针对未旋转前的`cropbox`区域,转成横版所需的角度
        :return: 旋转角度数组
        """
        # 如果不是pdf，一般情况下都是图片，所以默认返回0
        if not self.doc.is_pdf:
            return [0]
        rotations = []
        for index, page in enumerate(self.doc):
            if input_rotations and len(input_rotations) > index:
                rotations.append(input_rotations[index])
            else:
                rotations.append(self.get_page_roration_for_cropbox(index))
        return rotations
