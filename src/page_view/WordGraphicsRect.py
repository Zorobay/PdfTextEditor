import typing
import uuid

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent

from src.pdf.PdfWord import PdfWord
from src.enums.GraphicsRectStyle import GraphicsRectStyle
from src.enums.RectEdge import RectEdge
from src.misc.math import is_diff_within_tolerance
from src.page_view.constants import DEFAULT_PEN, HIGHTLIGHT_PEN, DELETED_PEN, DEFAULT_BRUSH, HIGHTLIGHT_BRUSH, \
    MIN_SIZE_PIX


class WordGraphicsRect(QGraphicsRectItem):
    DEFAULT_CURSOR = Qt.CursorShape.PointingHandCursor

    def __init__(self, word: PdfWord, scale: float):
        super().__init__(word.to_qrect(scale))

        self.word_id: uuid.UUID = word.uuid
        self.word = word
        self.scale = scale
        self.active_style: GraphicsRectStyle = GraphicsRectStyle.DEFAULT

        self._resize_edge: RectEdge | None = None
        self._resize_start_pos: QPointF | None = None
        self._resize_start_rect: QRectF | None = None
        self._resize_callback: typing.Callable | None = None

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
        return is_diff_within_tolerance(self.rect().left(), pos.x(), MIN_SIZE_PIX)

    def _is_position_at_right_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().right(), pos.x(), MIN_SIZE_PIX)

    def _is_position_at_top_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().top(), pos.y(), MIN_SIZE_PIX)

    def _is_position_at_bottom_edge(self, pos: QPointF):
        return is_diff_within_tolerance(self.rect().bottom(), pos.y(), MIN_SIZE_PIX)

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

    # ================================================================
    # --------------------- Event overrides -------------------------
    # ================================================================
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
        # Resizing existing word box
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
            new_rect.setLeft(min(new_rect.left() + delta.x(), new_rect.right() - MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.RIGHT:
            new_rect.setRight(max(new_rect.right() + delta.x(), new_rect.left() + MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.TOP:
            new_rect.setTop(min(new_rect.top() + delta.y(), new_rect.bottom() - MIN_SIZE_PIX))
        elif self._resize_edge == RectEdge.BOTTOM:
            new_rect.setBottom(max(new_rect.bottom() + delta.y(), new_rect.top() + MIN_SIZE_PIX))

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
