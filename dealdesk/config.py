import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dealdesk.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TOKEN_ENCRYPTION_KEY = os.environ.get("TOKEN_ENCRYPTION_KEY", "")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    INTERNAL_REFRESH_TOKEN = os.environ.get("INTERNAL_REFRESH_TOKEN", "")

    # Baseline = median of the creator's last N organic posts of the same format.
    BASELINE_WINDOW = 20


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TOKEN_ENCRYPTION_KEY = "d5873AQLom_lmtHZmkpYkrIRtsGO77mzs1KSX1jCWHA="  # test-only key
    WTF_CSRF_ENABLED = False
