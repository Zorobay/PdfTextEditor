import typing
import uuid

from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QMouseEvent
from PyQt6.QtWidgets import QGraphicsView, QWidget, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, \
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent

from src.PdfDocument import PdfPage, PdfWord
from src.enums.GraphicsRectStyle import GraphicsRectStyle
from src.enums.RectEdge import RectEdge

MIN_ZOOM = 0.2
MAX_ZOOM = 8.0
DEFAULT_PEN = QPen(QColor(0, 0, 255, 200))
HIGHTLIGHT_PEN = QPen(QColor(0, 255, 0, 200))
DELETED_PEN = QPen(QColor(255, 0, 0, 200))
DEFAULT_BRUSH = QBrush(QColor(255, 255, 0, 20))
HIGHTLIGHT_BRUSH = QBrush(QColor(255, 255, 0, 60))

# How close (in scene/pixel units) the cursor needs to be to an edge to
# grab it. 
EDGE_GRAB_MARGIN = 6.0


def is_diff_within_tolerance(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


class GraphicsRect(QGraphicsRectItem):
    DEFAULT_CURSOR = Qt.CursorShape.PointingHandCursor
    # Smallest allowed box size (pixels, pre-zoom-conversion) - stops a drag
    # from collapsing/inverting the rect.
    MIN_SIZE_PIX = 4.0

    def __init__(self, word: PdfWord, scale: float):
        super().__init__(word.to_qrect(scale))

        self.word_id: uuid.UUID = word.uuid
        self.word = word
        self.scale = scale
        self.active_style: GraphicsRectStyle = GraphicsRectStyle.DEFAULT

        self._resize_edge: RectEdge | None = None
        self._resize_start_pos: QPointF | None = None
        self._resize_start_rect: QRectF | None = None
        self._resize_callback:typing.Callable|None = None

        self._init()

    def _init(self) -> None:
        self.setAcceptHoverEvents(True)
        self.setCursor(self.DEFAULT_CURSOR)
        self.setZValue(1)

        if self.is_marked_for_deletion():
            self.style_marked_for_deletion()
        else:
            self.reset_style()
            
    def set_resize_callback(self, callback: typing.Callable) -> None:
        self._resize_callback = callback

    def is_marked_for_deletion(self) -> bool:
        return self.word.is_marked_for_deletion()

    def reset_style(self):
        if self.is_marked_for_deletion():
            self.style_marked_for_deletion()
        else:
            self.style_default()

    def style_default(self) -> None:
        self.setPen(DEFAULT_PEN)
        self.setBrush(DEFAULT_BRUSH)
        self.active_style = GraphicsRectStyle.DEFAULT

    def style_highlight(self):
        self.setPen(HIGHTLIGHT_PEN)
        self.setBrush(HIGHTLIGHT_BRUSH)
        self.active_style = GraphicsRectStyle.HIGHLIGHT

    def style_marked_for_deletion(self):
        self.setPen(DELETED_PEN)
        self.active_style = GraphicsRectStyle.MARKED_FOR_DELETION

    def hide(self) -> None:
        self.setVisible(False)

    def show(self) -> None:
        self.setVisible(True)

    def _is_position_at_left_edge(self, pos: QPointF) -> bool:
        return is_diff_within_tolerance(self.rect().left(), pos.x(), self.MIN_SIZE_PIX)

    def _is_position_at_right_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().right(), pos.x(), self.MIN_SIZE_PIX)

    def _is_position_at_top_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().top(), pos.y(), self.MIN_SIZE_PIX)

    def _is_position_at_bottom_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().bottom(), pos.y(), self.MIN_SIZE_PIX)

    def _get_nearest_edge(self, pos: QPointF) -> RectEdge | None:
        if self._is_position_at_left_edge(pos):
            return RectEdge.LEFT
        if self._is_position_at_right_edge(pos):
            return RectEdge.RIGHT
        if self._is_position_at_top_edge(pos):
            return RectEdge.TOP
        if self._is_position_at_bottom_edge(pos):
            return RectEdge.BOTTOM

        return None
    
    def _clamp_rect_to_page_bounds(self, rect: QRectF) -> None:
        scene = self.scene()
        if not scene:
            return
        
        bounds = scene.sceneRect()
        
        rect.setLeft(max(bounds.left(), rect.left()))
        rect.setRight(min(bounds.right(), rect.right()))
        rect.setTop(max(bounds.top(), rect.top()))
        rect.setBottom(min(bounds.bottom(), rect.bottom()))

    # --- Event overrides ---
    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        nearest_edge = self._get_nearest_edge(event.pos())
        if nearest_edge and nearest_edge.is_horizontal():
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif nearest_edge and nearest_edge.is_vertical():
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(self.DEFAULT_CURSOR)

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        nearest_edge = self._get_nearest_edge(event.pos())
        if nearest_edge:
            self._resize_edge = nearest_edge
            self._resize_start_rect = self.rect()
            self._resize_start_pos = event.pos()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if not self._resize_edge:  # No resize started
            super().mouseMoveEvent(event)
            return
        
        delta = event.pos() - self._resize_start_pos
        new_rect = QRectF(self._resize_start_rect)
        
        if self._resize_edge == RectEdge.LEFT:
            new_rect.setLeft(min(new_rect.left() + delta.x(), new_rect.right() - self.MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.RIGHT:
            new_rect.setRight(max(new_rect.right() + delta.x(), new_rect.left() + self.MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.TOP:
            new_rect.setTop(min(new_rect.top() + delta.y(), new_rect.bottom() - self.MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.BOTTOM:
            new_rect.setBottom(max(new_rect.bottom() + delta.y(), new_rect.top() + self.MIN_SIZE_PIX))
            
        self._clamp_rect_to_page_bounds(new_rect)
        self.setRect(new_rect)
        event.accept()
        
        if self._resize_callback:
            self._resize_callback(self)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._resize_edge:
            self.word.resize(self.rect(), self.scale)
            self._resize_edge = None
            self._resize_start_rect = None
            self._resize_start_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PdfPageView(QGraphicsView):
    """Displays a single rendered PDF page."""

    word_selected = pyqtSignal(uuid.UUID)
    word_resized = pyqtSignal(uuid.UUID)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.page: PdfPage | None = None
        self.zoom = 1.8
        self.zoom_step_size = 1.2
        self._word_rects: dict[uuid.UUID, GraphicsRect] = dict()
        self._show_text_boxes = False
        self._show_space_text_boxes = False

        self.scene = QGraphicsScene()
        self.pixmap_item: QGraphicsPixmapItem | None = None

        self.setScene(self.scene)
        self.setRenderHint(
            self.renderHints()
            | QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(item, GraphicsRect):
            self.word_selected.emit(item.word_id)

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

    def _render_active_page(self):
        if not self.page:
            return

        self._set_pixmap(self.page.get_pixmap(self.zoom))
        self._build_word_boxes()
        self.toggle_text_boxes(self._show_text_boxes)
        self.toggle_space_text_boxes(self._show_space_text_boxes)

    def clear(self) -> None:
        self.scene.clear()
        self._word_rects = dict()
        self.pixmap_item = None

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

    def _hide_word_boxes(self):
        for rect in self._word_rects.values():
            rect.hide()

    def _build_word_boxes(self):
        if not self.page:
            return

        self._word_rects = dict()
        for word in self.page.get_words():
            gr = GraphicsRect(word, self.zoom)
            gr.set_resize_callback(self._on_item_resize)
            self.scene.addItem(gr)
            gr.hide()
            self._word_rects[gr.word_id] = gr

    def _display_word_boxes(self):
        if not self.page:
            return

        for wb in self._word_rects.values():
            wb.show()

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        self.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        
    def _on_item_resize(self, item: GraphicsRect) -> None:
        item.word.resize(item.rect(), self.zoom)
        self.word_resized.emit(item.word_id)
