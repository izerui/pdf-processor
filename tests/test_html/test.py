import time

import fitz

from support import a4_width, a4_height, logged


def test_html_to_pdf():
    s_time = int(time.perf_counter() * 1000)
    doc = fitz.open()
    page = doc.new_page(width=a4_width, height=a4_height)
    content = """<div class="box">
          <div class="textList">
            <div class="text"><span class="label">工单号:</span><span class="value">34543</span> </div>
            <div class="text"><span class="label">货品编码:</span><span class="value">CS01-P3-008</span> </div>
            <div class="text"><span class="label">货品名称:</span><span class="value">进料008</span> </div>
            <div class="text"><span class="label">交 期:</span><span class="value">2024-04-30</span></div>
            <div class="text"><span class="label">数 量:</span><span class="value">45654674567</span> </div>
            <div class="text"><span class="label">规格型号:</span><span class="value">Φ12*870</span> </div>
            <div class="text"><span class="label">工艺路线:</span><span class="value">磨边>>抛光>>切割>>压铸Ø</span></div>
          </div>
        </div>"""
    css = """* {
              margin: 0;
              padding: 0;
            }
            .box {
              display: flex;
              align-items: center;
            }
            .box .img {
              width: 185px;
            }
            .textList {
              padding-left: 30px;
              display: flex;
              flex-wrap: wrap;
            }
            .textList .text {
              width: 33.3333%;
              flex: none;
              padding: 15px 0;
            }
            .textList .text .label {
              padding-right: 8px;
            }
            """

    page.insert_htmlbox(
        rect=page.rect,
        text=content,
        css=css
    )
    print(f'耗时: {int(time.perf_counter() * 1000) - s_time}/ms')
    doc.ez_save('x.pdf')


