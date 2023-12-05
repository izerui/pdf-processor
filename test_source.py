import os
import time

from fitz import fitz

if __name__ == '__main__':
    doc = fitz.open('tmp/客户文件禁止外传.pdf')
    doc.save(os.path.join('tmp', f"source-{int(time.time())}.pdf"))