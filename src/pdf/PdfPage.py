import uuid

import pymupdf
from PyQt6.QtGui import QImage, QPixmap

from src.decorators.LogDecorator import log
from src.enums.PdfRenderMode import PdfRenderMode
from src.pdf.PdfWord import PdfWord
from src.pdf.PdfWords import PdfWords
from src.pdf.constants import DEFAULT_FONT


class PdfPage:
    EXCLUDE_IMAGES_FROM_TEXT_EXTRACTION_FLAGS = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES

    def __init__(self, page: pymupdf.Page):
        self._page = page
        self._loaded = False
        self._words: PdfWords = PdfWords()

    def page(self) -> pymupdf.Page:
        return self._page

    @log
    def load_words(self):
        if self._loaded:
            return
        self._words.clear()
        blocks = self._page.get_text('dict', sort=True, flags=self.EXCLUDE_IMAGES_FROM_TEXT_EXTRACTION_FLAGS).get(
            'blocks', [])

        for block in blocks:
            lines = block.get('lines', [])

            for line in lines:
                spans = line.get('spans', [])

                for span in spans:
                    pdf_word = PdfWord.from_span_dict(span)
                    self._words.add(pdf_word)
        self._loaded = True

    def is_loaded(self) -> bool:
        return self._words.size() > 0

    def get_word(self, word_id: uuid.UUID) -> PdfWord:
        return self._words.get_by_id(word_id)
    
    def get_words(self) -> PdfWords:
        return self._words

    def delete_word(self, word: PdfWord) -> None:
        self._page.add_redact_annot(word.original_rect(), fill=None)

    def add_word(self, word: PdfWord) -> None:
        self._words.add(word)

    def get_image(self, scale: float) -> QImage:
        matrix = pymupdf.Matrix(scale, scale)
        pixmap = self._page.get_pixmap(matrix=matrix, alpha=True)

        # QImage does not own pixmap.samples' buffer, so make a deep copy
        # before the underlying pixmap object is garbage collected.
        return QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format.Format_RGBA8888).copy()

    def get_pixmap(self, scale: float) -> QPixmap:
        return QPixmap.fromImage(self.get_image(scale))

    @log
    def get_raw_image_bytes(self) -> bytes:
        images = self._page.get_images(full=True)
        if not images:
            raise ValueError(f'page {self._page.number} has no embedded image to thumbnail')
        xref = images[0][0]  # For scanned documents, the page should be the first image
        return self._page.parent.extract_image(xref)['image']

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
