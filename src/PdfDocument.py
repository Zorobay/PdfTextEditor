import logging
import re
import uuid
from pathlib import Path

import pymupdf
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPixmap, QImage

from src.decorators.LogDecorator import log
from src.enums.PdfRenderMode import PdfRenderMode

logger = logging.getLogger(__name__)

# Applicable for fontname='helv', lineheight=1.0
LINE_HEIGHT_FACTOR = 1.30

DEFAULT_FONT = 'Helv'


def fit_fontsize(text: str, rect: pymupdf.Rect, fontname: str = DEFAULT_FONT) -> float:
    """Largest fontsize that fits `text` inside `rect` on one line, without
    overflowing either dimension."""
    if not text:
        return 1.0

    text_unit_width = sum(pymupdf.get_text_length(c, fontname=fontname, fontsize=1) for c in text)
    height_limited = rect.height / LINE_HEIGHT_FACTOR
    width_limited = rect.width / text_unit_width if text_unit_width > 0 else height_limited
    return min(width_limited, height_limited)


def _measure_natural_bbox(text: str, fontname: str, ref_size: float, anchor: pymupdf.Point) -> pymupdf.Rect | None:
    """Insert `text` on a throwaway page with no morph, purely to find out its
    REAL rendered bbox at ref_size - this is PyMuPDF's own text extraction
    measuring PyMuPDF's own rendering, so it can't disagree with itself the
    way get_text_length() did for non-ASCII strings."""
    scratch = pymupdf.open()
    page = scratch.new_page(width=5000, height=5000)
    page.insert_text(anchor, text, fontsize=ref_size, fontname=fontname, render_mode=3)
    words = page.get_text('words')
    scratch.close()
    if not words:
        return None
    return pymupdf.Rect(
        min(w[0] for w in words),
        min(w[1] for w in words),
        max(w[2] for w in words),
        max(w[3] for w in words))


class PdfWord:

    def __init__(self, rect: pymupdf.Rect, text: str, font_size: float, font: str = DEFAULT_FONT, is_new:bool=True):
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
    def from_pymupdf_dict(cls, span:dict)->'PdfWord':
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

    def should_be_inserted(self)->bool:
        return not self.is_marked_for_deletion() and (self.is_edited() or self._is_new)

    def should_be_deleted(self)->bool:
        return not self._is_new and (self.is_marked_for_deletion() or self.is_edited())

    def edit_text(self, new_text: str):
        if self._orig_text != new_text:
            self._edited_text = new_text


class PdfPage:
    EXCLUDE_IMAGES_FROM_TEXT_EXTRACTION_FLAGS = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES

    def __init__(self, page: pymupdf.Page):
        self._page = page
        self._loaded = False
        self._words: list[PdfWord] = []

    def page(self)->pymupdf.Page:
        return self._page

    @log
    def load_words(self):
        if self._loaded:
            return
        self._words = []
        blocks = self._page.get_text('dict', sort=True, flags=self.EXCLUDE_IMAGES_FROM_TEXT_EXTRACTION_FLAGS).get('blocks', [])

        for block in blocks:
            lines = block.get('lines', [])

            for line in lines:
                spans = line.get('spans', [])

                for span in spans:
                    pdf_word = PdfWord.from_span_dict(span)
                    self._words.append(pdf_word)
        self._loaded = True

    def is_loaded(self) -> bool:
        return len(self._words) > 0

    def get_words(self) -> list[PdfWord]:
        return self._words

    def delete_word(self, word: PdfWord) -> None:
        self._page.add_redact_annot(word.original_rect(), fill=None)

    def add_word(self, word: PdfWord) -> None:
        self._words.append(word)

    def get_pixmap(self, scale: float) -> QPixmap:
        matrix = pymupdf.Matrix(scale, scale)
        pixmap = self._page.get_pixmap(matrix=matrix, alpha=True)
        image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format.Format_RGBA8888)

        # QImage does not own pixmap.samples' buffer, so make a deep copy
        # before the underlying pixmap object is garbage collected.
        return QPixmap.fromImage(image.copy())

    def insert_word_morph(self, word: PdfWord) -> None:
        """Insert `text` so its rendered bbox matches `rect` exactly (to float
        rounding) - measures the real size once, then solves for the affine
        transform mapping that measurement onto `rect`, instead of guessing a
        fontsize from approximate font metrics."""
        rect = word.rect
        text = word.text()
        fontname = DEFAULT_FONT
        ref_size = word.font_size
        anchor = pymupdf.Point(rect.x0, rect.y1)
        natural = _measure_natural_bbox(text, fontname, ref_size, anchor)
        if natural is None or natural.width == 0 or natural.height == 0:
            return  # nothing to place (e.g. whitespace-only text)

        sx = rect.width / natural.width
        sy = rect.height / natural.height

        # fixpoint solves: fixpoint + scale * (natural_corner - fixpoint) == target_corner,
        # i.e. the pivot point that makes the scale-about-a-point transform land exactly
        # on `rect` given where the reference text actually rendered.
        EPS = 1e-9
        fx = (rect.x0 - sx * natural.x0) / (1 - sx) if abs(1 - sx) > EPS else natural.x0
        fy = (rect.y0 - sy * natural.y0) / (1 - sy) if abs(1 - sy) > EPS else natural.y0

        self._page.insert_text(anchor, text, fontsize=ref_size, fontname=fontname,
                               render_mode=PdfRenderMode.INVISIBLE,
                               morph=(pymupdf.Point(fx, fy), pymupdf.Matrix(sx, sy)))

    def apply_deletions(self) -> None:
        self._page.apply_redactions(images=0, graphics=0, text=0)

    def page_number(self) -> int:
        return self._page.number


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
            print(f'Loaded page {i} of {self.doc.page_count}')
        return out

    def set_current_page(self, page_index: int) -> PdfPage:
        if 0 <= page_index < self.page_count():
            self.current_page_index = page_index
            
        return self.get_current_page()
            
    def get_current_page(self) -> PdfPage:
        page = self.pages[self.current_page_index]
        page.load_words()
        return page

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
