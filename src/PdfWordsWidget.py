from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu

from src.PdfDocument import WordBox

COLUMNS = ['Text', 'x0, y0', 'Width', 'Height']

ROW_DELETED_COLOR = QColor(255, 0, 0, 100)


class PdfWordsWidget(QTableWidget):
    row_selected = pyqtSignal(int)
    row_deleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Vars
        self.word_boxes: list[WordBox] = []
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(COLUMNS)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.cellClicked.connect(self._on_cell_clicked)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_word_boxes(self, word_boxes: list[WordBox]) -> None:
        self.word_boxes = word_boxes
        self.setRowCount(len(self.word_boxes))

        for row, box in enumerate(self.word_boxes):
            values = [box.text, f'({box.rect.x0:.2f}, {box.rect.y0:.2f})', f'{box.width():.2f}', f'{box.height():.2f}']
            for col, row_val in enumerate(values):
                item = QTableWidgetItem(row_val)
                self.setItem(row, col, item)

    def mark_row_for_deletion(self, row: int):
        self.word_boxes[row].mark_for_deletion()
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(ROW_DELETED_COLOR)
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)

    def _on_cell_clicked(self, row: int, column: int):
        self.row_selected.emit(row)

    def _show_context_menu(self, pos: QPoint) -> None:
        row = self.rowAt(pos.y())
        if row < 0:
            return

        self.selectRow(row)

        menu = QMenu(self)
        delete_action = QAction('Mark for deletion', self)
        delete_action.triggered.connect(lambda: self.row_deleted.emit(row))
        menu.addAction(delete_action)
        menu.exec(self.viewport().mapToGlobal(pos))
