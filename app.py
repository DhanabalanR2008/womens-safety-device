import functools
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from config import Config
from database import create_event, delete_event, get_all_events, init_db
from services.whatsapp import send_whatsapp_alert
from services.cloudinary_storage import upload_photo, upload_audio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("safety_app")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists (used for local mode)
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize database schema
init_db()


def login_required(view):
    """Decorator to require login for dashboard views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.url))
        return view(**kwargs)
    return wrapped_view


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Checks if a filename has an allowed extension."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions


def verify_device_token() -> bool:
    """Validates device upload token from request headers."""
    expected_token = Config.DEVICE_UPLOAD_TOKEN
    if not expected_token:
        return False

    token = request.headers.get("X-Device-Token")
    if token and token.strip() == expected_token:
        return True

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token == expected_token:
            return True

    token_param = request.form.get("token")
    if token_param and token_param.strip() == expected_token:
        return True

    return False


# ==============================================================================
# Web Dashboard Routes
# ==============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == Config.DASHBOARD_USERNAME and password == Config.DASHBOARD_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            flash("Welcome back! Successfully logged into the Safety Dashboard.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    events = get_all_events()
    whatsapp_active = Config.is_whatsapp_configured()
    cloudinary_active = Config.is_cloudinary_configured()
    return render_template(
        "dashboard.html",
        events=events,
        whatsapp_active=whatsapp_active,
        cloudinary_active=cloudinary_active,
        whatsapp_recipient=Config.WHATSAPP_RECIPIENT_PHONE_NUMBER if whatsapp_active else None,
    )


@app.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event_route(event_id: int):
    success = delete_event(event_id, Config.UPLOAD_FOLDER)
    if success:
        flash(f"Emergency Alert #{event_id} and all associated media have been permanently deleted.", "success")
    else:
        flash(f"Alert #{event_id} could not be found or was already deleted.", "warning")
    return redirect(url_for("dashboard"))


@app.route("/uploads/<path:filename>")
def serve_upload(filename: str):
    """Serve local uploads only — Cloudinary files use their own HTTPS URLs."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized: Login required"}), 401
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


# ==============================================================================
# ESP32 Upload API
# ==============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "Women's Safety Device Gateway",
        "server_time": datetime.now(timezone.utc).isoformat(),
        "storage": "cloudinary" if Config.is_cloudinary_configured() else "local",
        "whatsapp_configured": Config.is_whatsapp_configured(),
        "cloudinary_configured": Config.is_cloudinary_configured(),
    }), 200


@app.route("/api/events", methods=["POST"])
def upload_event():
    """
    ESP32-CAM Upload Endpoint.
    
    Accepts multipart/form-data:
      - photos: 1–4 JPG/JPEG files (repeat the field per photo)
      - audio:  optional WAV file
      - device_id: optional text
    
    Headers:
      X-Device-Token: <token>   OR   Authorization: Bearer <token>
    """
    # 1. Authenticate
    if not verify_device_token():
        logger.warning("Rejected upload: invalid/missing token from %s", request.remote_addr)
        return jsonify({
            "status": "error",
            "error": "Unauthorized: Pass header 'X-Device-Token: <token>' or 'Authorization: Bearer <token>'."
        }), 401

    # 2. Device ID
    device_id = request.form.get("device_id", "ESP32-CAM").strip() or "ESP32-CAM"

    # 3. Validate Photos
    uploaded_photos = request.files.getlist("photos")
    valid_photo_files = [p for p in uploaded_photos if p and p.filename and p.filename.strip()]

    if not valid_photo_files:
        return jsonify({
            "status": "error",
            "error": "Missing photos: At least 1 JPG/JPEG photo is required in the 'photos' field."
        }), 400

    if len(valid_photo_files) > 4:
        return jsonify({
            "status": "error",
            "error": f"Too many photos: Received {len(valid_photo_files)}, maximum is 4."
        }), 400

    for photo in valid_photo_files:
        if not allowed_file(photo.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({
                "status": "error",
                "error": f"Invalid photo format: '{photo.filename}'. Only JPG/JPEG accepted."
            }), 400

    # 4. Validate Audio
    uploaded_audio = request.files.get("audio")
    valid_audio_file = None
    if uploaded_audio and uploaded_audio.filename and uploaded_audio.filename.strip():
        if not allowed_file(uploaded_audio.filename, Config.ALLOWED_AUDIO_EXTENSIONS):
            return jsonify({
                "status": "error",
                "error": f"Invalid audio format: '{uploaded_audio.filename}'. Only WAV accepted."
            }), 400
        valid_audio_file = uploaded_audio

    # 5. Generate unique prefix for all files in this event
    timestamp_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = uuid.uuid4().hex[:6]
    event_folder = f"{timestamp_prefix}_{random_suffix}"

    # 6. Save Photos (Cloudinary or Local)
    use_cloudinary = Config.is_cloudinary_configured()
    storage_backend = "cloudinary" if use_cloudinary else "local"

    saved_photo_filenames: List[str] = []
    photo_urls: List[Optional[str]] = []
    photo_public_ids: List[Optional[str]] = []

    for idx, photo in enumerate(valid_photo_files, start=1):
        clean_name = secure_filename(photo.filename) or f"photo_{idx}.jpg"
        save_name = f"{event_folder}_p{idx}_{clean_name}"
        photo_bytes = photo.read()

        if use_cloudinary:
            result = upload_photo(photo_bytes, save_name, event_folder)
            if result:
                saved_photo_filenames.append(save_name)
                photo_urls.append(result["url"])
                photo_public_ids.append(result["public_id"])
                logger.info("Photo %d → Cloudinary: %s", idx, result["url"])
            else:
                # Cloudinary upload failed — fall back to local for this file
                logger.warning("Cloudinary failed for photo %d, saving locally", idx)
                local_path = Config.UPLOAD_FOLDER / save_name
                local_path.write_bytes(photo_bytes)
                saved_photo_filenames.append(save_name)
                photo_urls.append(None)
                photo_public_ids.append(None)
                storage_backend = "local"
        else:
            local_path = Config.UPLOAD_FOLDER / save_name
            local_path.write_bytes(photo_bytes)
            saved_photo_filenames.append(save_name)
            photo_urls.append(None)
            photo_public_ids.append(None)

    # 7. Save Audio (Cloudinary or Local)
    saved_audio_filename: Optional[str] = None
    audio_url: Optional[str] = None
    audio_public_id: Optional[str] = None

    if valid_audio_file:
        clean_audio_name = secure_filename(valid_audio_file.filename) or "audio.wav"
        audio_save_name = f"{event_folder}_audio_{clean_audio_name}"
        audio_bytes = valid_audio_file.read()

        if use_cloudinary:
            result = upload_audio(audio_bytes, audio_save_name, event_folder)
            if result:
                saved_audio_filename = audio_save_name
                audio_url = result["url"]
                audio_public_id = result["public_id"]
                logger.info("Audio → Cloudinary: %s", audio_url)
            else:
                logger.warning("Cloudinary failed for audio, saving locally")
                local_path = Config.UPLOAD_FOLDER / audio_save_name
                local_path.write_bytes(audio_bytes)
                saved_audio_filename = audio_save_name
        else:
            local_path = Config.UPLOAD_FOLDER / audio_save_name
            local_path.write_bytes(audio_bytes)
            saved_audio_filename = audio_save_name

    logger.info(
        "Event from %s (%s): %d photos, audio=%s, backend=%s",
        device_id, request.remote_addr,
        len(saved_photo_filenames), bool(saved_audio_filename), storage_backend
    )

    # 8. Optional WhatsApp notification
    whatsapp_res = send_whatsapp_alert(
        event_id=0,
        device_id=device_id,
        photo_count=len(saved_photo_filenames),
        has_audio=bool(saved_audio_filename)
    )

    # 9. Save to database
    event = create_event(
        device_id=device_id,
        photo_filenames=saved_photo_filenames,
        photo_urls=photo_urls,
        photo_public_ids=photo_public_ids,
        audio_filename=saved_audio_filename,
        audio_url=audio_url,
        audio_public_id=audio_public_id,
        whatsapp_status=whatsapp_res["status"],
        whatsapp_detail=whatsapp_res["detail"],
        storage_backend=storage_backend,
    )

    # 10. Return success response
    return jsonify({
        "status": "success",
        "message": "Emergency alert recorded successfully",
        "event_id": event["id"],
        "device_id": event["device_id"],
        "created_at": event["created_at"],
        "photos_received": len(saved_photo_filenames),
        "photos": saved_photo_filenames,
        "photo_urls": [u for u in photo_urls if u],
        "audio": saved_audio_filename,
        "audio_url": audio_url,
        "storage": storage_backend,
        "gps": {
            "available": False,
            "status": "Not fitted / Not included in this hardware prototype"
        },
        "whatsapp_status": event["whatsapp_status"],
        "whatsapp_detail": event["whatsapp_detail"],
    }), 201


@app.errorhandler(413)
def request_entity_too_large(error):
    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "error": "Payload too large: Combined file size exceeds 25 MB limit."
        }), 413
    flash("The uploaded files exceeded the 25 MB size limit.", "danger")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "error": "Endpoint not found"}), 404
    return render_template("404.html"), 404


@app.template_filter("format_datetime")
def format_datetime_filter(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %Y • %I:%M:%S %p UTC")
    except Exception:
        return iso_str


if __name__ == "__main__":
    logger.info(
        "Starting Women's Safety Device Server on %s:%d (storage: %s)",
        Config.FLASK_HOST, Config.FLASK_PORT,
        "cloudinary" if Config.is_cloudinary_configured() else "local"
    )
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=True)
