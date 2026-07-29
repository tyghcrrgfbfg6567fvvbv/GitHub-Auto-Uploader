"""Shared paths and upstream repository configuration."""

from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"
LOG_FILE = PROJECT_ROOT / "upload.log"

UPSTREAM_OWNER = os.getenv("GITHUB_UPLOADER_OWNER", "Mr-Risov")
UPSTREAM_REPOSITORY = os.getenv("GITHUB_UPLOADER_REPOSITORY", "GitHub-Auto-Uploader")
UPSTREAM_BRANCH = os.getenv("GITHUB_UPLOADER_BRANCH", "main")
UPSTREAM_WEB_URL = f"https://github.com/{UPSTREAM_OWNER}/{UPSTREAM_REPOSITORY}"
UPSTREAM_GIT_URL = f"{UPSTREAM_WEB_URL}.git"
UPSTREAM_API_URL = f"https://api.github.com/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPOSITORY}"

GITHUB_API_TIMEOUT = 10
