from pymupdf import pymupdf

# 图片插入位置不对
def test_wrong_files2():
    files = [
        "微信图片_20251028151513_69_183.jpg",
        "微信图片_20251028151527_70_183.jpg",
        "微信图片_20251028151545_71_183.jpg",
        "微信图片_20251028151550_72_183.jpg",
        "微信图片_20251028151606_73_183.jpg",
        "微信图片_20251028151614_74_183.jpg",
        "微信图片_20251028151627_75_183.jpg",
        "微信图片_20251028151639_76_183.jpg",
        "微信图片_20251028151651_77_183.jpg",
        "微信图片_20251028151708_78_183.jpg",
        "微信图片_20251028151713_79_183.jpg",
        "微信图片_20251028151722_80_183.jpg",
        "微信图片_20251028151737_81_183.jpg",
        "微信图片_20251028151759_82_183.jpg",
        "微信图片_20251028151810_83_183.jpg",
        "微信图片_20251028151820_84_183.jpg",
        "微信图片_20251028151829_85_183.jpg",
    ]

    rect = [0, 0, 1240, 1754]

    target_doc = pymupdf.open()
    for file in files:
        doc = pymupdf.open(file)
        for page in doc:
            new_page = target_doc.new_page(width=1240, height=1754)
            new_page.insert_image(rect, filename=file)
            # new_page.show_pdf_page(new_page.rect, doc, page.number)
        doc.close()
    target_doc.save("x.pdf")
    target_doc.close()