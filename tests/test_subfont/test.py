import pymupdf


def test_subfont0():
    doc = pymupdf.open()
    page = doc.new_page(width=1024, height=768)
    page.insert_htmlbox(
        rect=pymupdf.Rect(280, 50, 480, 100),
        text=f'<span style="font-size:18px;font-weight:bold;word-break:break-all;font-family:\'helv\';">Α、Β、Γ、Δ、Ε、Ζ、Η、Θ、Ι、Κ、Λ、Μ、Ν、Ξ、Ο、Π、Ρ、Σ、Τ、Υ、Φ、Χ、Ψ、Ω。α、β、γ、δ、ε、ζ、η、θ、ι、κ、λ、μ、ν、ξ、ο、π、ρ、ς、τ、υ、φ、χ、ψ、ω。</span>'
    )
    doc.subset_fonts()
    doc.ez_save('subseted.pdf')


def test_subfont1():
    chn_fontname = 'chn'
    with open('FangZhengHeiTiJianTi-1.ttf', 'rb') as f:
        font_buffer = bytes(f.read())
    font = pymupdf.Font(fontname=chn_fontname,
                        fontbuffer=font_buffer,
                        language='zh-Hans')
    doc = pymupdf.open()
    page = doc.new_page(width=1024, height=768)
    page.insert_font(fontname=chn_fontname,
                     fontbuffer=font.buffer)
    page.insert_text(point=pymupdf.Point(280, 50), text=f'表单项一: 表单项一内容',
                     fontsize=18,
                     fontname=chn_fontname, color=(0, 0, 0))
    page.insert_text(point=pymupdf.Point(280, 100), text=f'表单项一: 表单项二内容',
                     fontsize=18,
                     fontname=chn_fontname, color=(0, 0, 0))
    page.insert_text(point=pymupdf.Point(280, 150), text=f'表单项一: 表单项三内容',
                     fontsize=18,
                     fontname=chn_fontname, color=(0, 0, 0))
    doc.ez_save('un_com1.pdf')

    # doc.subset_fonts()

    # pdf = pymupdf._as_pdf_document(doc)  # access underlying PDF-specific level
    # pymupdf.mupdf.pdf_subset_fonts2(pdf, list(range(doc.page_count)))

    # 1.24.2 增加新功能，替换原有的font-tools压缩
    doc.subset_fonts()

    doc.ez_save('com1.pdf')


def test_subfont2():
    doc = pymupdf.open()
    page = doc.new_page(width=1024, height=768)
    page.insert_htmlbox(
        rect=pymupdf.Rect(280, 50, 280 + 330, 50 + 60),
        text=f'<span style="font-size:18px;font-weight:bold;display:block;word-break:break-all;">表单项一: 表单项一内容</span>'
    )

    page.insert_htmlbox(
        rect=pymupdf.Rect(280, 100, 280 + 330, 50 + 60 + 60),
        text=f'<span style="font-size:18px;font-weight:bold;display:block;word-break:break-all;">表单项二: 表单项二内容</span>'
    )

    page.insert_htmlbox(
        rect=pymupdf.Rect(280, 150, 280 + 330, 50 + 60 + 60),
        text=f'<span style="font-size:18px;font-weight:bold;display:block;word-break:break-all;">表单项三: 表单项三内容</span>'
    )

    doc.ez_save('un_com2.pdf')

    # doc.subset_fonts()

    pdf = pymupdf._as_pdf_document(doc)  # access underlying PDF-specific level
    pymupdf.mupdf.pdf_subset_fonts2(pdf, list(range(doc.page_count)))

    doc.ez_save('com2.pdf')
