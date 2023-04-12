import os

DB_URL = os.environ.get("DB_URL", "sqlite://:memory:")
DEBUG = os.environ.get("DEBUG", True)
