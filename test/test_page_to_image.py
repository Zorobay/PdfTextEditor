import sys
import time
from statistics import mean

from PyQt6.QtWidgets import QApplication

from src.pdf.PdfDocument import PdfDocument

SCALE = 0.12
START_PAGE = 10
END_PAGE = 20


def test_pixmap(doc: PdfDocument):
    print(f'==== test_pixmap() ====')
    times = []
    i = 1
    for page in doc.pages[START_PAGE:END_PAGE]:
        start = time.perf_counter()
        page.get_pixmap(SCALE)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f'\tFinished page {i} in {elapsed:.2f}s')
        i += 1

    avg_time = mean(times)
    print(f'[get_pixmap()] Average Time ({END_PAGE - START_PAGE} pages): {avg_time:.2f}s')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    path = sys.argv[1]
    doc = PdfDocument(path)
    test_pixmap(doc)
