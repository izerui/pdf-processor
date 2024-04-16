import fitz


def test():
    doc = fitz.open('a227bf74-c639-4d12-9f55-7d92b8a72ba9.pdf')
    page = doc[0]
    blocks = page.get_textpage().extractDICT()['blocks']
    for block in blocks:
        print(block)
        for line in block['lines']:
            print(line)
        pass
    pass