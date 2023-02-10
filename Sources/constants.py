import os

EMAIL_REGEX = r"^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*@[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*$"
NON_BLANK_REGEX = r"[^\s]"
DB_URL = os.environ.get("DB_URL", "sqlite://:memory:")
DEBUG = os.environ.get("DEBUG", True)
