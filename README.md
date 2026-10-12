# 🛡️ Women's Safety Device Prototype - Server & Dashboard

A lightweight, secure Python Flask backend and mobile-friendly responsive dashboard built for an ESP32-CAM and INMP441 microphone emergency safety device prototype.

When an emergency pushbutton is pressed, the ESP32 captures 3–4 JPG photos and a 5-second WAV audio recording, then securely uploads them via Wi-Fi to this server. Parents and guardians can immediately view the alert, inspect photos in a lightbox, listen to the audio stream, or receive instant Meta WhatsApp notifications.

---

## 📌 Features

- **Responsive Web Dashboard**: Works on desktop monitors and mobile phone browsers (e.g., parent's smartphone).
- **Grouped Alerts Feed**: Displays events newest first, grouping burst photos and audio together with timestamps.
- **Microphone Playback**: In-browser audio player for recorded INMP441 WAV clips.
- **Lightbox Photo Viewer**: High-contrast, touch-friendly image preview.
- **Strict Location Accuracy**: Clearly states that **GPS is unavailable / not included in this hardware prototype**. No fake or hallucinated locations.
- **Alert Deletion**: Permanent one-click deletion of database records and uploaded media files from disk.
- **Secure Token Upload API**: Requires a shared secret token via HTTP headers (`X-Device-Token` or `Authorization: Bearer <token>`).
- **Dashboard Authentication**: Session-based login protecting alert history and media files.
- **Official Meta WhatsApp Cloud API**: Optional instant alerts sent to parents; if credentials are not configured, the app runs normally without errors or mock simulations.
- **Ready-to-Use Simulation Script**: `test_upload.py` tests the upload endpoint with synthetic JPG and WAV data without needing the hardware plugged in.

---

## 🗂️ Project Structure

```text
womens-safety-device/
├── app.py                 # Flask server, dashboard routes, and ESP32 upload API
├── config.py              # Environment configuration & validation
├── database.py            # SQLite database schema, CRUD, and file deletion
├── services/
│   ├── __init__.py
│   └── whatsapp.py        # Official Meta WhatsApp Cloud API integration
├── static/
│   ├── css/
│   │   └── style.css      # Responsive styles (desktop & smartphone)
│   └── js/
│       └── main.js        # Lightbox, audio controller, delete modal
├── templates/
│   ├── base.html          # Base layout with navigation and flash alerts
│   ├── login.html         # Responsive dashboard login page
│   ├── dashboard.html     # Real-time alert feed & media player
│   └── 404.html           # Page not found error page
├── uploads/               # Local folder where uploaded JPGs & WAVs are saved
│   └── .gitkeep
├── .env.example           # Example configuration template (no secrets)
├── .env                   # Local settings & secrets
├── .gitignore             # Protects uploads, database, and .env
├── requirements.txt       # Python package dependencies
├── test_upload.py         # Test script simulating an ESP32 upload
└── test_app.py            # Automated unit test suite
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

Follow these exact steps in **Windows PowerShell** to install and run the server.

### 1. Open Windows PowerShell and navigate to the project directory

```powershell
cd C:\Users\dell\.gemini\antigravity\scratch\womens-safety-device
```

### 2. Create and activate a Python virtual environment (Recommended)

```powershell
# Create virtual environment
py -m venv venv

# If PowerShell blocks script execution, run:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

*(If you don't use a virtual environment, you can directly use `py` or `python`)*.

### 3. Install required packages

```powershell
py -m pip install -r requirements.txt
```

### 4. Review your `.env` configuration file

The repository includes a ready-to-use `.env` file (copied from `.env.example`). You can inspect or edit it in Notepad:

```powershell
notepad .env
```

Default credentials in `.env`:
- **Dashboard Username**: `admin`
- **Dashboard Password**: `admin123`
- **Device Upload Token**: `esp32-safety-device-secret-token-xyz987`
- **Port**: `5000`

> ⚠️ **Important**: Change `DASHBOARD_PASSWORD` and `DEVICE_UPLOAD_TOKEN` to your own strong passwords before sharing or deploying.

### 5. Start the Flask Server

```powershell
py app.py
```

You will see output similar to:
```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://<YOUR-LOCAL-IP>:5000
```

### 6. Open the Dashboard in your browser

- On your computer: Open [http://localhost:5000](http://localhost:5000)
- Sign in with username: `admin` and password: `admin123` (or your updated credentials).

---

## 🧪 Testing the Upload API Without Hardware

To verify that the server receives files, creates database entries, and displays them on the dashboard without needing your ESP32 connected:

1. Keep the Flask server running in your first PowerShell window.
2. Open a **second** Windows PowerShell window and run:

```powershell
cd C:\Users\dell\.gemini\antigravity\scratch\womens-safety-device
py test_upload.py
```

`test_upload.py` will:
1. Ping `GET /api/health` to confirm the server is running.
2. Generate 3 mock camera burst photos (JPG) and a 3-second audio recording (WAV) in memory.
3. Post the files to `POST /api/events` with the authentication token.
4. Print the server's HTTP 201 response JSON.
5. Refresh your browser at [http://localhost:5000](http://localhost:5000) — the alert will appear immediately with photos and an audio player!

---

## 📡 Connecting the ESP32 to the Flask Server

### Step A: Connect both devices to the same Wi-Fi / Hotspot
Your computer running the Flask server and the ESP32-CAM must be connected to the **same local Wi-Fi router** or **mobile hotspot** (e.g., your smartphone's hotspot).

### Step B: Find your Computer's Local IP Address
In Windows PowerShell, run:

```powershell
ipconfig
```

Look for your active network adapter (e.g. `Wireless LAN adapter Wi-Fi`):
- Find **`IPv4 Address`** (for example: `192.168.1.45` or `192.168.43.120`).

Your ESP32 will send uploads to:
```text
http://192.168.1.45:5000/api/events
```

### Step C: Allow Flask through Windows Firewall
When Flask starts for the first time, Windows may show a firewall popup. Click **"Allow access" on Private Networks**.
If the ESP32 cannot connect, run this one-time command in an **Administrator PowerShell** to allow port 5000:

```powershell
New-NetFirewallRule -DisplayName "Flask Safety Server Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Step D: Open the Dashboard on a Parent's Phone
Any phone connected to the same Wi-Fi can open the dashboard by browsing to:
```text
http://<YOUR-COMPUTER-IP>:5000
```
(e.g., `http://192.168.1.45:5000`).

---

## 🌐 Security Warning: Local Network vs. Internet Deployment

> ⚠️ **DO NOT open router ports (Port Forwarding) to the public internet.**
> 
> Simply opening port 5000 in your home Wi-Fi router's settings is dangerous because:
> 1. It exposes your computer directly to automated internet bots, port scanners, and malicious traffic.
> 2. Local HTTP traffic is unencrypted in transit.
>
> **For real-world outside-the-home use:**
> Deploy this Flask app to a secure cloud hosting provider with automatic HTTPS (SSL/TLS certificates), such as:
> - **Render** (render.com)
> - **Railway** (railway.app)
> - **DigitalOcean App Platform** or a Linux VPS behind an Nginx reverse proxy with Let's Encrypt SSL.
> 
> On secure cloud hosting, your endpoint will be `https://your-safety-app.onrender.com/api/events`, which is encrypted and safe for mobile parent access anywhere in the world.

---

## 📑 ESP32 Upload API Specification

### Endpoint Details
- **Method**: `POST`
- **URL**: `http://<SERVER-IP>:5000/api/events`
- **Content-Type**: `multipart/form-data; boundary=...`
- **Required Header**:
  - `X-Device-Token: <your-token>`  
    *(or `Authorization: Bearer <your-token>`)*

### Form Fields (`multipart/form-data`)
| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `photos` | File (JPG/JPEG) | **Yes** | 1 to 4 JPG photos. Repeat the `photos` field name for each photo in the burst. |
| `audio` | File (WAV) | Optional | 5-second 16-bit PCM WAV audio clip from INMP441. |
| `device_id` | Text | Optional | Identifying string (e.g. `ESP32-CAM-01`). Defaults to `ESP32-CAM`. |

### Success Response (`201 Created`)
```json
{
  "status": "success",
  "message": "Emergency alert recorded successfully",
  "event_id": 1,
  "device_id": "ESP32-CAM-01",
  "created_at": "2026-10-10T15:15:21.015774+00:00",
  "photos_received": 3,
  "photos": [
    "20261010_151521_c960df_p1_cam_burst_01.jpg",
    "20261010_151521_c960df_p2_cam_burst_02.jpg",
    "20261010_151521_c960df_p3_cam_burst_03.jpg"
  ],
  "audio": "20261010_151521_c960df_audio_inmp441_audio.wav",
  "gps": {
    "available": false,
    "status": "Not fitted / Not included in this hardware prototype"
  },
  "whatsapp_status": "not_configured",
  "whatsapp_detail": "WhatsApp alerts not configured (WHATSAPP_TOKEN / PHONE_NUMBER_ID / RECIPIENT missing in .env)"
}
```

### Error Responses
- **`401 Unauthorized`**: Token missing or invalid:
  ```json
  {"status": "error", "error": "Unauthorized: Invalid or missing device token."}
  ```
- **`400 Bad Request`**: Missing photos, more than 4 photos, or invalid file extensions:
  ```json
  {"status": "error", "error": "Missing photos: At least 1 JPG/JPEG photo is required in the 'photos' field."}
  ```
- **`413 Payload Too Large`**: Files exceed the 25 MB safety limit.

---

## 💻 Arduino C++ Code Reference for ESP32

Here is how your ESP32-CAM builds the `multipart/form-data` request with `WiFiClient` to stream photos and audio over Wi-Fi:

```cpp
#include <WiFi.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server IP (Your PC IP from ipconfig) and Port
const char* serverHost = "192.168.1.45"; 
const int serverPort = 5000;
const char* uploadPath = "/api/events";
const char* deviceToken = "esp32-safety-device-secret-token-xyz987";

void uploadAlert(uint8_t* photo1_buf, size_t photo1_len,
                 uint8_t* photo2_buf, size_t photo2_len,
                 uint8_t* photo3_buf, size_t photo3_len,
                 uint8_t* wav_buf, size_t wav_len) {
  
  WiFiClient client;
  if (!client.connect(serverHost, serverPort)) {
    Serial.println("Connection to server failed!");
    return;
  }

  String boundary = "----ESP32CamBoundary123456789";

  // Build field headers
  String headDeviceId = "--" + boundary + "\r\n" +
                        "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n" +
                        "ESP32-CAM-UNIT-01\r\n";

  String headPhoto1 = "--" + boundary + "\r\n" +
                      "Content-Disposition: form-data; name=\"photos\"; filename=\"burst1.jpg\"\r\n" +
                      "Content-Type: image/jpeg\r\n\r\n";

  String headPhoto2 = "--" + boundary + "\r\n" +
                      "Content-Disposition: form-data; name=\"photos\"; filename=\"burst2.jpg\"\r\n" +
                      "Content-Type: image/jpeg\r\n\r\n";

  String headPhoto3 = "--" + boundary + "\r\n" +
                      "Content-Disposition: form-data; name=\"photos\"; filename=\"burst3.jpg\"\r\n" +
                      "Content-Type: image/jpeg\r\n\r\n";

  String headAudio  = "--" + boundary + "\r\n" +
                      "Content-Disposition: form-data; name=\"audio\"; filename=\"mic.wav\"\r\n" +
                      "Content-Type: audio/wav\r\n\r\n";

  String tail = "\r\n--" + boundary + "--\r\n";

  // Calculate total Content-Length
  size_t totalLen = headDeviceId.length() +
                    headPhoto1.length() + photo1_len + 2 +
                    headPhoto2.length() + photo2_len + 2 +
                    headPhoto3.length() + photo3_len + 2 +
                    headAudio.length()  + wav_len + 2 +
                    tail.length();

  // Send HTTP POST headers
  client.printf("POST %s HTTP/1.1\r\n", uploadPath);
  client.printf("Host: %s:%d\r\n", serverHost, serverPort);
  client.printf("X-Device-Token: %s\r\n", deviceToken);
  client.printf("Content-Type: multipart/form-data; boundary=%s\r\n", boundary.c_str());
  client.printf("Content-Length: %u\r\n", totalLen);
  client.print("Connection: close\r\n\r\n");

  // Stream device ID
  client.print(headDeviceId);

  // Stream Photo 1
  client.print(headPhoto1);
  client.write(photo1_buf, photo1_len);
  client.print("\r\n");

  // Stream Photo 2
  client.print(headPhoto2);
  client.write(photo2_buf, photo2_len);
  client.print("\r\n");

  // Stream Photo 3
  client.print(headPhoto3);
  client.write(photo3_buf, photo3_len);
  client.print("\r\n");

  // Stream Audio
  client.print(headAudio);
  client.write(wav_buf, wav_len);
  client.print("\r\n");

  // Send terminating boundary
  client.print(tail);

  // Read response
  while (client.connected() || client.available()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      Serial.println(line);
    }
  }
  client.stop();
  Serial.println("Upload completed!");
}
```

---

## 💬 WhatsApp Business Cloud API Integration (Optional)

This project uses **only the official Meta WhatsApp Business Cloud API**. It never automates WhatsApp Web and never simulates delivery.

If you don't need WhatsApp alerts right now, leave the WhatsApp variables in `.env` blank. The app will work normally and display `WhatsApp: Not Configured`.

### To activate real WhatsApp alerts:
1. Go to the [Meta for Developers Portal](https://developers.facebook.com/) and create a free App under **Business** with the **WhatsApp** product.
2. In the WhatsApp API Setup panel:
   - Copy your **Temporary Access Token** or create a **System User Token**.
   - Copy your **Phone Number ID**.
   - Add your parent's/guardian's phone number as a test recipient.
3. Open your `.env` file and fill in:
   ```env
   WHATSAPP_TOKEN=EAAG...your_meta_token_here...
   WHATSAPP_PHONE_NUMBER_ID=123456789012345
   WHATSAPP_RECIPIENT_PHONE_NUMBER=15551234567
   ```
   *(Recipient phone number format: country code without `+` or spaces, e.g., `919876543210` for India, `15551234567` for US).*
4. Restart Flask (`py app.py`).
5. When an alert arrives, the parent will immediately receive an official WhatsApp text message with the alert details and dashboard link!

---

## 🧪 Running Automated Tests

Run the test suite to verify file validation, authentication, and database cleanup:

```powershell
py -3.14 test_app.py
```
Expected output:
```text
Ran 7 tests in 0.3s
OK
```
