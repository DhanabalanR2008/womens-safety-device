"""
services/cloudinary_storage.py
================================
Handles all file uploads and deletions via the Cloudinary Media API.

When CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET are set in .env,
ALL photos and audio are uploaded to Cloudinary and served via secure
HTTPS URLs — meaning files survive server restarts on Render free tier.

When credentials are NOT set, this module returns None and the app
falls back to saving files locally (fine for development).
"""

import logging
from io import BytesIO
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def _configure():
    """Configure the Cloudinary SDK from environment variables."""
    from config import Config
    import cloudinary
    cloudinary.config(
        cloud_name=Config.CLOUDINARY_CLOUD_NAME,
        api_key=Config.CLOUDINARY_API_KEY,
        api_secret=Config.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_photo(file_bytes: bytes, safe_filename: str, event_folder: str) -> Optional[Dict]:
    """
    Uploads a JPEG photo to Cloudinary.

    Returns:
        {"url": "https://...", "public_id": "safety_alerts/folder/name"}
        or None if Cloudinary is not configured / upload fails.
    """
    from config import Config
    if not Config.is_cloudinary_configured():
        return None

    try:
        import cloudinary.uploader
        _configure()

        # Strip extension from public_id — Cloudinary manages format itself
        public_id_name = safe_filename.rsplit(".", 1)[0]

        result = cloudinary.uploader.upload(
            BytesIO(file_bytes),
            folder=f"safety_alerts/{event_folder}",
            public_id=public_id_name,
            resource_type="image",
            overwrite=False,
            format="jpg",
        )
        logger.info("Cloudinary photo uploaded: %s", result["public_id"])
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }
    except Exception as exc:
        logger.error("Cloudinary photo upload failed: %s", exc)
        return None


def upload_audio(file_bytes: bytes, safe_filename: str, event_folder: str) -> Optional[Dict]:
    """
    Uploads a WAV audio clip to Cloudinary as a raw file.

    Returns:
        {"url": "https://...", "public_id": "safety_alerts/folder/name"}
        or None if Cloudinary is not configured / upload fails.
    """
    from config import Config
    if not Config.is_cloudinary_configured():
        return None

    try:
        import cloudinary.uploader
        _configure()

        public_id_name = safe_filename.rsplit(".", 1)[0]

        result = cloudinary.uploader.upload(
            BytesIO(file_bytes),
            folder=f"safety_alerts/{event_folder}",
            public_id=public_id_name,
            resource_type="raw",   # WAV is a raw binary — not image/video
            overwrite=False,
        )
        logger.info("Cloudinary audio uploaded: %s", result["public_id"])
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }
    except Exception as exc:
        logger.error("Cloudinary audio upload failed: %s", exc)
        return None


def delete_photo(public_id: str) -> bool:
    """Deletes a photo from Cloudinary by its public_id."""
    from config import Config
    if not Config.is_cloudinary_configured() or not public_id:
        return False
    try:
        import cloudinary.uploader
        _configure()
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        logger.info("Cloudinary photo deleted: %s → %s", public_id, result.get("result"))
        return result.get("result") == "ok"
    except Exception as exc:
        logger.error("Cloudinary photo delete failed: %s", exc)
        return False


def delete_audio(public_id: str) -> bool:
    """Deletes an audio file from Cloudinary by its public_id."""
    from config import Config
    if not Config.is_cloudinary_configured() or not public_id:
        return False
    try:
        import cloudinary.uploader
        _configure()
        result = cloudinary.uploader.destroy(public_id, resource_type="raw")
        logger.info("Cloudinary audio deleted: %s → %s", public_id, result.get("result"))
        return result.get("result") == "ok"
    except Exception as exc:
        logger.error("Cloudinary audio delete failed: %s", exc)
        return False
