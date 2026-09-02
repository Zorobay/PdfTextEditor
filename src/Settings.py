from PyQt6.QtCore import QSettings

APP_KEY_PATH = r'Software\Hegardt\PdfTextEditor'
KEY_NAME_LAST_PATH = 'LastPath'

_settings = QSettings('Hegardt', 'PdfTextEditor')

def save_last_path(path: str) -> None:
    _settings.setValue(KEY_NAME_LAST_PATH, path)
    # with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_KEY_PATH) as key:
    #     winreg.SetValue(key, KEY_NAME_LAST_PATH, winreg.REG_SZ, path)


def get_last_path() -> str | None:
    _settings.value(KEY_NAME_LAST_PATH, None, type=str)
    # try:
    #     with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY_PATH) as key:
    #         return winreg.QueryValue(key, KEY_NAME_LAST_PATH)
    # except FileNotFoundError:
    #     return None
