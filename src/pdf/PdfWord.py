import uuid

import pymupdf
from PyQt6.QtCore import QRectF

from src.pdf.constants import DEFAULT_FONT


class PdfWord:

    def __init__(self, rect: pymupdf.Rect, text: str, font_size: float, font: str = DEFAULT_FONT, is_new: bool = True):
        self.uuid = uuid.uuid4()
        self.rect = rect
        self._orig_rect = pymupdf.Rect(rect)
        self._orig_text = text
        self._edited_text = text
        self.font_size = font_size
        self.font = font
        self._is_marked_for_deletion = False
        self._is_new = is_new

    @classmethod
    def from_pymupdf_dict(cls, span: dict) -> 'PdfWord':
        if bbox := span.get('bbox'):
            rect = pymupdf.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        else:
            rect = pymupdf.Rect()
        return PdfWord(rect, span.get('text', ''), span.get('size', 12), span.get('font', DEFAULT_FONT), is_new=False)

    def text(self) -> str:
        return self._edited_text

    def original_rect(self) -> pymupdf.Rect:
        return self._orig_rect

    @classmethod
    def from_span_dict(cls, span: dict) -> 'PdfWord':
        return PdfWord.from_pymupdf_dict(span)

    def mark_for_deletion(self):
        self._is_marked_for_deletion = True

    def width(self) -> float:
        return self.rect.x1 - self.rect.x0

    def height(self) -> float:
        return self.rect.y1 - self.rect.y0

    def to_qrect(self, scale: float = 1.0) -> QRectF:
        """Converts the PDF points to a rect with screen pixels at the specific 'scale' (zoom)"""
        return QRectF(self.rect.x0 * scale, self.rect.y0 * scale, self.width() * scale, self.height() * scale)

    def resize(self, rect: QRectF, scale: float) -> None:
        """Applies a resize to this word from a screen pixel rect at the specific 'scale' (zoom)"""
        self.rect.x0 = rect.x() / scale
        self.rect.y0 = rect.y() / scale
        self.rect.x1 = (rect.x() + rect.width()) / scale
        self.rect.y1 = (rect.y() + rect.height()) / scale

    def is_marked_for_deletion(self) -> bool:
        return self._is_marked_for_deletion

    def is_text_edited(self) -> bool:
        return not self._edited_text == self._orig_text

    def is_rect_edited(self) -> bool:
        return not self._orig_rect == self.rect

    def is_edited(self) -> bool:
        return self.is_text_edited() or self.is_rect_edited()

    def is_only_space(self) -> bool:
        """Returns true if the text content of this word is only space"""
        return self._edited_text.strip() == ''

    def should_be_inserted(self) -> bool:
        return not self.is_marked_for_deletion() and (self.is_edited() or self._is_new)

    def should_be_deleted(self) -> bool:
        return not self._is_new and (self.is_marked_for_deletion() or self.is_edited())

    def edit_text(self, new_text: str):
        if self._orig_text != new_text:
            self._edited_text = new_text
