from PyQt6.QtWidgets import QGraphicsRectItem

from src.page_view.constants import DRAW_PREVIEW_PEN


class DrawPreviewRect(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setPen(DRAW_PREVIEW_PEN)
        self.setZValue(2)
