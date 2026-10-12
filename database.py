import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import Config

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """Creates a database connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initializes the SQLite database tables and runs safe migrations."""
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL DEFAULT 'ESP32-CAM',
                    created_at TEXT NOT NULL,
                    audio_filename TEXT,
                    audio_url TEXT,
                    audio_public_id TEXT,
                    whatsapp_status TEXT DEFAULT 'not_configured',
                    whatsapp_detail TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    storage_backend TEXT DEFAULT 'local'
                );

                CREATE TABLE IF NOT EXISTS event_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_url TEXT,
                    public_id TEXT,
                    uploaded_at TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
                );
            """)

        # Safe migration: add new columns if they don't exist yet (for existing databases)
        _migrate_add_column(conn, "events", "audio_url", "TEXT")
        _migrate_add_column(conn, "events", "audio_public_id", "TEXT")
        _migrate_add_column(conn, "events", "storage_backend", "TEXT DEFAULT 'local'")
        _migrate_add_column(conn, "event_photos", "file_url", "TEXT")
        _migrate_add_column(conn, "event_photos", "public_id", "TEXT")
    finally:
        conn.close()


def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    """Adds a column to a table if it doesn't already exist (safe migration)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
        logger.info("DB migration: added column %s.%s", table, column)
    except sqlite3.OperationalError:
        pass  # Column already exists — this is expected


def create_event(
    device_id: str,
    photo_filenames: List[str],
    photo_urls: Optional[List[str]] = None,
    photo_public_ids: Optional[List[str]] = None,
    audio_filename: Optional[str] = None,
    audio_url: Optional[str] = None,
    audio_public_id: Optional[str] = None,
    whatsapp_status: str = "not_configured",
    whatsapp_detail: str = "",
    notes: str = "",
    storage_backend: str = "local",
) -> Dict[str, Any]:
    """Inserts an emergency alert event and associated photo records."""
    now_iso = datetime.now(timezone.utc).isoformat()

    if photo_urls is None:
        photo_urls = [None] * len(photo_filenames)
    if photo_public_ids is None:
        photo_public_ids = [None] * len(photo_filenames)

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events
                  (device_id, created_at, audio_filename, audio_url, audio_public_id,
                   whatsapp_status, whatsapp_detail, notes, storage_backend)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (device_id, now_iso, audio_filename, audio_url, audio_public_id,
                 whatsapp_status, whatsapp_detail, notes, storage_backend)
            )
            event_id = cursor.lastrowid

            for filename, url, pid in zip(photo_filenames, photo_urls, photo_public_ids):
                cursor.execute(
                    """
                    INSERT INTO event_photos (event_id, filename, file_url, public_id, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (event_id, filename, url, pid, now_iso)
                )

        return {
            "id": event_id,
            "device_id": device_id,
            "created_at": now_iso,
            "photos": photo_filenames,
            "photo_urls": photo_urls,
            "audio": audio_filename,
            "audio_url": audio_url,
            "whatsapp_status": whatsapp_status,
            "whatsapp_detail": whatsapp_detail,
            "storage_backend": storage_backend,
        }
    finally:
        conn.close()


def get_all_events() -> List[Dict[str, Any]]:
    """Returns all events ordered newest first, with their photos attached."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY id DESC")
        event_rows = cursor.fetchall()

        events = []
        for row in event_rows:
            event = dict(row)
            cursor.execute(
                "SELECT filename, file_url, public_id FROM event_photos WHERE event_id = ? ORDER BY id ASC",
                (event["id"],)
            )
            photo_rows = cursor.fetchall()
            event["photos"] = [dict(p) for p in photo_rows]
            events.append(event)

        return events
    finally:
        conn.close()


def get_event_by_id(event_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single event with its photos."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            return None

        event = dict(row)
        cursor.execute(
            "SELECT filename, file_url, public_id FROM event_photos WHERE event_id = ? ORDER BY id ASC",
            (event_id,)
        )
        photo_rows = cursor.fetchall()
        event["photos"] = [dict(p) for p in photo_rows]
        return event
    finally:
        conn.close()


def delete_event(event_id: int, upload_folder: Optional[Path] = None) -> bool:
    """
    Deletes an event and its media.
    - If Cloudinary is configured: deletes from Cloudinary.
    - If local: deletes physical files from disk.
    - Always removes database records.
    """
    if upload_folder is None:
        upload_folder = Config.UPLOAD_FOLDER

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get event details for cleanup
        cursor.execute(
            "SELECT audio_filename, audio_url, audio_public_id, storage_backend FROM events WHERE id = ?",
            (event_id,)
        )
        event_row = cursor.fetchone()
        if not event_row:
            return False

        event_data = dict(event_row)

        cursor.execute(
            "SELECT filename, file_url, public_id FROM event_photos WHERE event_id = ?",
            (event_id,)
        )
        photo_rows = [dict(r) for r in cursor.fetchall()]

        # Delete from database first (CASCADE handles event_photos)
        with conn:
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))

        # Delete media files
        if event_data.get("storage_backend") == "cloudinary":
            _delete_from_cloudinary(photo_rows, event_data)
        else:
            _delete_from_local(photo_rows, event_data, upload_folder)

        return True
    finally:
        conn.close()


def _delete_from_cloudinary(photo_rows: list, event_data: dict):
    """Removes files from Cloudinary."""
    from services.cloudinary_storage import delete_photo, delete_audio

    for photo in photo_rows:
        if photo.get("public_id"):
            delete_photo(photo["public_id"])

    if event_data.get("audio_public_id"):
        delete_audio(event_data["audio_public_id"])


def _delete_from_local(photo_rows: list, event_data: dict, upload_folder: Path):
    """Removes files from local disk."""
    for photo in photo_rows:
        fname = photo.get("filename")
        if fname:
            fpath = upload_folder / fname
            if fpath.exists() and fpath.is_file():
                try:
                    fpath.unlink()
                except OSError as e:
                    logger.warning("Could not delete local file %s: %s", fpath, e)

    audio_fname = event_data.get("audio_filename")
    if audio_fname:
        apath = upload_folder / audio_fname
        if apath.exists() and apath.is_file():
            try:
                apath.unlink()
            except OSError as e:
                logger.warning("Could not delete local audio %s: %s", apath, e)
