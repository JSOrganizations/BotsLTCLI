"""
auth.py — Handles login and credential storage.
Credentials are stored in ~/.botslt/credentials.json (never in the project folder).
"""
import os
import json
from pathlib import Path

CRED_DIR = Path.home() / ".botslt"
CRED_FILE = CRED_DIR / "credentials.json"


def get_credentials() -> dict:
    """Load credentials from ~/.botslt/credentials.json"""
    if not CRED_FILE.exists():
        return {}
    try:
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_credentials(api_key: str, base_url: str = "https://bots.lt/api"):
    """Save credentials to ~/.botslt/credentials.json"""
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    data = {"api_key": api_key, "base_url": base_url}
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_api_key() -> str | None:
    """Return the stored API key, or None if not logged in."""
    return get_credentials().get("api_key")


def get_base_url() -> str:
    """Return the stored base URL (defaults to bots.lt)."""
    return get_credentials().get("base_url", "https://bots.lt/api")


def clear_credentials():
    """Remove stored credentials (logout)."""
    if CRED_FILE.exists():
        CRED_FILE.unlink()
