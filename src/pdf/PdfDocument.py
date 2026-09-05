import logging
import re
import uuid
from pathlib import Path

import pymupdf

from src.decorators.LogDecorator import log
from src.pdf.PdfPage import PdfPage
from src.pdf.PdfWord import PdfWord

logger = logging.getLogger(__name__)


class PdfDocument:

    def __init__(self, path: str):
        super().__init__()

        self.path = Path(path)
        self.doc: pymupdf.Document | None = None
        self.pages: list[PdfPage] = []
        self.current_page_index = 0

        self._init()

    def _init(self):
        if self.doc:
            self.doc.close()
        self.doc = pymupdf.open(self.path)
        self.pages = self._load_pages()

    def _load_pages(self) -> list[PdfPage]:
        out = []

        for i, page in enumerate(self.doc.pages()):
            out.append(PdfPage(page))
        return out

    def set_current_page(self, page_index: int) -> PdfPage:
        if 0 <= page_index < self.page_count():
            self.current_page_index = page_index

        return self.get_current_page()

    def get_current_page(self) -> PdfPage:
        page = self.pages[self.current_page_index]
        page.load_words()
        return page

    def get_page(self, page_index: int) -> PdfPage | None:
        if 0 <= page_index < self.page_count():
            return self.pages[page_index]
        return None

    def set_next_page(self) -> PdfPage:
        self.increment_page_counter()
        return self.get_current_page()

    def set_prev_page(self) -> PdfPage:
        self.decrement_page_counter()
        return self.get_current_page()

    def page_count(self) -> int:
        return self.doc.page_count

    def increment_page_counter(self):
        self.current_page_index += 1

    def decrement_page_counter(self):
        self.current_page_index -= 1

    def get_words_current_page(self):
        return self.get_current_page().get_words()

    def mark_word_for_deletion(self, word_id: uuid.UUID):
        page_words = self.get_words_current_page()
        for word in page_words:
            if word.uuid == word_id:
                word.mark_for_deletion()

    def add_new_word(self, rect: pymupdf.Rect, text: str) -> PdfWord:
        page = self.get_current_page()
        word = PdfWord(rect, text, rect.height / 1.3, is_new=True)
        page.add_word(word)
        return word

    def save(self) -> None:
        """Save changes back to the file this document was opened from."""
        if self.doc.can_save_incrementally():
            self.doc.saveIncr()

    @log
    def save_as(self, path: str) -> None:
        """Save a fresh copy to a new path, with cleanup."""
        for page in self.pages:
            try:
                page_words = page.get_words()

                for word in [w for w in page_words if w.should_be_deleted()]:
                    page.delete_word(word)

                page.apply_deletions()

                for word in [w for w in page_words if w.should_be_inserted()]:
                    page.insert_word_morph(word)
            except Exception as e:
                logger.error(f'Could not apply edits to page {page.page_number()}: {str(e)}')

        self.doc.save(path, garbage=4, deflate=True)
        self.doc.close()

    def saveas_debug(self, path: str) -> None:
        doc = pymupdf.open(self.path)

        for page in doc:
            for xref in page.get_contents():
                xref_stream = doc.xref_stream(xref)
                visible_xref_stream = re.sub(rb'\d+(\s+Tr\b)', rb'0\1', xref_stream)
                if xref_stream != visible_xref_stream:
                    doc.update_stream(xref, visible_xref_stream)

        doc.save(path, garbage=4, deflate=True)
        doc.close()
