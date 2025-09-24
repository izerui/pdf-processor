import concurrent
import io

from PIL import Image
from pymupdf import pymupdf, Shape, Document

from model import Mark
from pdf import Reader
from support import logged, get_url_content_retry, logger, get_text_rotation_from_dir


# hui_img_buffer = read_bytes_from_file(
#     os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'gray.png'))
#
# hui_pixmap = pymupdf.Pixmap(hui_img_buffer)

class Editor(Reader):
    """
    pdf修改器, 会跟随实例消亡自动关闭文档
    """

    def __init__(self, data: bytes, is_convert: bool = False):
        """
        构造函数
        :param data: 单个pdf对象的内容字节数组
        :param is_convert: 单个pdf对象的内容字节数组
        """
        super().__init__(data, is_convert)

    @logged(desc='批量获取marks区域的网络图片，并返回填充后的缓存')
    def cache_marks_images(self, marks: list[Mark], marks_images_cache: dict) -> None:
        """
        从遮罩区域数组中提取图片url，并发下载，放到 url-pixmap 作为kv的字典中
        :param marks: 遮罩区域数组
        :param marks_images_cache: 遮罩区域包含的网络图片的缓存dict
        :return: dict
        """

        def check_and_fill_marks_images_cache(url: str, marks_images_cache: object = {}):
            if url not in marks_images_cache:
                # PIL加载网络图片，并转换成统一jpeg格式的二进制
                img = Image.open(io.BytesIO(get_url_content_retry(url))).convert("RGB")
                img_stream = io.BytesIO()
                img.save(img_stream, format='JPEG')
                # TODO 这里转成pixmap会不会定义一个引用，缩小pdf体积？
                img_pixmap = pymupdf.Pixmap(img_stream)
                marks_images_cache[url] = img_pixmap

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for mark in marks:
                if mark.image_url:
                    future = pool.submit(check_and_fill_marks_images_cache, mark.image_url, marks_images_cache)
                    futures.append(future)
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}遮罩图片')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                exception = future.exception()
                if exception:
                    logger.exception(exception)
                pass

    @logged(desc='给源文件所有页添加遮罩区域')
    def wrap_doc_with_marks(self, rotations: list[float], zoom: float, marks: list[Mark], url_datas: dict) -> None:
        """
        给当前source文档添加遮罩区域
        :param rotations: 每页的旋转角度
        :param zoom: 每页统一的缩放比例
        :param marks: 每页的遮罩区域数组
        :param url_datas: url_data对照表
        :return:
        """
        if not marks or len(marks) == 0:
            return
        if not zoom:
            zoom = 1
        for index, page in enumerate(self.doc):
            # 记录原来的旋转角度
            _rotation = page.rotation
            for mark in marks:
                # print('rotation: ', rotations[index], 'mark: ', mark)

                # 页面传递进来的缩放倍数,这里使用的时候要进行反向缩放，才能适配原始页面的坐标系
                rect = pymupdf.Rect(float(mark.x0) / zoom, float(mark.y0) / zoom, float(mark.x1) / zoom,
                                 float(mark.y1) / zoom)
                # 设置为传入的旋转角度，防止显示效果不一致
                page.set_rotation(rotations[index])
                # 通过设置的旋转角度通过反向计算区域块实际位置
                rect = rect.transform(page.derotation_matrix)
                if mark.image_url:
                    # 不填充颜色，彻底删除
                    page.add_redact_annot(rect)
                    # 应用删除操作
                    page.apply_redactions(
                        images=2,  # 抹掉重叠部分：只把图像中与删除区域重叠的部分变空白，保留图像其他部分
                        graphics=1,  # 删除包含的图形：只删除完全包含在删除矩形内的图形（包括线条）
                        text=0  # 删除文字
                    )

                    # PIL加载网络图片，并转换成统一jpeg格式的二进制
                    img = Image.open(io.BytesIO(url_datas[mark.image_url])).convert("RGB")
                    # img = img.resize((int(rect.width), int(rect.height)))
                    img_stream = io.BytesIO()
                    img.save(img_stream, format='JPEG')
                    # 这里转成pixmap反而会增大最终pdf体积
                    # img_pixmap = pymupdf.Pixmap(img_stream)
                    # 跟随页面旋转角度进行旋转，否则图片方向不对
                    page.insert_image(rect, stream=img_stream, keep_proportion=False, alpha=0, xref=0,
                                      rotate=rotations[index])
                else:
                    shape: Shape = page.new_shape()
                    shape.draw_rect(rect=rect)
                    # 颜色对照表 (217 / 255, 217 / 255, 217 / 255) 对应  #D9D9D9
                    # https://sunpma.com/other/rgb/
                    shape.finish(
                        fill=(217 / 255, 217 / 255, 217 / 255),  # fill color
                        color=(217 / 255, 217 / 255, 217 / 255)  # line color
                    )
                    shape.commit()
            # 还原原来的旋转角度
            page.set_rotation(_rotation)

    def generate_annot_doc_without_close(self) -> Document:
        # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
        pymupdf.TOOLS.set_small_glyph_heights(True)
        # 下部区域
        annot_doc = pymupdf.open()
        for index, page in enumerate(self.doc):
            _page_rotation = page.rotation
            page.set_rotation(0)
            new_page = annot_doc.new_page(width=page.rect.width, height=page.rect.height)
            # 查找源页面注释
            annots = list(page.annots(types=[pymupdf.mupdf.PDF_ANNOT_FREE_TEXT]))
            if len(annots) < 0:
                continue
            for annot_index, annot in enumerate(annots):
                print('\r\t')
                # print(doc.xref_object(annot.xref))
                # print('Remote Control:', doc.xref_get_key(annot.xref, 'RC'))
                # print('Default Style:', doc.xref_get_key(annot.xref, 'DS'))
                if annot.type[1] == 'FreeText':
                    blocks = annot.get_textpage().extractDICT()['blocks']
                    for block in blocks:
                        lines = block['lines']
                        # 拆分后按每个span进行添加
                        for line in lines:
                            # 书写方向及书写方式（横/竖） 0 = horizontal, 1 = vertical
                            line_wmode = line['wmode']
                            line_rotation = get_text_rotation_from_dir(line['dir'])
                            line_rect = pymupdf.Rect(line['bbox'][0], line['bbox'][1], line['bbox'][2], line['bbox'][3])
                            for span in line['spans']:
                                span_size = span['size']
                                span_flags = span['flags']
                                span_font = span['font']
                                # span_color = [((span['color'] >> 16) & 255) / 255, ((span['color'] >> 8) & 255) / 255, (span['color'] & 255) / 255]
                                rgb_tuple = pymupdf.sRGB_to_pdf(span['color'])
                                span_color = [rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]]
                                span_ascender = span['ascender']
                                span_descender = span['descender']
                                span_text = span['text']

                                # https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary
                                a = span["ascender"]
                                d = span["descender"]
                                o = pymupdf.Point(span["origin"])
                                r = pymupdf.Rect(span['bbox'])

                                # 通过设置的旋转角度通过反向计算区域块实际位置
                                # r = r.transform(page.derotation_matrix)

                                # 如果区域高度不足以包含字体的大小，则把字体大小设置为rect的高度
                                # if r.height < span_size:
                                #     span_size = r.height

                                _annot = new_page.add_freetext_annot(rect=r,
                                                                     text=span_text,
                                                                     fontname=span_font,
                                                                     fontsize=span_size,
                                                                     text_color=span_color)
                                _annot.set_flags(span_flags)
                                _annot.set_opacity(1)
                                _annot.update(rotate=line_rotation, text_color=span_color, fill_color=[1, 1, 1])
            page.set_rotation(_page_rotation)
            new_page.set_rotation(_page_rotation)
        return self.convert_doc(annot_doc)

    # @logged(desc='整理页面')
    def clean_pages(self):
        """
        循环每页清理：
            清理并连接与此页面关联的所有contents对象
        参考：https://pymupdf.readthedocs.io/en/latest/functions.html#Page.clean_contents
        :return:
        """

        # 考虑下面两个方法的区别：貌似第二个快，但是会清理不完整，导致坐标还是存在偏差
        # 1. https://pymupdf.readthedocs.io/en/latest/functions.html#Page.clean_contents
        # 2. https://pymupdf.readthedocs.io/en/latest/functions.html#Page.wrap_contents
        # page.wrap_contents()

        # clean 能纠正错误的位置问题，但是会丢失内容
        # for page in self.doc:
        #     page.wrap_contents() # wrap 的目的是保证页面插入图片和矩形保证坐标位置正确
        # 1.24.2 后不再需要清理页面 应该会自动修复坐标位置错误问题
        pass

    @logged(desc='重新定义当前文档')
    def clone_doc_for_self(self):
        """
        复制一个新的pdf
        """
        clone_doc = pymupdf.open()
        clone_doc.insert_pdf(docsrc=self.doc)
        self.doc.close()
        self.doc = clone_doc

    @logged(desc='将注释和字段“烘焙”到PDF页面中')
    def bake_document(self):
        """
        可立即在 PyMuPDF 中使用。有一个功能可以将注释和字段（！！！）“烘焙”到 PDF 中 - 这意味着它将这些项目转换为正常的页面内容。
        解释：https://github.com/pymupdf/PyMuPDF/discussions/3356
        """
        # source_file_pdf = pymupdf.mupdf.pdf_document_from_fz_document(self.doc)
        # pymupdf.mupdf.pdf_bake_document(source_file_pdf, 1, 1)
        # 1.24.2 增加新功能
        self.doc.bake()
        pass
