import time
from concurrent.futures.process import ProcessPoolExecutor

import pymupdf
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QRunnable, QThreadPool, QObject
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage
from PyQt6.QtWidgets import QWidget, QListWidget, QListWidgetItem

from src.pdf.PdfDocument import PdfDocument

ICON_HEIGHT = 80
ICON_WIDTH = 50
ITEM_SPACING = 10
ICON_PADDING = 12
PIXMAP_SCALE = 0.10

_process_pool = ProcessPoolExecutor(max_workers=2)


def _placeholder_icon() -> QIcon:
    pixmap = QPixmap(ICON_WIDTH, ICON_HEIGHT)
    pixmap.fill(QColor(225, 225, 225))
    return QIcon(pixmap)


def render_thumbnail_in_subprocess(path: str, page_index: int, scale: float) -> bytes:
    """Runs in a completely separate OS process. Whatever PyMuPDF does
    internally for this file's encoding, it can only block THIS process -
    the main app process (and its GIL, and its Qt event loop) is untouched."""
    doc = pymupdf.open(path)
    pixmap = doc[page_index].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
    png_bytes = pixmap.tobytes('png')  # plain bytes - safe to send back across the process boundary
    doc.close()
    return png_bytes


class _WorkerSignals(QObject):
    job_done = pyqtSignal(int, QImage, int)


class ThumbnailWorker(QRunnable):

    def __init__(self, row: int, path: str, generation: int):
        super().__init__()
        self.row = row
        self.path = path
        self.generation = generation
        self.signals = _WorkerSignals()

    def run(self):
        start = time.perf_counter()

        future = _process_pool.submit(render_thumbnail_in_subprocess, self.path, self.row, PIXMAP_SCALE)
        png_bytes = future.result()  # blocks THIS background thread, not the main one
        image = QImage.fromData(png_bytes, 'PNG')

        elapsed = time.perf_counter() - start
        print(f'Built thumbnail for page {self.row+1} in {elapsed:.2f}s')

        self.signals.job_done.emit(self.row, image, self.generation)


class PageSliderWidget(QListWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._doc: PdfDocument | None = None
        self._rendered_rows: set[int] = set()
        self._pending_rows: set[int] = set()
        self._generation = 0

        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(1)

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)
        self.setMovement(QListWidget.Movement.Static)
        self.setIconSize(QSize(ICON_WIDTH, ICON_HEIGHT))
        self.setSpacing(ITEM_SPACING)
        self.setUniformItemSizes(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(ICON_HEIGHT + (2 * ICON_PADDING) + 30)

        self.itemClicked.connect(self._on_item_clicked)
        self.horizontalScrollBar().valueChanged.connect(lambda: self._render_visible_rows())

    def set_document(self, document: PdfDocument, page_index:int=0) -> None:
        self._doc = document
        self._generation += 1
        self._rendered_rows = set()
        self._pending_rows = set()
        self._thread_pool.clear()
        self.clear()

        placeholder = _placeholder_icon()
        for i in range(self._doc.page_count()):
            item = QListWidgetItem(placeholder, str(i + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.addItem(item)
            
        
        self.setCurrentRow(page_index)
        self._render_visible_rows()

    def set_active_page(self, page_index: int) -> None:
        self.blockSignals(True)
        try:
            self.setCurrentRow(page_index)
            item = self.item(page_index)
            self.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)
        finally:
            self.blockSignals(False)
        self._render_visible_rows()

    def _render_visible_rows(self) -> None:
        if self._doc is None:
            return
        viewport_rect = self.viewport().rect()
        for row in range(self.count()):
            if row in self._rendered_rows or row in self._pending_rows:
                continue

            item = self.item(row)
            if viewport_rect.intersects(self.visualItemRect(item)):
                job = ThumbnailWorker(row, self._doc.path, self._generation)
                job.signals.job_done.connect(self._on_job_done)
                self._pending_rows.add(row)
                self._thread_pool.start(job)

    def _on_job_done(self, row: int, image: QImage, generation: int) -> None:
        if generation != self._generation:
            # Stale result from a document that's no longer loaded - the
            # widget has already been cleared/repopulated for a different
            # document, so this row index means something else now (or may
            # not exist at all). Discard it rather than applying it.
            return

        self._pending_rows.discard(row)
        item = self.item(row)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(image)))
            self._rendered_rows.add(row)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        self.set_active_page(row)
        self.page_selected.emit(row)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_visible_rows()
