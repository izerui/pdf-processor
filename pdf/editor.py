import concurrent
import os

from fitz import fitz, Shape

from model import Mark
from pdf import Reader
from support import logged, get_url_content_retry, read_bytes_from_file


# hui_img_buffer = read_bytes_from_file(
#     os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'gray.png'))
#
# hui_pixmap = fitz.Pixmap(hui_img_buffer)

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

    @logged(desc='批量下载遮罩区域图片')
    def get_image_url_pixmap_dict(self, marks: list[Mark]) -> dict:
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
            # process_bar = tqdm(total=len(futures), desc=f'并行下载{len(futures)}遮罩图片')
            for future in concurrent.futures.as_completed(futures):  # 并发执行
                # process_bar.update(1)
                pass
        return image_pixmap_dict

    @logged(desc='给源文件所有页添加遮罩区域')
    def wrap_doc_with_marks(self, rotations: list[float], zoom: float, marks: list[Mark]) -> None:
        """
        给当前source文档添加遮罩区域
        :param rotations: 每页的旋转角度
        :param zoom: 每页统一的缩放比例
        :param marks: 每页的遮罩区域数组
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
                # print('rotation: ', rotations[index], 'mark: ', mark)

                # 页面传递进来的缩放倍数,这里使用的时候要进行反向缩放，才能适配原始页面的坐标系
                rect = fitz.Rect(float(mark.x0) / zoom, float(mark.y0) / zoom, float(mark.x1) / zoom,
                                 float(mark.y1) / zoom)
                # 记录原来的旋转角度
                _rotation = page.rotation
                # 设置为传入的旋转角度，防止显示效果不一致
                page.set_rotation(rotations[index])
                # 通过设置的旋转角度通过反向计算区域块实际位置
                rect = rect.transform(page.derotation_matrix)
                if mark.image_url:
                    img_pixmap = image_url_dict[mark.image_url]
                    # 跟随页面旋转角度进行旋转，否则图片方向不对
                    page.insert_image(rect, pixmap=img_pixmap, keep_proportion=False, alpha=0, xref=0,
                                      rotate=rotations[index])
                else:
                    # 跟随页面旋转角度进行旋转，否则图片方向不对
                    # page.insert_image(rect, pixmap=hui_pixmap, keep_proportion=False, alpha=0, xref=0,
                    #                   rotate=rotations[index])

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

    @logged(desc='清理页面')
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

        for page in self.doc:
            page.clean_contents()
