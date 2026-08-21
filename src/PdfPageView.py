import pymupdf
from PyQt6.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsView, QWidget, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from src.PdfDocument import PdfDocument

MIN_ZOOM = 0.2
MAX_ZOOM = 8.0
PEN = QPen(QColor(255, 0, 0, 200))
PEN.setWidth(0)  # cosmetic: always 1px on screen regardless of view scale
HIGHTLIGHT_PEN = QPen(QColor(0, 255, 0, 200))
BRUSH = QBrush(QColor(255, 255, 0, 20))
HIGHTLIGHT_BRUSH = QBrush(QColor(255, 255, 0, 60))

class GraphicsRect:

    def __init__(self, q_graphics_item: QGraphicsRectItem):
        super().__init__()
        self._is_highlit = False
        self._q_graphics_item = q_graphics_item

    def is_highlit(self) -> bool:
        return self._is_highlit
    
    def get_item(self) -> QGraphicsRectItem:
        return self._q_graphics_item

    def set_highlight(self, highlight: bool):
        if highlight:
            if not self.is_highlit():
                self._q_graphics_item.setPen(HIGHTLIGHT_PEN)
                self._q_graphics_item.setBrush(HIGHTLIGHT_BRUSH)
                self._is_highlit = True
        else:
            if self.is_highlit():
                self._q_graphics_item.setPen(PEN)
                self._q_graphics_item.setBrush(BRUSH)
                self._is_highlit = False


class PdfPageView(QGraphicsView):
    """Displays a single rendered PDF page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.page: Page | None = None
        self.zoom = 1.8
        self.zoom_step_size = 1.2
        self._word_box_items: list[GraphicsRect] = []
        self._show_text_boxes = False

        self.scene = QGraphicsScene()
        self.pixmap_item: QGraphicsPixmapItem | None = None

        self.setScene(self.scene)
        self.setRenderHint(
            self.renderHints()
            | QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def zoom_in(self):
        self.set_zoom(self.zoom * self.zoom_step_size)

    def zoom_out(self):
        self.set_zoom(self.zoom / self.zoom_step_size)

    def set_zoom(self, zoom: float):
        self.zoom = max(MIN_ZOOM, min(zoom, MAX_ZOOM))
        self._render_active_page()

    def render_page(self, page: pymupdf.Page) -> None:
        self.page = page
        self._render_active_page()

    def _render_active_page(self):
        if not self.page:
            return

        matrix = pymupdf.Matrix(self.zoom, self.zoom)
        pixmap = self.page.get_pixmap(matrix=matrix, alpha=True)
        image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format.Format_RGBA8888)
        # QImage does not own pixmap.samples' buffer, so make a deep copy
        # before the underlying pixmap object is garbage collected.
        image = image.copy()

        self._set_pixmap(QPixmap.fromImage(image))
        if self._show_text_boxes:
            self._display_word_boxes()

    def clear(self) -> None:
        self.scene.clear()
        self._word_box_items = []
        self.pixmap_item = None

    def toggle_text_boxes(self, enabled: bool):
        self._show_text_boxes = enabled
        if enabled:
            self._display_word_boxes()
        else:
            self._clear_word_boxes()

    def highlight_word_box(self, index: int):
        for i, item in enumerate(self._word_box_items):
            item.set_highlight(i == index)

    def _clear_word_boxes(self):
        for item in self._word_box_items:
            self.scene.removeItem(item.get_item())

        self._word_box_items = []

    def _display_word_boxes(self):
        if not self.doc:
            return

        self._clear_word_boxes()
        word_boxes = self.doc.get_word_boxes_current_page()
        scene_rects = [w.to_qrect(self.zoom) for w in word_boxes]
        self._clear_word_boxes()
        for rect in scene_rects:
            item = self.scene.addRect(rect, PEN, BRUSH)
            item.setZValue(1)
            self._word_box_items.append(GraphicsRect(item))

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        self.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
