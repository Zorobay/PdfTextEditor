import uuid

import pymupdf
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import QMainWindow, QStatusBar, QToolBar, QLabel, QFileDialog, QMessageBox, QDockWidget, QWidget, \
    QVBoxLayout

from src import Settings
from src.PageSliderWidget import PageSliderWidget
from src.PdfDocument import PdfDocument
from src.PdfWordsWidget import PdfWordsWidget
from src.page_view.PdfPageView import PdfPageView


class CentralWidget(QWidget):
    def __init__(self, parent=QWidget):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def add_widget(self, widget: QWidget) -> None:
        self.layout.addWidget(widget)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Vars
        self.doc: PdfDocument | None = None

        # Actions
        self.toggle_text_boxes_action = QAction('Show Text Boxes', self)
        self.toggle_show_space_boxes_action = QAction('Show Space Text', self)

        # Widgets
        self.central_widget = CentralWidget(self)
        self.page_view = PdfPageView(self)
        self.page_slider_widget = PageSliderWidget(self)
        self.status_label = QLabel('No document loaded')
        self.status_bar = self.build_status_bar()
        self.file_tool_bar = None
        self.word_tool_bar = None
        self.tools_tool_bar = None
        self.right_dock_widget = QDockWidget('Words', self)
        self.pdf_words_widget = PdfWordsWidget()

        # Configure Widgets
        self.build_tool_bar()
        self.page_slider_widget.page_selected.connect(self._on_page_slider_page_selected)
        self.central_widget.add_widget(self.page_view)
        self.central_widget.add_widget(self.page_slider_widget)

        # Config
        self.setWindowTitle(self._get_window_title())
        self.resize(1200, 1200)
        self.setCentralWidget(self.central_widget)

        # Signals
        self.pdf_words_widget.word_selected.connect(self._on_word_selected)
        self.pdf_words_widget.word_deleted.connect(self._on_words_row_deleted)
        self.page_view.word_selected.connect(self._on_word_selected)
        self.page_view.word_resized.connect(self._on_word_resize)
        self.page_view.word_drawn.connect(self._on_word_drawn)

        # Configure dockable widgets
        self.right_dock_widget.setWidget(self.pdf_words_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock_widget)
        self.resizeDocks([self.right_dock_widget], [300], Qt.Orientation.Horizontal)

    def build_status_bar(self) -> QStatusBar:
        status_bar = QStatusBar()
        status_bar.addWidget(self.status_label)
        self.setStatusBar(status_bar)
        return status_bar

    def build_tool_bar(self) -> None:
        # --------- File Tool Bar -----------
        self.file_tool_bar = QToolBar('File', self)

        open_action = QAction('Open', self)
        open_action.triggered.connect(self._on_open_action_triggered)
        self.file_tool_bar.addAction(open_action)

        save_page_action = QAction('Save As', self)
        save_page_action.triggered.connect(self._on_save_action_triggered)
        self.file_tool_bar.addAction(save_page_action)

        save_debug_action = QAction('Save Debug As', self)
        save_debug_action.triggered.connect(self._on_save_debug_action_triggered)
        self.file_tool_bar.addAction(save_debug_action)

        self.file_tool_bar.addSeparator()

        prev_page_action = QAction('< Prev', self)
        prev_page_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousPage)
        prev_page_action.triggered.connect(self._on_prev_page)
        self.file_tool_bar.addAction(prev_page_action)

        next_page_action = QAction('Next >', self)
        next_page_action.setShortcut(QKeySequence.StandardKey.MoveToNextPage)
        next_page_action.triggered.connect(self._on_next_page)
        self.file_tool_bar.addAction(next_page_action)

        self.file_tool_bar.addSeparator()

        zoom_out_action = QAction('Zoom -', self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_out_action.triggered.connect(self._zoom_out)
        self.file_tool_bar.addAction(zoom_out_action)

        zoom_in_action = QAction('Zoom +', self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        self.file_tool_bar.addAction(zoom_in_action)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.file_tool_bar)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        # --------- Words Tool Bar -----------
        self.word_tool_bar = QToolBar('Words', self)

        self.toggle_text_boxes_action.setCheckable(True)
        self.toggle_text_boxes_action.setToolTip('Toggles between showing and hiding bounding boxes around text words')
        self.toggle_text_boxes_action.setStatusTip(
            'Toggles between showing and hiding bounding boxes around text words')
        self.toggle_text_boxes_action.toggled.connect(self._on_toggle_text_boxes)
        self.word_tool_bar.addAction(self.toggle_text_boxes_action)

        self.toggle_show_space_boxes_action.setCheckable(True)
        self.toggle_show_space_boxes_action.toggled.connect(self._on_toggle_show_space_boxes)
        self.word_tool_bar.addAction(self.toggle_show_space_boxes_action)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.word_tool_bar)

        # --------- "Tools" Tool Bar -----------
        self.tools_tool_bar = QToolBar('Tools', self)

        add_box_descr = 'Draw new word box'
        add_box_action = QAction(QIcon('res/svg/add_word_box_icon.svg'), add_box_descr, self)
        add_box_action.setToolTip(add_box_descr)
        add_box_action.setStatusTip(add_box_descr)
        add_box_action.triggered.connect(self._on_add_box_action_triggered)
        self.tools_tool_bar.addAction(add_box_action)

        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.tools_tool_bar)

    def _on_open_action_triggered(self):
        last_path = Settings.get_last_path()
        path, _ = QFileDialog.getOpenFileName(self, 'Open PDF', last_path, 'PDF Files (*.pdf)')

        if path:
            try:
                self._load_document(path)
            except Exception as e:
                QMessageBox.critical(self, 'Failed to open PDF', str(e))

    def _load_document(self, path: str, page_index: int = 0) -> None:
        self.doc = PdfDocument(path)
        self.doc.set_current_page(page_index)
        self.page_view.render_page(self.doc.get_current_page())
        self.page_slider_widget.set_document(self.doc)
        self._update_status()
        self._update_word_boxes_table()
        Settings.save_last_path(path)

    def _on_save_action_triggered(self):
        last_path = Settings.get_last_path()
        path, _ = QFileDialog.getSaveFileName(self, 'Save PDF As', last_path, 'PDF File (*.pdf)')

        if path:
            current_page = self.doc.current_page_index
            self.doc.save_as(path)
            self._load_document(path, current_page)

    def _on_save_debug_action_triggered(self) -> None:
        last_path = Settings.get_last_path()
        path, _ = QFileDialog.getSaveFileName(self, 'Save Debug PDF As', last_path, 'PDF File (*.pdf)')

        if path:
            self.doc.saveas_debug(path)

    def _on_word_selected(self, word_id: uuid.UUID):
        self.page_view.highlight_word_box(word_id)
        self.pdf_words_widget.select_row(word_id)

    def _on_word_resize(self, word_id: uuid.UUID):
        self.pdf_words_widget.update_word_by_id(word_id)

    def _on_word_drawn(self, rect: pymupdf.Rect, text: str) -> None:
        word = self.doc.add_new_word(rect, text)
        self.pdf_words_widget.add_word_to_table(word)
        self.page_view.add_word(word)

    def _on_words_row_deleted(self, word_id: uuid.UUID):
        self.doc.mark_word_for_deletion(word_id)
        self.page_view.mark_word_box_for_deletion(word_id)

    def _on_toggle_text_boxes(self, enabled: bool) -> None:
        self.page_view.toggle_text_boxes(enabled)
        self._on_toggle_show_space_boxes(self.toggle_show_space_boxes_action.isChecked())

    def _on_toggle_show_space_boxes(self, enabled: bool) -> None:
        self.page_view.toggle_space_text_boxes(enabled)
        self.pdf_words_widget.toggle_show_space_only_text(enabled)

    def _on_add_box_action_triggered(self) -> None:
        self.page_view.set_draw_mode(True)
        
    def _on_page_slider_page_selected(self, page_index: int) -> None:
        self.page_view.render_page(self.doc.set_current_page(page_index))
        self._update_word_boxes_table()

    def _on_next_page(self):
        self.page_view.render_page(self.doc.set_next_page())
        self.page_slider_widget.set_active_page(self.doc.current_page_index)
        self._update_word_boxes_table()

    def _on_prev_page(self):
        self.page_view.render_page(self.doc.set_prev_page())
        self.page_slider_widget.set_active_page(self.doc.current_page_index)
        self._update_word_boxes_table()

    def _zoom_out(self):
        self.page_view.zoom_out()
        self._update_status()

    def _zoom_in(self):
        self.page_view.zoom_in()
        self._update_status()

    def _update_status(self):
        self.setWindowTitle(self._get_window_title())
        self.status_label.setText(f'Page {self.doc.current_page_index + 1} / {self.doc.page_count()}   '
                                  f'Zoom {self.page_view.zoom:.0%}')

    def _update_word_boxes_table(self):
        self.pdf_words_widget.set_word_boxes(self.doc.get_words_current_page())
        self.pdf_words_widget.toggle_show_space_only_text(self.toggle_show_space_boxes_action.isChecked())

    def _get_window_title(self):
        if self.doc:
            return f'PDF Text Editor - {self.doc.path}'
        return 'PDF Text Editor'
