from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QSlider, QHBoxLayout, QListWidget, QListWidgetItem

from src.PdfDocument import PdfDocument

ICON_HEIGHT = 80
ICON_WIDTH = 50
ITEM_SPACING = 10
ICON_PADDING = 12
PIXMAP_SCALE = 0.12

class PageSliderWidget(QListWidget):
    
    page_selected = pyqtSignal(int)
    
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        
        self._doc : PdfDocument|None = None

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)
        self.setMovement(QListWidget.Movement.Static)
        self.setIconSize(QSize(ICON_WIDTH, ICON_HEIGHT))
        self.setSpacing(ITEM_SPACING)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(ICON_HEIGHT + (2 * ICON_PADDING) + 26)
        
        self.itemClicked.connect(self._on_item_clicked)
        
    def set_document(self, document: PdfDocument) -> None:
        self._doc = document
        for row, page in enumerate(self._doc.pages):
            pixmap = page.get_pixmap(PIXMAP_SCALE)
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setText(str(row))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.addItem(item)

    def set_active_page(self, page_index: int)->None:
        self.blockSignals(True)
        try:
            self.setCurrentRow(page_index)
            item = self.item(page_index)
            self.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)
        finally:
            self.blockSignals(False)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        self.set_active_page(row)
        self.page_selected.emit(row)
