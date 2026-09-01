import pymupdf
from PyQt6.QtCore import QRectF


def qt_rect_to_pdf_rect(rect: QRectF, scale: float) -> pymupdf.Rect:
    return pymupdf.Rect(rect.x() / scale, rect.y() / scale, (rect.x() + rect.width()) / scale,
                        (rect.y() + rect.height()) / scale)
