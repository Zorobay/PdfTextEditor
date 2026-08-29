import logging
import sys

from PyQt6.QtWidgets import QApplication

from src.MainWindow import MainWindow


def main() -> None:
    try:
        logging.basicConfig(
            level=logging.DEBUG,  # threshold: INFO and above get shown
            format='%(asctime)s.%(msecs)03d %(name)s %(levelname)s: %(message)s',
            datefmt='%H:%M:%S',
        )
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        print(f'ERROR: {str(e)}')


if __name__ == '__main__':
    main()
