from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PyQt6.QtCore import QRectF


class WordBox:

    def __init__(self, rect: pymupdf.Rect, text: str):
        self.rect = rect
        self.text = text
        self.marked_for_deletion = False

    def mark_for_deletion(self):
        self.marked_for_deletion = True

    def scale(self, scale: float):
        self.rect.x0 *= scale
        self.rect.y0 *= scale
        self.rect.x1 *= scale
        self.rect.y1 *= scale

    def width(self) -> float:
        return self.rect.x1 - self.rect.x0

    def height(self) -> float:
        return self.rect.y1 - self.rect.y0

    def to_qrect(self, scale: float | None = None):
        if scale:
            self.scale(scale)

        return QRectF(self.rect.x0, self.rect.y0, self.width(), self.height())


class PdfPage:
    
    def __init__(self, page: pymupdf.Page):
        self._page = page
        self.word_boxes = self._load_word_boxes()
        
    def _load_word_boxes(self):
        words = self._page.get_text_words()
        return [WordBox(pymupdf.Rect(x0, y0, x1, y1), text) for x0, y0, x1, y1, text, *_ in words] 

class PdfDocument:

    def __init__(self, path: str):
        super().__init__()

        self.doc = pymupdf.open(path)
        self.pages: list[PdfPage] = self._load_pages()
        self.path = Path(path)
        self.current_page_index = 0
        self._word_box_cache: dict[int, list[WordBox]] = dict()
        
    def _load_pages(self) -> list[PdfPage]:
        return [PdfPage(p) for p in self.doc.pages()]
            

    def get_current_page(self) -> PdfPage:
        return self.pages[self.current_page_index]

    def page_count(self) -> int:
        return self.doc.page_count

    def increment_page_index(self):
        self.current_page_index += 1

    def decrement_page_index(self):
        self.current_page_index -= 1

    def get_word_boxes_current_page(self):
        return self.get_current_page().word_boxes

    def mark_word_box_for_deletion(self, word_id: int):
        page_words = self._word_box_cache[self.current_page_index]
        for word in page_words:
            if id(word) == word_id:
                word.mark_for_deletion()

    def save_current_page(self):
        page = self.get_current_page()
        # Handle deletions
        page_words = self._word_box_cache[self.current_page_index]
        for word in page_words:
            if word.marked_for_deletion:
                page.add_redact_annot(word.rect, fill=None)
        page.apply_redactions(images=0, graphics=0, text=0)
        self.save()

    def save(self) -> None:
        """Save changes back to the file this document was opened from."""
        self.doc.saveIncr()
    
    def save_as(self, path: str) -> None:
        """Save a fresh copy to a new path, with cleanup."""
        self.doc.save(path, garbage=4, deflate=True)
