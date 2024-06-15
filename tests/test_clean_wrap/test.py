import os
import tempfile

import pymupdf


def bake_document(doc):
    # source_file_pdf = pymupdf.mupdf.pdf_document_from_fz_document(doc)
    # pymupdf.mupdf.pdf_bake_document(source_file_pdf, 1, 1)
    # 1.24.2 升级替换
    doc.bake()
    pass


# 解释参考: https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-handle-page-contents
def handle_page(page, type):
    if type == 0:
        page.insert_text(point=pymupdf.Point(300, 300), text='no_operation', fontsize=48, color=[1, 0, 0])
        pass
    elif type == 1:
        page.clean_contents()
        page.insert_text(point=pymupdf.Point(300, 300), text='clean_contents', fontsize=48, color=[1, 0, 0])
    elif type == 2:
        page.wrap_contents()
        page.insert_text(point=pymupdf.Point(300, 300), text='wrap_contents', fontsize=48, color=[1, 0, 0])
    pass


def test():
    docs = [
        pymupdf.open('28205N61101AAA (1).pdf'),
        pymupdf.open('mt_03_22318er.pdf'),
        pymupdf.open('401-020605-00.pdf'),
        pymupdf.open('mt_04_23024cc.pdf'),
        pymupdf.open('401-016306-01(内容丢失).pdf'),
        pymupdf.open('NOR4.139.136（V00）.pdf')
    ]

    new_doc = pymupdf.open()
    for doc in docs:
        new_doc.insert_pdf(docsrc=doc)

        page = doc[0]
        print('')
        print(doc.name)
        print(doc.xref_object(page.xref))


        # TODO Switch from 0 to 2 to reproduce the problem
        # handle_page(page, 0) # no operation  error: 1,2,4
        # handle_page(page, 1) # clean_contents error: 3,5,6
        handle_page(page, 2) # wrap_contents error: 1,2,4

        # cont_lines = page.read_contents().splitlines()
        # for line in cont_lines:
        #     print(line)

        print(doc.xref_object(page.xref))
        print('')

        bake_document(doc)

        new_page = new_doc.new_page(width=page.cropbox.width, height=page.cropbox.height)
        new_page.show_pdf_page(new_page.cropbox, doc, 0)
        doc.close()
    new_doc.ez_save('x.pdf')
    import webbrowser
    browser = webbrowser.get('chrome')
    browser.open(f'file:///{os.path.realpath("x.pdf")}')

def test003():
    fff = tempfile.mkdtemp()
    print(fff)