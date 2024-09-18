import pymupdf

if __name__ == '__main__':
    doc = pymupdf.open('WechatIMG201.jpg')
    for page in doc:
        text = page.get_text()
        print(text)
