"""
config.py — Reads and writes blp.json in the current project directory.
This file is safe to commit to Git — it only contains bot_id and command mappings.
"""
import json
from pathlib import Path

CONFIG_FILE = Path("blp.json")
LOCK_FILE = Path("botslt.lock")


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_config() -> dict:
    """Load blp.json from current directory."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data: dict):
    """Save blp.json to current directory."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_lock() -> dict:
    """Load botslt.lock (local hash cache, NOT for Git)."""
    if not LOCK_FILE.exists():
        return {"files": {}}
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"files": {}}


def save_lock(data: dict):
    """Save botslt.lock."""
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_file_hash(filepath: str) -> str:
    """Return SHA256 hash of a local file."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            h.update(f.read())
        return h.hexdigest()
    except FileNotFoundError:
        return ""


def update_lock_for_file(filename: str):
    """Update the hash entry for a specific file in botslt.lock."""
    lock = load_lock()
    lock.setdefault("files", {})[filename] = get_file_hash(filename)
    save_lock(lock)


def get_changed_files() -> list[dict]:
    """Compare local files with botslt.lock hashes. Returns list of changed files."""
    config = load_config()
    lock = load_lock()
    cached_hashes = lock.get("files", {})
    commands = config.get("commands", {})

    changed = []
    for cmd_name, filename in commands.items():
        if not Path(filename).exists():
            continue
        current_hash = get_file_hash(filename)
        cached_hash = cached_hashes.get(filename, "")
        if current_hash != cached_hash:
            changed.append({"command": cmd_name, "file": filename})
    return changed


def ensure_gitignore():
    """Add botslt.lock to .gitignore if it's not already there."""
    gitignore = Path(".gitignore")
    entries_to_add = ["# BotsLT", "botslt.lock"]
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if "botslt.lock" not in content:
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(entries_to_add) + "\n")
    else:
        gitignore.write_text("\n".join(entries_to_add) + "\n", encoding="utf-8")
