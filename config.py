import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Used to sign session cookies and CSRF tokens. Change this in production
    # and load it from an environment variable instead of hardcoding it.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'skill_exchange.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Legacy chat image uploads (kept so old messages still display)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "chat")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # Private storage for chat attachments (any file type). Served only through an
    # authenticated route, never directly from /static.
    CHAT_FILES_FOLDER = os.path.join(BASE_DIR, "instance", "chat_files")
    MAX_UPLOAD_MB = 25
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
