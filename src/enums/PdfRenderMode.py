import enum


class PdfRenderMode(enum.IntEnum):
    DEFAULT = 0
    BORDER = 1
    FILL_AND_STROKE = 2
    INVISIBLE = 3