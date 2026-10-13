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
    BASE_URL = os.environ.get("BASE_URL", "https://womens-safety-device.onrender.com")

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

    # WhatsApp Cloud API Credentials (Meta)
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    WHATSAPP_RECIPIENT_PHONE_NUMBER = os.environ.get("WHATSAPP_RECIPIENT_PHONE_NUMBER", "+919976963200").strip()

    # Twilio WhatsApp Credentials
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "+17372583742").strip()
    TWILIO_WHATSAPP_TO = os.environ.get("TWILIO_WHATSAPP_TO", "+919976963200").strip()
    TWILIO_CONTENT_SID = os.environ.get("TWILIO_CONTENT_SID", "HXfe5ab5f00277942d4d4200328b4d403c").strip()

    # Cloudinary Cloud Storage (for persistent file hosting on Render free tier)
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    @classmethod
    def is_twilio_configured(cls) -> bool:
        """Check if Twilio WhatsApp credentials are provided."""
        to_number = cls.TWILIO_WHATSAPP_TO or cls.WHATSAPP_RECIPIENT_PHONE_NUMBER
        return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN and to_number)

    @classmethod
    def is_meta_whatsapp_configured(cls) -> bool:
        """Check if Meta WhatsApp Cloud API credentials are provided."""
        return bool(cls.WHATSAPP_TOKEN and cls.WHATSAPP_PHONE_NUMBER_ID and cls.WHATSAPP_RECIPIENT_PHONE_NUMBER)

    @classmethod
    def is_whatsapp_configured(cls) -> bool:
        """Check if either Twilio or Meta WhatsApp credentials are provided."""
        return cls.is_twilio_configured() or cls.is_meta_whatsapp_configured()

    @classmethod
    def is_cloudinary_configured(cls) -> bool:
        """Check if Cloudinary credentials are set. When True, all uploads go to Cloudinary."""
        return bool(cls.CLOUDINARY_CLOUD_NAME and cls.CLOUDINARY_API_KEY and cls.CLOUDINARY_API_SECRET)
