# blp — Official Bots.LT CLI

> Sync your Telegram bot commands like Git.

```bash
pip install botslt
```

---

## Quick Start

```bash
# 1. Save your API key (from Settings → Security on bots.lt)
blp login

# 2. Create a project in your bot's folder
mkdir my-bot && cd my-bot
blp init

# 3. Map your commands to .py files
blp add /start start.py
blp add /help  help.py
blp add @       at_handler.py

# 4. Write your code, then push!
blp push
```

---

## How it Works

Your project folder will look like this:

```
my-telegram-bot/
├── blp.json        ← Bot ID + command mappings (safe to commit to Git)
├── botslt.lock        ← Hash cache for change detection (Git-ignored)
├── start.py           ← Code for /start command
├── help.py            ← Code for /help command
└── at_handler.py      ← Code for @ (global) handler
```

Your **API key is stored globally** in `~/.botslt/credentials.json` — never in the project folder, so it's never accidentally committed to Git.

---

## Commands

| Command | Description |
|---------|-------------|
| `blp login` | Save your API key |
| `blp logout` | Remove saved credentials |
| `blp init` | Create `blp.json` in current folder |
| `blp add /cmd file.py` | Map a command to a local file |
| `blp push` | Push changed commands to server |
| `blp push file.py` | Push a specific file |
| `blp push --all` | Push all commands (ignore change detection) |
| `blp pull` | Pull all server commands to local files |
| `blp status` | Show which files have changed |
| `blp logs` | Show recent bot error logs |
| `blp bots` | List all your bots |

---

## Example `blp.json` (with Aliases)

```json
{
    "bot_id": "12345678",
    "commands": {
        "/start": {
            "file": "start.py",
            "aliases": ["/menu"]
        },
        "/help": "help.py",
        "/balance": {
            "file": "balance.py",
            "aliases": ["/bal", "Balance"]
        },
        "@": "at_handler.py",
        "*": "fallback.py"
    }
}
```

---

## Example Bot Command (start.py)

```python
bot.sendMessage(
    text=f"<b>Welcome, {user.first_name}!</b>\n\nHow can I help you?",
    parse_mode="html",
    reply_markup={
        "keyboard": [
            [{"text": "💰 Balance"}],
            [{"text": "❓ Help"}]
        ],
        "resize_keyboard": True
    }
)
```

---

## .gitignore

`blp init` automatically adds `botslt.lock` to your `.gitignore`:

```gitignore
# BotsLT
botslt.lock
```

> **Never commit `~/.botslt/credentials.json`** — it contains your API key.

---

## Links

- Platform: [https://bots.lt](https://bots.lt)
- Documentation: [https://help.bots.lt](https://help.bots.lt)
- Support: [https://t.me/JSOrganization](https://t.me/JSOrganization)
