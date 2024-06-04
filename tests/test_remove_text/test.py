import pymupdf


def test():
    doc = pymupdf.open('a227bf74-c639-4d12-9f55-7d92b8a72ba9.pdf')
    page = doc[0]
    blocks = page.get_textpage().extractDICT()['blocks']
    for block in blocks:
        for line in block["lines"]:
            for span in line['spans']:
                if span['text'] == 'Copyright 2016-2024 Aspose Pty Ltd.':
                    page.add_redact_annot(span["bbox"])
                elif span['text'] == 'Created with Aspose.CAD.':
                    page.add_redact_annot(span["bbox"])
                elif span['text'] == 'Evaluation only.':
                    page.add_redact_annot(span["bbox"])
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)  # remove text, but no image
    # for xref in page.get_contents():
    #     stream = doc.xref_stream(xref).replace(b'Copyright 2016-2024 Aspose Pty Ltd.', b'')
    #     doc.update_stream(xref, stream)
    doc.ez_save('x.pdf')
    pass

def test1():
    doc = pymupdf.open('a227bf74-c639-4d12-9f55-7d92b8a72ba9.pdf')
    page = doc[0]
    # https://pymupdf.readthedocs.io/en/latest/functions.html#Page.get_text_blocks
    blocks = page.get_text_blocks()
    for block in blocks:
        if (block[4] == 'Copyright 2016-2024 Aspose Pty Ltd.\n' or
            block[4] == 'Created with Aspose.CAD.\n' or
            block[4] == 'Evaluation only.\n'):
            page.add_redact_annot((block[0], block[1], block[2], block[3]))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)  # remove text, but no image
    doc.ez_save('x.pdf')
    pass

# 暂时不可用，未验证完
def test2():
    doc = pymupdf.open('a227bf74-c639-4d12-9f55-7d92b8a72ba9.pdf')
    page = doc[0]

    cont_lines = page.read_contents().splitlines()
    for line in cont_lines:
        print(line)

    for xref in page.get_contents():
        stream = doc.xref_stream(xref).replace(b'Copyright', b'')
        doc.update_stream(xref, stream)


    # for xref in page.get_contents():
    #     stream = doc.xref_stream(xref).replace(b'Copyright 2016-2024 Aspose Pty Ltd.', b'')
    #     doc.update_stream(xref, stream)
    doc.ez_save('x.pdf')
    pass