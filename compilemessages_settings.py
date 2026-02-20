from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

USE_I18N = True
LANGUAGE_CODE = "en"

INSTALLED_APPS = []
LOCALE_PATHS = [str(BASE_DIR / "locale")]

