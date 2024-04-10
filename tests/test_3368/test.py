from fitz import fitz

# https://github.com/pymupdf/PyMuPDF/discussions/3368
def test_subset_fonts():
    doc = fitz.open('401-020605-00.pdf')
    doc.subset_fonts()
    doc.save('x.pdf')