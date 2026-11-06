"""Shared paths and upstream repository configuration."""

from pathlib import Path
import os
import shutil


# Base application directory: ~/.Github-Auto-Uploader (or custom env var)
APP_DIR = Path(
    os.environ.get("GITHUB_UPLOADER_DIR")
    or (Path.home() / ".Github-Auto-Uploader")
).resolve()
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "upload.log"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Migrate existing config if ~/.Github-Auto-Uploader/config.json does not exist yet
if not CONFIG_FILE.exists():
    fallback_candidates = [
        PROJECT_ROOT / "config.json",
        Path("/data/data/com.termux/files/home/GitHub-Auto-Uploader/config.json"),
        Path("/root/.Github-Auto-Uploader/config.json"),
    ]
    for fallback in fallback_candidates:
        if fallback.exists() and fallback != CONFIG_FILE:
            try:
                shutil.copy2(fallback, CONFIG_FILE)
                break
            except Exception:
                pass

UPSTREAM_OWNER = os.getenv("GITHUB_UPLOADER_OWNER", "Mr-Risov")
UPSTREAM_REPOSITORY = os.getenv("GITHUB_UPLOADER_REPOSITORY", "GitHub-Auto-Uploader")
UPSTREAM_BRANCH = os.getenv("GITHUB_UPLOADER_BRANCH", "main")
UPSTREAM_WEB_URL = f"https://github.com/{UPSTREAM_OWNER}/{UPSTREAM_REPOSITORY}"
UPSTREAM_GIT_URL = f"{UPSTREAM_WEB_URL}.git"
UPSTREAM_API_URL = f"https://api.github.com/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPOSITORY}"

GITHUB_API_TIMEOUT = 10
