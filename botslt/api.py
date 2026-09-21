"""
api.py — All API calls to the Bots.LT backend.
Uses X-API-Key header for authentication.
"""
import requests
from .auth import get_api_key, get_base_url


def _headers() -> dict:
    return {"X-API-Key": get_api_key()}


def _url(path: str) -> str:
    return f"{get_base_url()}{path}"


def verify_api_key() -> dict:
    """Verify that the stored API key is valid by calling /api/account."""
    try:
        r = requests.get(_url("/account"), headers=_headers(), timeout=10)
        if r.status_code == 200:
            return r.json()
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_bots() -> dict:
    """List all bots for the authenticated user."""
    r = requests.get(_url("/bots-list"), headers=_headers(), timeout=10)
    return r.json()


def get_all_commands(bot_id: str) -> dict:
    """Get all commands for a bot."""
    r = requests.get(_url(f"/bots/{bot_id}/commands"), headers=_headers(), timeout=10)
    return r.json()


def get_command_code(bot_id: str, command_name: str) -> str | None:
    """Get the code for a single command."""
    import base64
    encoded = base64.b64encode(command_name.encode("utf-8")).decode("utf-8")
    r = requests.get(_url(f"/bots/{bot_id}/commands/{encoded}"), headers=_headers(), timeout=10)
    if r.status_code == 200:
        data = r.json()
        return data.get("code") or data.get("result", {}).get("code")
    return None


def push_command(bot_id: str, command_name: str, code: str, aliases: list = None) -> dict:
    """Create or update a command on the server."""
    if aliases is None:
        aliases = []
        
    import base64
    encoded = base64.b64encode(command_name.encode("utf-8")).decode("utf-8")
    # Try update first
    r = requests.put(
        _url(f"/bots/{bot_id}/commands/{encoded}"),
        headers=_headers(),
        json={"code": code, "aliases": aliases},
        timeout=15
    )
    if r.status_code == 200:
        return r.json()
    # If not found, create it
    r2 = requests.post(
        _url(f"/bots/{bot_id}/commands"),
        headers=_headers(),
        json={"command": command_name, "code": code, "aliases": aliases},
        timeout=15
    )
    return r2.json()


def get_bot_errors(bot_id: str) -> dict:
    """Get recent error logs for a bot."""
    r = requests.get(_url(f"/bots/{bot_id}/errors"), headers=_headers(), timeout=10)
    return r.json()


def start_bot(bot_id: str) -> dict:
    """Start a bot."""
    r = requests.post(_url(f"/start-bot/{bot_id}"), headers=_headers(), timeout=10)
    return r.json()


def stop_bot(bot_id: str) -> dict:
    """Stop a bot."""
    r = requests.post(_url(f"/stop-bot/{bot_id}"), headers=_headers(), timeout=10)
    return r.json()


def delete_command(bot_id: str, command_name: str) -> dict:
    """Delete a command from the server."""
    import base64
    # The server uses base64 encoded command names in the URL
    # Replace any padding or safe chars if required, but standard base64 encode works based on push_command
    encoded = base64.b64encode(command_name.encode("utf-8")).decode("utf-8")
    # BotsLT API seems to use URL-safe base64 without padding in some cases, 
    # but based on push_command it works with standard base64.
    # To match 'L3Rlc3RfY2FsbGJhY2s' (which has no padding '='), we can strip padding to be safe.
    encoded = encoded.rstrip("=")
    
    r = requests.delete(_url(f"/bots/{bot_id}/commands/{encoded}"), headers=_headers(), timeout=15)
    return r.json()


def rename_command(bot_id: str, old_command: str, new_command: str) -> dict:
    """Rename a command on the server."""
    import base64
    encoded = base64.b64encode(old_command.encode("utf-8")).decode("utf-8").rstrip("=")
    
    r = requests.patch(
        _url(f"/bots/{bot_id}/commands/{encoded}/rename"),
        headers=_headers(),
        json={"command": new_command, "code": ""},
        timeout=15
    )
    return r.json()
