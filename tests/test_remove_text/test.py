import fitz


def test():
    doc = fitz.open('a227bf74-c639-4d12-9f55-7d92b8a72ba9.pdf')
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
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)  # remove text, but no image
    # for xref in page.get_contents():
    #     stream = doc.xref_stream(xref).replace(b'Copyright 2016-2024 Aspose Pty Ltd.', b'')
    #     doc.update_stream(xref, stream)
    doc.ez_save('x.pdf')
    pass