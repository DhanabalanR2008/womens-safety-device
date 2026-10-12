"""
==============================================================================
Test Upload Utility - Women's Safety Device Prototype
==============================================================================
This beginner-friendly script generates sample JPG photos and a sample WAV
audio file, then simulates an ESP32-CAM sending a multipart POST request
to the Flask upload API (POST /api/events).

Usage:
    python test_upload.py
"""

import io
import math
import os
import struct
import sys
import wave
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load local .env if available
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SERVER_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
API_ENDPOINT = f"{SERVER_URL}/api/events"
DEVICE_TOKEN = os.environ.get("DEVICE_UPLOAD_TOKEN", "esp32-safety-device-secret-token-xyz987")
DEVICE_ID = "ESP32-CAM-SIMULATOR"


def generate_sample_wav(duration_seconds: float = 3.0, sample_rate: int = 16000) -> bytes:
    """
    Generates a valid mono 16-bit PCM WAV audio file in memory
    using Python's standard library (wave & struct).
    Produces an alternating dual-tone emergency beep sound.
    """
    num_samples = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)       # Mono (like INMP441 I2S mic)
        wav_file.setsampwidth(2)      # 16-bit samples
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            # Alternate tone every 0.5s between 600Hz and 900Hz
            freq = 900.0 if (i // (sample_rate // 2)) % 2 == 0 else 600.0
            # Generate sine wave with gentle amplitude (0.3 of full scale)
            sample_val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            frames.extend(struct.pack("<h", sample_val))

        wav_file.writeframes(frames)

    return buffer.getvalue()


def generate_sample_jpeg(image_number: int) -> bytes:
    """
    Generates a simulated camera JPEG image.
    Uses PIL (Pillow) if installed to render a camera frame;
    otherwise falls back to a valid JPEG byte stream.
    """
    try:
        from PIL import Image, ImageDraw

        # Create a 640x480 image (VGA resolution commonly used by ESP32-CAM)
        colors = [(26, 32, 44), (45, 55, 72), (74, 85, 104)]
        bg_color = colors[(image_number - 1) % len(colors)]
        
        img = Image.new("RGB", (640, 480), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw camera viewfinder border
        draw.rectangle([20, 20, 620, 460], outline=(225, 29, 72), width=3)
        # Crosshair in center
        draw.line([300, 240, 340, 240], fill=(255, 255, 255), width=2)
        draw.line([320, 220, 320, 260], fill=(255, 255, 255), width=2)

        # Text banner
        banner_text = f"SIMULATED ESP32-CAM CAPTURE - FRAME #{image_number}"
        draw.text((40, 40), banner_text, fill=(255, 255, 255))
        draw.text((40, 70), "Prototype Women's Safety Device (No GPS)", fill=(245, 158, 11))
        draw.text((40, 420), f"Timestamp: Sample Frame {image_number}", fill=(203, 213, 225))

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="JPEG", quality=85)
        return out_buffer.getvalue()

    except ImportError:
        # Fallback minimal valid JPEG (1x1 pixel) if Pillow is not available
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xBF, 0x80, 0xFF, 0xD9
        ])


def run_test_upload():
    print("=" * 70)
    print(" Women's Safety Device Prototype - Test Upload Simulation")
    print("=" * 70)
    print(f"Target Server URL:  {SERVER_URL}")
    print(f"Upload Endpoint:    {API_ENDPOINT}")
    print(f"Device ID:          {DEVICE_ID}")
    print(f"Using Token:        {DEVICE_TOKEN[:8]}... (from .env)")
    print("-" * 70)

    # 1. Check server health first
    health_url = f"{SERVER_URL}/api/health"
    try:
        print(f"Checking server availability at {health_url}...")
        resp = requests.get(health_url, timeout=3)
        if resp.status_code == 200:
            print("Server is ONLINE and responding!")
        else:
            print(f"Warning: Health check returned HTTP {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Could not connect to the Flask server at {SERVER_URL}.")
        print("Please ensure the Flask app is running in another terminal:")
        print("  python app.py\n")
        sys.exit(1)

    # 2. Synthesize test files
    print("\nGenerating sample files in memory:")
    print("  - Generating 3 simulated camera photos (JPG)...")
    photo1_bytes = generate_sample_jpeg(1)
    photo2_bytes = generate_sample_jpeg(2)
    photo3_bytes = generate_sample_jpeg(3)

    print("  - Generating 3-second audio recording (WAV)...")
    audio_bytes = generate_sample_wav(duration_seconds=3.0)

    # 3. Assemble multipart/form-data payload
    # Note: requests supports multiple files with the same key 'photos' via a list of tuples
    files = [
        ("photos", ("cam_burst_01.jpg", photo1_bytes, "image/jpeg")),
        ("photos", ("cam_burst_02.jpg", photo2_bytes, "image/jpeg")),
        ("photos", ("cam_burst_03.jpg", photo3_bytes, "image/jpeg")),
        ("audio", ("inmp441_audio.wav", audio_bytes, "audio/wav")),
    ]

    data = {
        "device_id": DEVICE_ID
    }

    headers = {
        "X-Device-Token": DEVICE_TOKEN
    }

    print("\nSending multipart/form-data POST request to /api/events...")
    try:
        upload_resp = requests.post(
            API_ENDPOINT,
            headers=headers,
            data=data,
            files=files,
            timeout=15
        )

        print(f"\nResponse HTTP Status: {upload_resp.status_code}")
        print("Response Body (JSON):")
        try:
            res_json = upload_resp.json()
            import json
            print(json.dumps(res_json, indent=2))
        except Exception:
            print(upload_resp.text)

        if upload_resp.status_code in (200, 201):
            print("\n" + "=" * 70)
            print(" SUCCESS! Simulated emergency alert recorded.")
            print(f" Now open your browser to view it on the dashboard:")
            print(f"   {SERVER_URL}")
            print("=" * 70)
        else:
            print("\n[!] Upload failed. Check the error message in the response above.")

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_test_upload()
