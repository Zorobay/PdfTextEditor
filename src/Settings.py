from PyQt6.QtCore import QSettings

APP_KEY_PATH = r'Software\Hegardt\PdfTextEditor'
KEY_NAME_LAST_PATH = 'LastPath'

_settings = QSettings('Hegardt', 'PdfTextEditor')

def save_last_path(path: str) -> None:
    _settings.setValue(KEY_NAME_LAST_PATH, path)


def get_last_path() -> str | None:
    return _settings.value(KEY_NAME_LAST_PATH, None, type=str)
