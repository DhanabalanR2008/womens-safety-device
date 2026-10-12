import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the current directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Application configuration loaded from environment variables."""
    BASE_DIR = BASE_DIR

    # On Render, the persistent disk is mounted at /opt/render/project/src/uploads
    # Locally it stays in the project folder
    _UPLOAD_ENV = os.environ.get("UPLOAD_FOLDER")
    UPLOAD_FOLDER = Path(_UPLOAD_ENV) if _UPLOAD_ENV else BASE_DIR / "uploads"

    # Store DB in the project directory (not inside uploads)
    DATABASE_PATH = BASE_DIR / "safety_alerts.db"

    # Flask Core
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-please-change-in-production")
    FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
    BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{FLASK_PORT}")

    # Maximum file upload size: 50 MB
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    # File extensions
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg"}
    ALLOWED_AUDIO_EXTENSIONS = {"wav"}

    # Dashboard Login Credentials
    DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
    DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

    # ESP32 Device Upload Token
    DEVICE_UPLOAD_TOKEN = os.environ.get("DEVICE_UPLOAD_TOKEN", "esp32-safety-device-secret-token-xyz987")

    # WhatsApp Cloud API Credentials
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    WHATSAPP_RECIPIENT_PHONE_NUMBER = os.environ.get("WHATSAPP_RECIPIENT_PHONE_NUMBER", "").strip()

    # Cloudinary Cloud Storage (for persistent file hosting on Render free tier)
    # Sign up free at https://cloudinary.com — no credit card required
    # Copy credentials from: Dashboard → Account Details
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    @classmethod
    def is_whatsapp_configured(cls) -> bool:
        """Check if all required WhatsApp credentials are provided."""
        return bool(cls.WHATSAPP_TOKEN and cls.WHATSAPP_PHONE_NUMBER_ID and cls.WHATSAPP_RECIPIENT_PHONE_NUMBER)

    @classmethod
    def is_cloudinary_configured(cls) -> bool:
        """Check if Cloudinary credentials are set. When True, all uploads go to Cloudinary."""
        return bool(cls.CLOUDINARY_CLOUD_NAME and cls.CLOUDINARY_API_KEY and cls.CLOUDINARY_API_SECRET)
