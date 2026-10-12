import io
import unittest
from pathlib import Path
from app import app
from database import get_all_events, init_db
from config import Config
from test_upload import generate_sample_jpeg, generate_sample_wav

class TestWomensSafetyApp(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Use temporary test database
        Config.DATABASE_PATH = Config.BASE_DIR / "test_safety_alerts.db"
        init_db()

    def tearDown(self):
        # Clean up test database
        if Config.DATABASE_PATH.exists():
            Config.DATABASE_PATH.unlink()
        # Clean up any test uploads
        for f in Config.UPLOAD_FOLDER.glob("*"):
            if f.is_file() and f.name != ".gitkeep":
                try:
                    f.unlink()
                except OSError:
                    pass

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "online")
        self.assertIn("whatsapp_configured", data)

    def test_upload_missing_token(self):
        # Missing token must return 401
        res = self.client.post("/api/events")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_upload_invalid_token(self):
        # Invalid token must return 401
        res = self.client.post(
            "/api/events",
            headers={"X-Device-Token": "wrong-token-abc"}
        )
        self.assertEqual(res.status_code, 401)

    def test_upload_missing_photos(self):
        # Valid token but no photos attached must return 400
        res = self.client.post(
            "/api/events",
            headers={"X-Device-Token": Config.DEVICE_UPLOAD_TOKEN},
            data={"device_id": "TEST-CAM"}
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Missing photos", data["error"])

    def test_upload_invalid_photo_extension(self):
        # Text file uploaded as photo must return 400
        res = self.client.post(
            "/api/events",
            headers={"X-Device-Token": Config.DEVICE_UPLOAD_TOKEN},
            data={
                "photos": (io.BytesIO(b"fake text"), "bad_photo.txt")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Invalid photo format", data["error"])

    def test_upload_too_many_photos(self):
        # 11 photos (max is 10) must return 400
        photos = [
            (io.BytesIO(generate_sample_jpeg(i)), f"photo_{i}.jpg")
            for i in range(1, 12)
        ]
        data = {"photos": photos}
        res = self.client.post(
            "/api/events",
            headers={"X-Device-Token": Config.DEVICE_UPLOAD_TOKEN},
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Too many photos", data["error"])

    def test_successful_event_upload(self):
        # 3 photos + 1 audio file
        photos = [
            (io.BytesIO(generate_sample_jpeg(1)), "p1.jpg"),
            (io.BytesIO(generate_sample_jpeg(2)), "p2.jpeg"),
            (io.BytesIO(generate_sample_jpeg(3)), "p3.jpg"),
        ]
        audio = (io.BytesIO(generate_sample_wav(1.0)), "mic.wav")

        res = self.client.post(
            "/api/events",
            headers={"X-Device-Token": Config.DEVICE_UPLOAD_TOKEN},
            data={
                "device_id": "ESP32-CAM-UNIT-01",
                "photos": photos,
                "audio": audio
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["device_id"], "ESP32-CAM-UNIT-01")
        self.assertEqual(data["photos_received"], 3)
        self.assertIsNotNone(data["audio"])
        self.assertFalse(data["gps"]["available"])

        event_id = data["event_id"]

        # Check DB
        events = get_all_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], event_id)
        self.assertEqual(len(events[0]["photos"]), 3)

        # Login to dashboard
        login_res = self.client.post(
            "/login",
            data={
                "username": Config.DASHBOARD_USERNAME,
                "password": Config.DASHBOARD_PASSWORD
            },
            follow_redirects=True
        )
        self.assertEqual(login_res.status_code, 200)
        html = login_res.get_data(as_text=True)
        self.assertIn("ALERT #1", html)
        self.assertIn("ESP32-CAM-UNIT-01", html)
        self.assertIn("GPS: Not Included / Unavailable", html)

        # Verify photo url or local serving
        photo_entry = events[0]["photos"][0]
        if isinstance(photo_entry, dict) and photo_entry.get("file_url"):
            # Cloudinary mode: verify HTTPS URL is present
            self.assertTrue(photo_entry["file_url"].startswith("https://"))
        else:
            # Local disk mode
            photo_filename = photo_entry["filename"] if isinstance(photo_entry, dict) else photo_entry
            photo_res = self.client.get(f"/uploads/{photo_filename}")
            self.assertEqual(photo_res.status_code, 200)
            photo_res.close()

        # Delete event
        del_res = self.client.post(f"/events/{event_id}/delete", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        del_html = del_res.get_data(as_text=True)
        self.assertIn("No alerts yet", del_html)

if __name__ == "__main__":
    unittest.main()
