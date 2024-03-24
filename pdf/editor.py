import concurrent

from fitz import Document, fitz, Shape
from tqdm import tqdm

from model import Mark
from pdf import Reader
from support import a4_width, a4_height, header_height, logged, get_url_content_retry

debugger = False


class Editor(Reader):
    """
    pdf修改器
    """

    def __init__(self, bytes: bytes, is_rewrap: bool = False):
        """
        构造函数
        :param bytes: 单个pdf对象的内容字节数组
        """
        super().__init__(bytes, is_rewrap)

    @logged(desc='批量下载遮罩区域图片')
    def get_image_url_pixmap_dict(self, marks: list[Mark]):
        """
        从遮罩区域数组中提取图片url，并发下载，放到 url-pixmap 作为kv的字典中
        :param marks: 遮罩区域数组
        :return: dict
        """

        def append_dict(url: str, image_pixmap_dict: object):
            if url not in image_pixmap_dict:
                img_pixmap = fitz.Pixmap(get_url_content_retry(url))
                image_pixmap_dict[url] = img_pixmap

        image_pixmap_dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = []
            for mark in marks:
                if mark.image_url:
                    future = pool.submit(append_dict, mark.image_url, image_pixmap_dict)
                    futures.append(future)
            process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}遮罩图片')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                process_bar.update(1)
                pass
        return image_pixmap_dict

    @logged(desc='给源文件所有页添加遮罩区域')
    def wrap_doc_with_marks(self, zoom: float, marks: list[Mark]):
        """
        给当前source文档添加遮罩区域
        :param zoom: 每页统一的缩放比例
        :param rotations: 每页的旋转角度
        :param page_marks: 每页的遮罩区域数组
        :return:
        """
        if not marks or len(marks) == 0:
            return
        # 添加遮罩区域之前先批量下载所有的图片
        image_url_dict = self.get_image_url_pixmap_dict(marks)
        if not zoom:
            zoom = 1
        for index, page in enumerate(self.doc):
            for mark in marks:
                # 页面传递进来的缩放倍数,这里使用的时候要进行反向缩放，才能适配原始页面的坐标系
                rect = fitz.Rect(float(mark.x0) / zoom, float(mark.y0) / zoom, float(mark.x1) / zoom,
                                 float(mark.y1) / zoom)
                if mark.image_url:
                    img_pixmap = image_url_dict[mark.image_url]
                    page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0)
                else:
                    shape: Shape = page.new_shape()
                    shape.draw_rect(rect=rect)
                    shape.finish(
                        fill=0,  # fill color
                        color=0  # line color
                    )
                    shape.commit()

    @logged(desc='将头内容和源内容合并到target_doc文件中')
    def wrap_target_doc_with_header(self, rotations: list[float], header_doc: Document, target_doc: Document):
        """
        将头内容和源内容合并到target_doc文件中
        :param rotations: 源文件的旋转角度集合
        :param header_doc: 头文件
        :param target_doc: 目标文件
        :return:
        """
        usage_pdf: Document = self.doc
        for p_index, usage_page in enumerate(usage_pdf):
            # 所以需要在二次转化前记录之前每页的旋转角度，并转换后再设置进去, 这里不可删除
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
            if rotations and len(rotations) > p_index:
                rotation = rotations[p_index]
            else:
                # 获取页面应该回正的旋转角度
                rotation = self.get_page_roration_for_cropbox(p_index)
            # 因为 show_pdf_page 利用的原始图层，故将页面重置为未旋转前的， 并且拼接后，按照上面得到的旋转角度再旋转
            usage_page.set_rotation(0)
            new_page.show_pdf_page(r2, usage_pdf, p_index, rotate=rotation, keep_proportion=True,
                                   clip=usage_page.cropbox)
            # 清理无效链接，针对页面缩容
            # new_page.clean_contents()
