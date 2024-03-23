from fitz import Document, fitz

from model import File
from pdf import Reader
from support import logger, a4_width, a4_height, header_height

debugger = False


class Editor(Reader):
    """
    pdf修改器
    """

    def __init__(self, file: File):
        """
        构造函数
        :param file: 单个pdf请求对象
        """
        super().__init__(file)

    def wrap_pdf_with_header(self, header_doc: Document, target_doc: Document):
        assert self.doc, '文档未初始化,请调用init_doc()方法初始化!'
        usage_pdf: Document = self.doc
        # 转换前先记录下原始pdf的rotations, 因为发生`convert_to_pdf`后，旋转角度会丢失
        source_page_rotations = []
        for index, page in enumerate(usage_pdf):
            source_page_rotations.append(page.rotation)
        try:
            # 将原pdf重新转换下，保证注释可见
            # 问题fixed: https://pymupdf.readthedocs.io/en/latest/page.html#f6
            usage_pdf = fitz.open('pdf', usage_pdf.convert_to_pdf())
        except BaseException as e:
            logger.warn(f'转换失败: {repr(e)}')
        for p_index, usage_page in enumerate(usage_pdf):
            # 所以需要在二次转化前记录之前每页的旋转角度，并转换后再设置进去, 这里不可删除
            usage_page.set_rotation(source_page_rotations[p_index])
            new_page = target_doc.new_page(width=a4_width, height=a4_height)
            # 顶部区域
            r1 = fitz.Rect(0, 0, a4_width, header_height)
            # 下部区域
            r2 = fitz.Rect(0, header_height, a4_width, a4_height)
            # 将header-pdf首页贴到顶部区域
            new_page.show_pdf_page(r1, header_doc, 0)
            # 转横版 (针对`cropbox`区域，在贴到下部区域前要旋转的角度)
            rotation = 0.0
            # 如果传递进来的有旋转角度,则优先使用(如果传递的旋转角度是针对原始pdf未旋转页面，则不用特殊处理)
            if self.file.rotations and len(self.file.rotations) > p_index:
                rotation = self.file.rotations[p_index]
            else:
                # 获取页面应该回正的旋转角度
                rotation = self.get_page_roration_for_cropbox(p_index)
            # 标记遮罩区域
            # self._mask_page_content(s_index, p_index, usage_page)
            # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
            usage_page.set_rotation(0)
            new_page.show_pdf_page(r2, usage_pdf, p_index, rotate=rotation, keep_proportion=True,
                                   clip=usage_page.cropbox)
            # 清理无效链接，针对页面缩容
            # new_page.clean_contents()

            # 测试用.....
            if debugger:
                # ######### 增加输出原页面(未旋转原始页) 测试用
                # 按原页面宽高设置新页面
                sPage = target_doc.new_page(width=usage_page.cropbox.width, height=usage_page.cropbox.height)
                # 按源页面旋转度数复制
                # cropbox 页面裁剪框
                # fitz.Rect(0, 0, sWidth, sHeight) 也可以换成 usage_page.bound()
                # https://pymupdf.readthedocs.io/en/latest/page.html#Page.show_pdf_page
                sPage.show_pdf_page(usage_page.cropbox, usage_pdf, p_index, keep_proportion=True,
                                    clip=usage_page.cropbox)
                sPage.set_rotation(source_page_rotations[p_index])
                ######### 增加输出原页面 测试用
        # if main.debugger:
        #     folder = os.path.join(self.current_file_path, 'tmp')
        #     if not os.path.exists(folder):
        #         os.makedirs(folder)
        #     usage_pdf.save(os.path.join(folder, f"source-{int(time.time())}.pdf"))
