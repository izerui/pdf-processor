import os
import time

from fitz import fitz

if __name__ == '__main__':
    doc = fitz.open('tmp/FB14-KX23120262-23-049-A 封板.pdf')
    doc.save(os.path.join('tmp', f"tmp-{int(time.time())}.pdf"))