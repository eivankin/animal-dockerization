import os

EMAIL_REGEX = r"^[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*@[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*$"
DB_URL = os.environ.get("DB_URL", "sqlite:///db.sqlite3")
DEBUG = os.environ.get("DEBUG", True)
