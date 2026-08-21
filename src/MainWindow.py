from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QStatusBar, QToolBar, QLabel, QFileDialog, QMessageBox, QDockWidget

from src.PdfDocument import PdfDocument
from src.PdfPageView import PdfPageView
from src.PdfWordsWidget import PdfWordsWidget


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Vars
        self.doc: PdfDocument | None = None

        # Actions
        self.toggle_text_boxes_action = QAction('Show Text Boxes', self)
        
        # Widgets
        self.page_view = PdfPageView(self)
        self.status_label = QLabel('No document loaded')
        self.status_bar = self.build_status_bar()
        self.tool_bar = self.build_tool_bar()
        self.right_dock_widget = QDockWidget('Words', self)
        self.pdf_words_widget = PdfWordsWidget()       

        # Config
        self.setWindowTitle(self._get_window_title())
        self.resize(1200, 1200)
        self.setCentralWidget(self.page_view)

        # Configure dockable widgets
        self.pdf_words_widget.row_selected.connect(self._on_words_row_selected)
        self.pdf_words_widget.row_deleted.connect(self._on_words_row_deleted)
        self.right_dock_widget.setWidget(self.pdf_words_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock_widget)

    def build_status_bar(self) -> QStatusBar:
        status_bar = QStatusBar()
        status_bar.addWidget(self.status_label)
        self.setStatusBar(status_bar)
        return status_bar

    def build_tool_bar(self) -> QToolBar:
        tool_bar = QToolBar()

        open_action = QAction('Open', self)
        open_action.triggered.connect(self._on_open_action_triggered)
        tool_bar.addAction(open_action)

        tool_bar.addSeparator()

        prev_page_action = QAction('< Prev', self)
        prev_page_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousPage)
        prev_page_action.triggered.connect(self._on_prev_page)
        tool_bar.addAction(prev_page_action)

        next_page_action = QAction('Next >', self)
        next_page_action.setShortcut(QKeySequence.StandardKey.MoveToNextPage)
        next_page_action.triggered.connect(self._on_next_page)
        tool_bar.addAction(next_page_action)

        tool_bar.addSeparator()

        zoom_out_action = QAction('Zoom -', self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_out_action.triggered.connect(self._zoom_out)
        tool_bar.addAction(zoom_out_action)

        zoom_in_action = QAction('Zoom +', self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        tool_bar.addAction(zoom_in_action)

        tool_bar.addSeparator()
        self.toggle_text_boxes_action.setCheckable(True)
        self.toggle_text_boxes_action.toggled.connect(self._on_toggle_text_boxes)
        tool_bar.addAction(self.toggle_text_boxes_action)
        
        tool_bar.addSeparator()
        save_page_action = QAction('Save Page', self)
        save_page_action.triggered.connect(lambda: self.doc.save_current_page())
        tool_bar.addAction(save_page_action)

        self.addToolBar(tool_bar)
        return tool_bar

    def _on_open_action_triggered(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open PDF', r'C:\Users\Sebastian\Hegardt\static_media\pdfs',
                                              'PDF Files (*.pdf)')

        if path:
            try:
                self.doc = PdfDocument(path)
                self.page_view.render_page(self.doc.get_current_page())
                self._update_status()
                self._update_word_boxes_table()
            except Exception as e:
                QMessageBox.critical(self, 'Failed to open PDF', str(e))

    def _on_words_row_selected(self, row: int):
        self.page_view.highlight_word_box(row)

    def _on_words_row_deleted(self, row: int):
        self.pdf_words_widget.mark_row_for_deletion(row)
        self.doc.mark_word_box_for_deletion()
        
    def _on_toggle_text_boxes(self, enabled: bool) -> None:
        self.page_view.toggle_text_boxes(enabled)

    def _on_next_page(self):
        self.doc.increment_page_index()
        self.page_view.render_page(self.doc.get_current_page())
        self._update_word_boxes_table()

    def _on_prev_page(self):
        self.doc.decrement_page_index()
        self.page_view.render_page(self.doc.get_current_page())
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
        self.pdf_words_widget.set_word_boxes(self.page_view.doc.get_word_boxes_current_page())

    def _get_window_title(self):
        if self.doc:
            return f'PDF OCR Editor - {self.doc.path}'
        return 'PDF OCR Editor'
