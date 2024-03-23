from fitz import fitz

if __name__ == '__main__':
    doc = fitz.open('扫码报工PDF/CS01-P3-001-竖向-右侧.pdf')
    for page in doc:
        print(page.rotation)
