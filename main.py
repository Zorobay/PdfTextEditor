import sys

from PyQt6.QtWidgets import QApplication

from src.MainWindow import MainWindow


def main() -> None:
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
    
        sys.exit(app.exec())
    except Exception as e:
        print(f'ERROR: {str(e)}')
    
if __name__ == '__main__':
    main()