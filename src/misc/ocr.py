
import io
import logging

from pymupdf import pymupdf
from PIL import Image
from pytesseract import pytesseract, Output

from PdfDocument import PdfPage


SCALE = 5
"""Each point in a PDF is multiplied by the SCALE factor. As each point in a PDF is, by definition, 1/72th of an inch,
this results in approximately 300 DPI (4*72 = 288 DPI), which is optimal for Tesseract OCR"""

MATRIX = pymupdf.Matrix(SCALE, SCALE)

PSM_TEXT_LINE = 7
"""Tesseract OCR 'Page Segmentation Mode' config meaning 'expect a line of text'"""
PSM_WORD = 8
"""Tesseract OCR 'Page Segmentation Mode' config meaning 'expect a single word'"""

logger = logging.getLogger(__name__)

def ocr_rect(page: PdfPage, rect: pymupdf.Rect, language='eng') -> str|None:
    pixmap = page.page().get_pixmap(matrix=MATRIX, clip=rect, alpha=False)
    img = Image.open(io.BytesIO(pixmap.tobytes('png')))
    try:
        return pytesseract.image_to_string(img, config=f'--psm {PSM_WORD}', output_type=Output.STRING).strip()
    except RuntimeError as e:
        logger.error(f'Failed to run OCR: {e}')
        return None