import uuid

from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QAction, QColor, QKeyEvent
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu

from src.pdf.PdfWord import PdfWord
from src.decorators.LogDecorator import log
from src.pdf.PdfWords import PdfWords

COLUMNS = ['Text', 'x0, y0', 'Width', 'Height']

ROW_DELETED_COLOR = QColor(255, 0, 0, 100)
ROW_EDITED_COLOR = QColor(0, 0, 255, 100)

EDITABLE_COLS = [0]


class TableItem(QTableWidgetItem):

    def __init__(self, value: str, word: PdfWord):
        super().__init__(value)
        self.word = word
        self._default_foreground = self.foreground()
        self._default_background = self.background()
        self._default_font = self.font()

        if self.word.is_marked_for_deletion():
            self.style_deleted()
        elif self.word.is_edited():
            self.style_edited()

    def set_editable(self, editable: bool) -> None:
        if editable:
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
    def reset_style(self):
        self.setForeground(self._default_foreground)
        self.setBackground(self._default_background)
        self.setFont(self._default_font)

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
    update_word_with_ocr = pyqtSignal(uuid.UUID)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Vars
        self._words = PdfWords()
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
        
    def clear(self) -> None:
        self._words.clear()
        self.setRowCount(0)

    @log
    def set_word_boxes(self, words: list[PdfWord]) -> None:
        self.blockSignals(True)
        try:
            self.clear()

            for row, word in enumerate(words):
                self.add_word_to_table(word, False)
        finally:
            self.blockSignals(False)

    def get_word_row(self, word_id: uuid.UUID) -> int:
        return self._words.get_index(word_id)

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
            word = self._words.get(row)
            self.setRowHidden(row, word.is_only_space() and not show)

    def add_word_to_table(self, word: PdfWord, block_signals: bool = True) -> None:
        row = self.rowCount()
        self.setRowCount(row + 1)
        values = word_to_values(word)

        try:
            if block_signals:
                self.blockSignals(True)
            for col, row_val in enumerate(values):
                item = TableItem(row_val, word)
                if col not in EDITABLE_COLS:
                    item.set_editable(False)

                self.setItem(row, col, item)

            self._words.add(word)
            self.update_word(word)
        finally:
            if block_signals:
                self.blockSignals(False)

    def update_word_by_id(self, word_id: uuid.UUID) -> None:
        word = self._words.get_by_id(word_id)
        self.update_word(word)

    def update_word(self, word: PdfWord) -> None:
        row = self._words.get_index(word.uuid)
        self.selectRow(row)
        
        if word.is_marked_for_deletion():
            self.mark_row_for_deletion(row)
        elif word.is_edited():
            updated_values = word_to_values(word)
            for col in range(self.columnCount()):
                item: TableItem = self.item(row, col)

                if item:
                    item.setText(updated_values[col])
                    item.style_edited()
                    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete:
            selected_indices = self.selectedIndexes()
            for i in selected_indices:
                self._on_row_deleted(i.row())
            event.accept()
            return 
        
        super().keyPressEvent(event)

    def _on_cell_clicked(self, row: int, column: int):
        if 0 < row < self._words.size():
            self.word_selected.emit(self._words.get(row).uuid)

    def _on_item_changed(self, item: TableItem):
        row = item.row()
        if row < 0 or row > self._words.size():
            return
        if item.column() not in EDITABLE_COLS:
            return

        new_text = item.text()
        word = self._words.get(row)
        word.edit_text(new_text)
        if word.is_edited():
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
        ocr_action = QAction('Run OCR', self)
        ocr_action.triggered.connect(lambda: self._on_row_ocr(row))
        menu.addAction(delete_action)
        menu.addAction(ocr_action)
        menu.exec(self.viewport().mapToGlobal(pos))

    def _on_row_deleted(self, row: int) ->None:
        self.mark_row_for_deletion(row)
        self.word_deleted.emit(self._words.get(row).uuid)
        
    def _on_row_ocr(self, row:int) -> None:
        self.update_word_with_ocr.emit(self._words.get(row).uuid)
        
