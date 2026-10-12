"""
push_to_github.py
=================
Automated script to:
  1. Create a new GitHub repository via the GitHub API
  2. Initialize local git repo and push all project files

Usage:
    py push_to_github.py

You will be prompted for your GitHub username and Personal Access Token.
"""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_NAME = "womens-safety-device"

# Files / dirs to EXCLUDE from GitHub (secrets, uploads, database, cache)
EXCLUDE = {
    ".env",
    "safety_alerts.db",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "env",
    "test_safety_alerts.db",
    "push_to_github.py",
}

def run(cmd: list, cwd=None) -> bool:
    result = subprocess.run(cmd, cwd=cwd or BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] {' '.join(cmd)}")
        print(f"  {result.stderr.strip()}")
        return False
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    return True

def main():
    import urllib.request
    import getpass

    print("=" * 60)
    print(" Women's Safety Device - GitHub Repository Setup")
    print("=" * 60)

    username = input("\nEnter your GitHub username: ").strip()
    token = getpass.getpass("Enter your GitHub Personal Access Token\n"
                            "(Settings → Developer settings → Personal access tokens → Tokens classic\n"
                            " → New token → check 'repo' → Generate token)\nToken: ").strip()

    if not username or not token:
        print("[ERROR] Username and token are required.")
        sys.exit(1)

    # 1. Create GitHub repo via REST API
    print(f"\n[1/4] Creating repository '{REPO_NAME}' on GitHub...")
    payload = json.dumps({
        "name": REPO_NAME,
        "description": "Women's Safety Device Prototype - ESP32-CAM Flask Dashboard",
        "private": False,
        "auto_init": False
    }).encode()

    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "ESP32-Safety-Uploader"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            repo_data = json.load(resp)
            remote_url = repo_data["clone_url"]
            print(f"  Repo created: {repo_data['html_url']}")
    except urllib.error.HTTPError as e:
        body = json.load(e)
        if e.code == 422:
            # Repo already exists — use existing
            remote_url = f"https://github.com/{username}/{REPO_NAME}.git"
            print(f"  Repository already exists — using: {remote_url}")
        else:
            print(f"  [ERROR] GitHub API {e.code}: {body.get('message','')}")
            sys.exit(1)

    # 2. Init local git repo
    print(f"\n[2/4] Initialising local git repository...")
    git_dir = BASE_DIR / ".git"
    if not git_dir.exists():
        if not run(["git", "init", "-b", "main"]):
            sys.exit(1)
    else:
        print("  Git repo already initialised.")

    # Write/update .gitignore to be safe
    gitignore_path = BASE_DIR / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(
            "# secrets\n.env\n*.db\n__pycache__/\nuploads/*\n!uploads/.gitkeep\nvenv/\n.venv/\n"
        )

    # 3. Stage & commit
    print(f"\n[3/4] Staging files and creating commit...")
    run(["git", "config", "user.email", f"{username}@users.noreply.github.com"])
    run(["git", "config", "user.name", username])
    run(["git", "add", "."])
    run(["git", "commit", "-m", "Initial commit: Women's Safety Device Flask App"])

    # 4. Push
    print(f"\n[4/4] Pushing to GitHub...")
    auth_url = remote_url.replace("https://", f"https://{username}:{token}@")
    run(["git", "remote", "remove", "origin"])  # remove if exists
    run(["git", "remote", "add", "origin", auth_url])
    if not run(["git", "push", "-u", "origin", "main"]):
        # Try force push if branch issue
        run(["git", "push", "-u", "--force", "origin", "main"])

    print("\n" + "=" * 60)
    print(f" SUCCESS! Code pushed to GitHub.")
    print(f" Repository URL: https://github.com/{username}/{REPO_NAME}")
    print(f"\n Next step: Deploy on Render")
    print(f"  1. Go to https://render.com and sign up / log in")
    print(f"  2. Click 'New +' → 'Web Service'")
    print(f"  3. Connect your GitHub account")
    print(f"  4. Select repository: {REPO_NAME}")
    print(f"  5. Render auto-detects Python. Set start command to:")
    print(f"       gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120")
    print(f"  6. Add environment variables (shown below)")
    print(f"  7. Click Deploy!")
    print("=" * 60)
    print("\n Environment Variables to add in Render Dashboard:")
    print("  SECRET_KEY          = (click Generate — Render creates it)")
    print("  DASHBOARD_USERNAME  = admin")
    print("  DASHBOARD_PASSWORD  = (your chosen password)")
    print("  DEVICE_UPLOAD_TOKEN = (your ESP32 token)")
    print("  FLASK_ENV           = production")
    print("  BASE_URL            = https://<your-render-app-name>.onrender.com")
    print("  (WhatsApp vars optional — leave blank to skip)")

if __name__ == "__main__":
    main()
