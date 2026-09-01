from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor, QBrush

MIN_ZOOM = 0.2
MAX_ZOOM = 8.0
DEFAULT_PEN = QPen(QColor(0, 0, 255, 200))
DEFAULT_BRUSH = QBrush(QColor(255, 255, 0, 20))

HIGHTLIGHT_PEN = QPen(QColor(0, 255, 0, 200))
HIGHTLIGHT_BRUSH = QBrush(QColor(255, 255, 0, 60))

DELETED_PEN = QPen(QColor(255, 0, 0, 200))

DRAW_PREVIEW_PEN = QPen(QColor(30, 120, 220, 220))
DRAW_PREVIEW_PEN.setStyle(Qt.PenStyle.DashLine)

# How close (in scene/pixel units) the cursor needs to be to an edge to
# grab it. 
EDGE_GRAB_MARGIN = 6.0

# Smallest allowed box size (pixels, pre-zoom-conversion) - stops a drag
# from collapsing/inverting the rect.
MIN_SIZE_PIX = 4.0
