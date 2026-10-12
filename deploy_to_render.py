"""
deploy_to_render.py
====================
Uploads ALL project files directly to a GitHub repository using the GitHub
REST API (no git installation needed), then prints Render deploy instructions.

Usage:
    py deploy_to_render.py

You only need Python and an internet connection.
"""

import base64
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
REPO_NAME = "womens-safety-device"

# Files and directories to SKIP
SKIP_NAMES = {
    ".env",
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "safety_alerts.db",
    "test_safety_alerts.db",
    "PortableGit.exe",
    "deploy_to_render.py",   # don't upload this script itself
}
SKIP_EXTENSIONS = {".pyc", ".pyo", ".db", ".exe"}
SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", "env", ".gitkeep"}


def github_request(method: str, path: str, token: str, data=None):
    """Make a GitHub REST API request."""
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "WomensSafetyDeployScript/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            body = json.load(e)
        except Exception:
            body = {"message": e.read().decode()}
        return e.code, body


def collect_files():
    """Walk project directory and collect all files to upload."""
    files = {}
    for item in BASE_DIR.rglob("*"):
        if item.is_dir():
            continue
        # Skip by name
        if item.name in SKIP_NAMES:
            continue
        # Skip by extension
        if item.suffix.lower() in SKIP_EXTENSIONS:
            continue
        # Skip if any parent dir is in SKIP_DIRS
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        # Skip uploads folder content (keep placeholder)
        rel = item.relative_to(BASE_DIR)
        rel_str = rel.as_posix()
        if rel_str.startswith("uploads/") and item.name != ".gitkeep":
            continue

        try:
            content = item.read_bytes()
            files[rel_str] = base64.b64encode(content).decode()
        except Exception as e:
            print(f"  Warning: could not read {rel_str}: {e}")
    return files


def main():
    print("=" * 65)
    print("  Women's Safety Device — GitHub Upload & Render Deploy")
    print("=" * 65)
    print("\nThis script uploads your code to GitHub WITHOUT needing Git.")
    print("All it needs is your GitHub username and a Personal Access Token.\n")

    username = input("GitHub Username: ").strip()
    token = getpass.getpass(
        "GitHub Personal Access Token\n"
        "  (Get one: github.com → Settings → Developer settings →\n"
        "   Personal access tokens → Tokens (classic) → New token\n"
        "   → Tick 'repo' checkbox → Generate token)\nToken: "
    ).strip()

    if not username or not token:
        print("[ERROR] Both username and token are required.")
        sys.exit(1)

    # 1. Create repository
    print(f"\n[1/3] Creating GitHub repo '{REPO_NAME}'...")
    status, resp = github_request("POST", "/user/repos", token, {
        "name": REPO_NAME,
        "description": "Women's Safety Device Prototype - ESP32-CAM Flask Dashboard",
        "private": False,
        "auto_init": False,
    })
    if status == 201:
        repo_url = resp["html_url"]
        print(f"  ✅ Repository created: {repo_url}")
    elif status == 422 and "already exists" in resp.get("errors", [{}])[0].get("message", ""):
        repo_url = f"https://github.com/{username}/{REPO_NAME}"
        print(f"  ℹ️  Repository already exists — uploading to: {repo_url}")
    else:
        print(f"  [ERROR] GitHub API {status}: {resp.get('message', resp)}")
        sys.exit(1)

    # 2. Collect and upload files
    print(f"\n[2/3] Scanning project files...")
    files = collect_files()
    print(f"  Found {len(files)} files to upload.")

    success_count = 0
    fail_count = 0
    for i, (rel_path, content_b64) in enumerate(files.items(), 1):
        print(f"  [{i:02d}/{len(files)}] Uploading: {rel_path}", end=" ", flush=True)

        # Check if file already exists (to get its SHA for update)
        get_status, get_resp = github_request(
            "GET", f"/repos/{username}/{REPO_NAME}/contents/{rel_path}", token
        )
        sha = get_resp.get("sha") if get_status == 200 else None

        payload = {
            "message": f"Add {rel_path}",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha
            payload["message"] = f"Update {rel_path}"

        put_status, put_resp = github_request(
            "PUT", f"/repos/{username}/{REPO_NAME}/contents/{rel_path}", token, payload
        )
        if put_status in (200, 201):
            print("✅")
            success_count += 1
        else:
            print(f"❌ ({put_resp.get('message', 'error')})")
            fail_count += 1

    # 3. Print Render instructions
    render_app_name = REPO_NAME  # e.g. womens-safety-device
    print(f"\n[3/3] Upload complete! {success_count} files uploaded, {fail_count} failed.")
    print(f"\n{'=' * 65}")
    print(f"  ✅ CODE IS ON GITHUB:")
    print(f"     {repo_url}")
    print(f"\n{'=' * 65}")
    print("""
  📦 DEPLOY ON RENDER (5 minutes):
  ─────────────────────────────────
  1. Open  https://render.com  and sign up / log in (free account).

  2. Click "New +"  →  "Web Service"

  3. Connect your GitHub account and select repo:
         womens-safety-device

  4. Render auto-detects Python. Confirm these settings:
       • Environment:    Python 3
       • Build Command:  pip install -r requirements.txt
       • Start Command:  gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120

  5. Scroll to "Environment Variables" and add:
       SECRET_KEY           →  (click "Generate" button)
       FLASK_ENV            →  production
       DASHBOARD_USERNAME   →  admin
       DASHBOARD_PASSWORD   →  (choose a strong password)
       DEVICE_UPLOAD_TOKEN  →  (paste your ESP32 token)
       BASE_URL             →  https://<your-app>.onrender.com
       CLOUDINARY_CLOUD_NAME→  (from your cloudinary.com dashboard)
       CLOUDINARY_API_KEY   →  (from your cloudinary.com dashboard)
       CLOUDINARY_API_SECRET→  (from your cloudinary.com dashboard)

  6. Click "Create Web Service".

  7. Wait ~3 minutes for the first build. Then open your live URL:
       https://womens-safety-device.onrender.com
     (or whatever name Render assigns — check the dashboard).

  8. Update your ESP32 Arduino sketch:
       const char *UPLOAD_URL =
         "https://womens-safety-device.onrender.com/api/events";

  ☁️  NOTE on File Storage:
     With your Cloudinary credentials set in Render, all uploaded
     photos and WAV audio files are stored permanently in the cloud
     for free and will survive all server restarts.
""")


if __name__ == "__main__":
    main()
