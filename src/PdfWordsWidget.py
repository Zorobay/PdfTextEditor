import uuid

from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu

from src.PdfDocument import PdfWord
from src.decorators.LogDecorator import log

COLUMNS = ['Text', 'x0, y0', 'Width', 'Height']

ROW_DELETED_COLOR = QColor(255, 0, 0, 100)
ROW_EDITED_COLOR = QColor(0, 0, 255, 100)

EDITABLE_COLS = [0]


class TableItem(QTableWidgetItem):

    def __init__(self, value: str, word: PdfWord):
        super().__init__(value)
        self.word = word

        if self.word.is_marked_for_deletion():
            self.style_deleted()
        elif self.word.is_edited():
            self.style_edited()

    def set_editable(self, editable: bool) -> None:
        if editable:
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def style_deleted(self):
        self.setBackground(ROW_DELETED_COLOR)
        font = self.font()
        font.setStrikeOut(True)
        self.setFont(font)

    def style_edited(self):
        self.setBackground(ROW_EDITED_COLOR)


def word_to_values(word: PdfWord) -> list[str]:
    return [word.text(), f'({word.rect.x0:.2f}, {word.rect.y0:.2f})', f'{word.width():.2f}',
            f'{word.height():.2f}']


class PdfWordsWidget(QTableWidget):
    word_selected = pyqtSignal(uuid.UUID)
    word_deleted = pyqtSignal(uuid.UUID)
    word_edited = pyqtSignal(uuid.UUID)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Vars
        self._words: list[PdfWord] = []
        self._word_row_index: dict[uuid.UUID, int] = dict()
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(COLUMNS)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.cellClicked.connect(self._on_cell_clicked)
        self.currentCellChanged.connect(self._on_cell_clicked)
        self.itemChanged.connect(self._on_item_changed)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    @log
    def set_word_boxes(self, words: list[PdfWord]) -> None:
        self.blockSignals(True)
        try:
            self._words = []
            self._word_row_index = dict()
            self.setRowCount(len(words))

            for row, word in enumerate(words):
                values = word_to_values(word)
                for col, row_val in enumerate(values):
                    item = TableItem(row_val, word)
                    if col not in EDITABLE_COLS:
                        item.set_editable(False)

                    self.setItem(row, col, item)
                    
                self._words.append(word)
                self._word_row_index[word.uuid] = row
                self.update_word(word, row)
        finally:
            self.blockSignals(False)

    def get_word_row(self, word_id: uuid.UUID) -> int:
        return self._word_row_index[word_id]

    def mark_row_for_deletion(self, row: int):
        for col in range(self.columnCount()):
            item: TableItem = self.item(row, col)
            if item:
                item.style_deleted()

    def select_row(self, word_id: uuid.UUID) -> None:
        row = self.get_word_row(word_id)
        self.selectRow(row)

    def toggle_show_space_only_text(self, show: bool) -> None:
        for row in range(self.rowCount()):
            word = self._words[row]
            self.setRowHidden(row, word.is_only_space() and not show)

    def update_word_by_id(self, word_id: uuid.UUID) -> None:
        row = self.get_word_row(word_id)
        word = self._words[row]
        self.update_word(word, row)

    def update_word(self, word: PdfWord, row: int) -> None:
        if word.is_marked_for_deletion():
            self.mark_row_for_deletion(row)
        elif word.is_edited():
            updated_values = word_to_values(word)
            for col in range(self.columnCount()):
                item: TableItem = self.item(row, col)

                if item:
                    item.setText(updated_values[col])
                    item.style_edited()

    def _on_cell_clicked(self, row: int, column: int):
        if 0 < row < len(self._words):
            self.word_selected.emit(self._words[row].uuid)

    def _on_item_changed(self, item: TableItem):
        row = item.row()
        if row < 0 or row > len(self._words):
            return
        if item.column() not in EDITABLE_COLS:
            return

        new_text = item.text()
        word = self._words[row]
        word.edit_text(new_text)
        item.style_edited()
        self.word_edited.emit(word.uuid)

    def _show_context_menu(self, pos: QPoint) -> None:
        row = self.rowAt(pos.y())
        if row < 0:
            return

        self.selectRow(row)

        menu = QMenu(self)
        delete_action = QAction('Mark for deletion', self)
        delete_action.triggered.connect(lambda: self._on_row_deleted(row))
        menu.addAction(delete_action)
        menu.exec(self.viewport().mapToGlobal(pos))

    def _on_row_deleted(self, row: int):
        self.mark_row_for_deletion(row)
        self.word_deleted.emit(self._words[row].uuid)
