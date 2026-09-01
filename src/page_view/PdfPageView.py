import uuid

import pymupdf
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QMouseEvent
from PyQt6.QtWidgets import QGraphicsView, QWidget, QGraphicsScene, QGraphicsPixmapItem

from src.PdfDocument import PdfPage, PdfWord
from src.misc.pdf import qt_rect_to_pdf_rect
from src.page_view.DrawPreviewRect import DrawPreviewRect
from src.page_view.WordGraphicsRect import WordGraphicsRect
from src.page_view.constants import MIN_ZOOM, MAX_ZOOM, MIN_SIZE_PIX


class PdfPageView(QGraphicsView):
    """Displays a single rendered PDF page."""

    word_selected = pyqtSignal(uuid.UUID)
    word_resized = pyqtSignal(uuid.UUID)
    word_drawn = pyqtSignal(pymupdf.Rect, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.page: PdfPage | None = None
        self.zoom = 1.8
        self.zoom_step_size = 1.2
        self._word_rects: dict[uuid.UUID, WordGraphicsRect] = dict()
        self._show_text_boxes = False
        self._show_space_text_boxes = False

        self.scene = QGraphicsScene()
        self.pixmap_item: QGraphicsPixmapItem | None = None

        self._draw_box_mode = False
        self._draw_box_top_left_anchor: QPointF | None = None
        self._draw_box_preview_item: DrawPreviewRect | None = None

        self.setScene(self.scene)
        self.setRenderHint(
            self.renderHints()
            | QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_draw_mode(self, enabled: bool) -> None:
        self._draw_box_mode = enabled
        if self._draw_box_mode:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.viewport().unsetCursor()

    def zoom_in(self):
        self.set_zoom(self.zoom * self.zoom_step_size)

    def zoom_out(self):
        self.set_zoom(self.zoom / self.zoom_step_size)

    def set_zoom(self, zoom: float):
        self.zoom = max(MIN_ZOOM, min(zoom, MAX_ZOOM))
        self._render_active_page()

    def render_page(self, page: PdfPage) -> None:
        self.page = page
        self._render_active_page()

    def mark_word_box_for_deletion(self, word_id: uuid.UUID):
        wb = self._word_rects[word_id]
        wb.style_marked_for_deletion()

    def clear(self) -> None:
        self.scene.clear()
        self._word_rects = dict()
        self.pixmap_item = None

    def add_word(self, word: PdfWord) -> None:
        gr = WordGraphicsRect(word, self.zoom)
        gr.set_resize_callback(self._on_item_resize)
        self.scene.addItem(gr)
        gr.setVisible(self._show_text_boxes)
        self._word_rects[gr.word_id] = gr

    def toggle_text_boxes(self, enabled: bool):
        self._show_text_boxes = enabled
        if enabled:
            self._display_word_boxes()
        else:
            self._hide_word_boxes()

    def toggle_space_text_boxes(self, enabled: bool) -> None:
        self._show_space_text_boxes = enabled
        for _, word in self._word_rects.items():
            if word.word.is_only_space():
                if enabled:
                    word.show()
                else:
                    word.hide()

    def highlight_word_box(self, word_id: uuid.UUID):
        for rect in self._word_rects.values():
            rect.reset_style()

        self._word_rects[word_id].style_highlight()

    # ================================================================
    # --------------------- Event overrides -------------------------
    # ================================================================
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._draw_box_mode:
            if event.button() == Qt.MouseButton.RightButton:
                # Cancel drawing when right-clicking
                self._cancel_draw_box()
                return

            # Drawing new word box
            pos = self.mapToScene(event.pos())
            self._draw_box_top_left_anchor = pos
            self._draw_box_preview_item = DrawPreviewRect(QRectF(pos, pos))
            self.scene.addItem(self._draw_box_preview_item)
            event.accept()
            return

        super().mousePressEvent(event)

        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(item, WordGraphicsRect):
            self.word_selected.emit(item.word_id)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._draw_box_mode and self._draw_box_top_left_anchor:
            # Drawing has started
            pos = self.mapToScene(event.pos())
            rect = QRectF(self._draw_box_top_left_anchor, pos).normalized()
            self._draw_box_preview_item.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._draw_box_mode and self._draw_box_top_left_anchor:
            pos = self.mapToScene(event.pos())
            self._commit_draw_box(pos)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _render_active_page(self):
        if not self.page:
            return

        self._set_pixmap(self.page.get_pixmap(self.zoom))
        self._build_word_boxes()
        self.toggle_text_boxes(self._show_text_boxes)
        self.toggle_space_text_boxes(self._show_space_text_boxes)

    def _commit_draw_box(self, end_pos: QPointF) -> None:
        rect = QRectF(self._draw_box_top_left_anchor, end_pos).normalized()
        self._cancel_draw_box()

        if rect.width() < MIN_SIZE_PIX or rect.height() < MIN_SIZE_PIX:
            return

        pdf_rect = qt_rect_to_pdf_rect(rect, self.zoom)
        self.word_drawn.emit(pdf_rect, '???')

    def _cancel_draw_box(self) -> None:
        if self._draw_box_preview_item:
            self.scene.removeItem(self._draw_box_preview_item)

        self._draw_box_preview_item = None
        self._draw_box_top_left_anchor = None
        self.set_draw_mode(False)

    def _hide_word_boxes(self):
        for rect in self._word_rects.values():
            rect.hide()

    def _build_word_boxes(self):
        if not self.page:
            return

        self._word_rects = dict()
        for word in self.page.get_words():
            self.add_word(word)

    def _display_word_boxes(self):
        if not self.page:
            return

        for wb in self._word_rects.values():
            wb.show()

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        self.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

    def _on_item_resize(self, item: WordGraphicsRect) -> None:
        item.word.resize(item.rect(), self.zoom)
        self.word_resized.emit(item.word_id)
