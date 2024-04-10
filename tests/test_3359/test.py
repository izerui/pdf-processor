from fitz import fitz

# 内容丢失
# https://github.com/pymupdf/PyMuPDF/discussions/3359
def test_wrong_files():
    files = ["mt_03_22318er_0_806.pdf", "丢失大量内容401-020605-00.pdf"]

    rect = [0, 0, 200, 300]

    target_doc = fitz.open()
    for file in files:
        doc = fitz.open(file)
        for page in doc:
            page.clean_contents(sanitize=False)
            page.insert_image(rect, filename="logo.png")
            page.draw_rect(rect, color=(1, 0, 0))
            new_page = target_doc.new_page(width=842, height=595)
            new_page.show_pdf_page(new_page.rect, doc, page.number)
        doc.close()
    target_doc.save("x.pdf")
    target_doc.close()

# 图片插入位置不对
def test_wrong_files2():
    files = ["mt_03_22318er_0_806.pdf", "丢失大量内容401-020605-00.pdf"]

    rect = [0, 0, 200, 300]

    target_doc = fitz.open()
    for file in files:
        doc = fitz.open(file)
        for page in doc:
            page.wrap_contents()
            page.insert_image(rect, filename="logo.png")
            page.draw_rect(rect, color=(1, 0, 0))
            new_page = target_doc.new_page(width=842, height=595)
            new_page.show_pdf_page(new_page.rect, doc, page.number)
        doc.close()
    target_doc.save("x.pdf")
    target_doc.close()