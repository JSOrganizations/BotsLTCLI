"""
cli.py — Main entry point for the blp CLI.
Command: blp <subcommand>
"""
import click
import sys
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
from . import auth, config, api

try:
    __version__ = version("botslt")
except PackageNotFoundError:
    __version__ = "unknown"


# ─── Helpers ────────────────────────────────────────────────────────────────

def require_login():
    """Abort with a helpful message if not logged in."""
    key = auth.get_api_key()
    if not key:
        click.echo(click.style("[-] Not logged in.", fg="red"))
        click.echo("  Run: blp login")
        sys.exit(1)

def require_config():
    """Abort with a helpful message if blp.json is missing, or prompt for bot_id."""
    if not config.config_exists():
        click.echo(click.style("[-] No blp.json found in current directory.", fg="yellow"))
        bot_id = click.prompt("Please enter your Bot ID to initialize", type=str, default="")
        if not bot_id.strip():
            click.echo("  Run: blp init (to initialize manually)")
            sys.exit(1)
        config.save_config({"bot_id": bot_id.strip(), "commands": {}})
        click.echo(click.style(f"[+] Initialized blp.json for bot {bot_id.strip()}", fg="green"))


# ─── CLI Group ───────────────────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="blp")
def cli():
    """
    blp — Official CLI for Bots.LT

    Sync your Telegram bot commands like Git.

    \b
    Quick start:
      blp login          Save your API key
      blp init           Setup a project in the current folder
      blp push           Push all changed commands to server
      blp pull           Pull all commands from server
      blp status         Show which files have changed
      blp bots           List all your bots
      blp commands       List all commands for a bot
      blp view           View the code of a specific command
      blp delete         Delete a command from the server
      blp start          Start your bot
      blp stop           Stop your bot

    Get your API Key from: https://bots.lt/dashboard -> Settings -> Security
    """
    pass


# ─── login ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--key", "-k", prompt=False, default=None, help="API Key (from Settings -> Security)")
def login(key):
    """Save your Bots.LT API key to ~/.botslt/credentials.json"""
    if not key:
        click.echo("Get your API Key from: https://bots.lt/dashboard -> Settings -> Security")
        key = click.prompt("API Key", hide_input=True)

    key = key.strip()
    if not key:
        click.echo(click.style("[-] API Key cannot be empty.", fg="red"))
        sys.exit(1)

    # Validate key against server
    click.echo("Verifying API key...")
    auth.save_credentials(key)
    result = api.verify_api_key()

    if result.get("ok"):
        acc = result.get("result", {}).get("account", {})
        email = acc.get("email", "unknown")
        click.echo(click.style(f"[+] Logged in as: {email}", fg="green"))
        click.echo(click.style(f"  Credentials saved to: {auth.CRED_FILE}", fg="bright_black"))
    else:
        auth.clear_credentials()
        click.echo(click.style(f"[-] Invalid API key: {result.get('error', 'Unknown error')}", fg="red"))
        sys.exit(1)


# ─── logout ──────────────────────────────────────────────────────────────────

@cli.command()
def logout():
    """Remove stored credentials from ~/.botslt/credentials.json"""
    auth.clear_credentials()
    click.echo(click.style("[+] Logged out successfully.", fg="green"))


# ─── init ────────────────────────────────────────────────────────────────────

def generate_agent_rules():
    """Fetch documentation from GitHub and create AGENTS.md for AI context."""
    click.echo(click.style("  [*] Fetching AI rules from documentation...", fg="bright_black"))
    try:
        import requests
        # Get tree of docs repo
        resp = requests.get("https://api.github.com/repos/JSOrganizations/docs/git/trees/main?recursive=1", timeout=10)
        if resp.status_code != 200:
            click.echo(click.style("  [-] Failed to fetch docs tree from GitHub.", fg="yellow"))
            return
            
        tree = resp.json().get("tree", [])
        md_files = [item["path"] for item in tree if item["path"].endswith((".mdx", ".md")) and "logo" not in item["path"]]
        
        if not md_files:
            return
            
        rules_content = "# Bots.LT (BLP) AI Assistant Rules\n\n"
        rules_content += "You are an AI assistant writing code for the Bots.LT platform using BLP (Bots Limited Python).\n"
        rules_content += "Adhere strictly to the syntax, rules, and limitations provided in the following documentation:\n\n"
        
        for file_path in md_files:
            raw_url = f"https://raw.githubusercontent.com/JSOrganizations/docs/main/{file_path}"
            file_resp = requests.get(raw_url, timeout=5)
            if file_resp.status_code == 200:
                rules_content += f"## Source: {file_path}\n\n{file_resp.text}\n\n---\n\n"
                
        with open("AGENTS.md", "w", encoding="utf-8") as f:
            f.write(rules_content)
            
        click.echo(click.style("  [+] Generated AGENTS.md for AI assistance.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"  [-] Could not generate AGENTS.md: {str(e)}", fg="yellow"))

@cli.command()
@click.option("--bot-id", "-b", prompt="Bot ID", help="Your Bots.LT Bot ID")
def init(bot_id):
    """Create a blp.json config file in the current directory."""
    require_login()

    if config.config_exists():
        if not click.confirm("blp.json already exists. Overwrite?"):
            click.echo("Aborted.")
            sys.exit(0)

    bot_id = bot_id.strip()
    data = {
        "bot_id": bot_id,
        "commands": {
            "/start": {
                "file": "start.py",
                "aliases": []
            }
        }
    }
    config.save_config(data)
    config.ensure_gitignore()

    if not Path("start.py").exists():
        with open("start.py", "w", encoding="utf-8") as f:
            f.write("bot.sendMessage(\n    text='<b>Hello from Bots.LT CLI!</b>',\n    parse_mode='html'\n)\n")
        click.echo(click.style("  [+] Generated starter file: start.py", fg="bright_black"))

    click.echo(click.style(f"[+] Initialized project for bot ID: {bot_id}", fg="green"))
    click.echo(click.style("  blp.json created. Add more commands with: blp add /help help.py", fg="bright_black"))

    # Generate AI rules in the background/synchronously
    generate_agent_rules()


# ─── add ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("command_name")
@click.argument("filename")
def add(command_name, filename):
    """Map a command name to a local .py file.

    \b
    Example:
      blp add /start start.py
      blp add @ at_handler.py
    """
    require_config()

    cfg = config.load_config()
    cfg.setdefault("commands", {})[command_name] = {
        "file": filename,
        "aliases": []
    }
    config.save_config(cfg)

    click.echo(click.style(f"[+] Mapped '{command_name}' -> '{filename}'", fg="green"))
    click.echo("  Remember to create the file, then run: blp push")


# ─── status ──────────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show which local files have changed since last push."""
    require_login()
    require_config()

    cfg = config.load_config()
    commands = cfg.get("commands", {})

    if not commands:
        click.echo("No commands mapped. Use: blp add /start start.py")
        return

    changed = config.get_changed_files()
    changed_files = {c["file"] for c in changed}

    click.echo(f"\n  Bot ID: {click.style(cfg.get('bot_id', '?'), fg='cyan')}\n")

    modified = []
    ok = []
    missing = []

    for cmd_name, cmd_info in commands.items():
        filename = cmd_info.get("file") if isinstance(cmd_info, dict) else cmd_info
        if not filename or not Path(filename).exists():
            missing.append((cmd_name, filename))
        elif filename in changed_files:
            modified.append((cmd_name, filename))
        else:
            ok.append((cmd_name, filename))

    if modified:
        click.echo(click.style("  Modified (not pushed):", fg="yellow"))
        for cmd, f in modified:
            click.echo(f"    {click.style('M', fg='yellow')}  {f:<25} -> {cmd}")

    if missing:
        click.echo(click.style("\n  File not found:", fg="red"))
        for cmd, f in missing:
            click.echo(f"    {click.style('!', fg='red')}  {f:<25} -> {cmd}")

    if ok:
        click.echo(click.style("\n  Up to date:", fg="green"))
        for cmd, f in ok:
            click.echo(f"    {click.style('[+]', fg='green')}  {f:<25} -> {cmd}")

    if not modified and not missing:
        click.echo(click.style("\n  Everything is up to date!", fg="green"))
    else:
        click.echo(f"\n  Run {click.style('blp push', fg='cyan')} to sync changes.")


# ─── push ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("files", nargs=-1)
@click.option("--all", "-a", "push_all", is_flag=True, help="Push all commands, even if unchanged")
@click.option("--force", "-f", is_flag=True, help="Same as --all")
def push(files, push_all, force):
    """Push changed commands to Bots.LT server.

    \b
    Examples:
      blp push                   Push only changed files
      blp push start.py          Push a specific file
      blp push --all             Push all commands regardless of changes
    """
    require_login()
    require_config()

    cfg = config.load_config()
    bot_id = cfg.get("bot_id")
    commands = cfg.get("commands", {})

    if not commands:
        click.echo("No commands configured. Run: blp add /start start.py")
        return

    push_all = push_all or force

    # If specific files given, only push those
    if files:
        to_push = []
        for cmd, info in commands.items():
            f = info.get("file") if isinstance(info, dict) else info
            if f in files:
                to_push.append((cmd, info))
        if not to_push:
            click.echo(click.style("[-] No matching commands found for the given files.", fg="red"))
            click.echo("  Check your blp.json mappings.")
            sys.exit(1)
    elif push_all:
        to_push = list(commands.items())
    else:
        changed = config.get_changed_files()
        changed_files = {c["file"] for c in changed}
        to_push = []
        for cmd, info in commands.items():
            f = info.get("file") if isinstance(info, dict) else info
            if f in changed_files:
                to_push.append((cmd, info))

    if not to_push:
        click.echo(click.style("[+] Nothing to push. Everything is up to date.", fg="green"))
        return

    click.echo(f"\n  Syncing bot {click.style(bot_id, fg='cyan')}...\n")

    updated = 0
    failed = 0

    for cmd_name, cmd_info in to_push:
        if isinstance(cmd_info, dict):
            filename = cmd_info.get("file")
            aliases = cmd_info.get("aliases", [])
        else:
            filename = cmd_info
            aliases = []

        if not filename or not Path(filename).exists():
            click.echo(f"  {click.style('!', fg='red')}  {filename:<25} -> {cmd_name} (file not found, skipped)")
            failed += 1
            continue

        with open(filename, "r", encoding="utf-8") as f:
            code = f.read()

        try:
            result = api.push_command(bot_id, cmd_name, code, aliases=aliases)
            if result.get("ok"):
                click.echo(f"  {click.style('[+]', fg='green')}  {filename:<25} -> {cmd_name}")
                config.update_lock_for_file(filename)
                updated += 1
            else:
                err = result.get("error") or result.get("detail", "Unknown error")
                click.echo(f"  {click.style('[-]', fg='red')}  {filename:<25} -> {cmd_name} ({err})")
                failed += 1
        except Exception as e:
            click.echo(f"  {click.style('[-]', fg='red')}  {filename:<25} -> {cmd_name} (Error: {e})")
            failed += 1

    click.echo()
    click.echo(f"  Done! {click.style(str(updated), fg='green')} pushed, {click.style(str(failed), fg='red' if failed else 'bright_black')} failed.")


# ─── pull ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite local files without asking")
def pull(overwrite):
    """Pull all commands from server and create local .py files."""
    require_login()
    require_config()

    cfg = config.load_config()
    bot_id = cfg.get("bot_id")

    click.echo(f"\n  Pulling from bot {click.style(bot_id, fg='cyan')}...\n")

    result = api.get_all_commands(bot_id)
    if not result.get("ok"):
        click.echo(click.style(f"[-] Failed to fetch commands: {result.get('error', 'Unknown error')}", fg="red"))
        sys.exit(1)

    commands_data = result.get("commands") or result.get("result", {}).get("commands", [])

    if not commands_data:
        click.echo("  No commands found on the server.")
        return

    cfg_commands = cfg.setdefault("commands", {})
    created = 0
    skipped = 0

    for cmd in commands_data:
        cmd_name = cmd.get("command") or cmd.get("name") or cmd.get("trigger", "")
        code = cmd.get("code", "")
        aliases = cmd.get("aliases", [])

        if not cmd_name:
            continue

        existing_info = cfg_commands.get(cmd_name)
        if existing_info:
            if isinstance(existing_info, str):
                filename = existing_info
            else:
                filename = existing_info.get("file")
        else:
            # Generate a safe filename from the command name
            safe_name = cmd_name.lstrip("/").replace(" ", "_").replace("*", "star").replace("@", "at") or "command"
            filename = f"{safe_name}.py"

        if Path(filename).exists() and not overwrite:
            if not click.confirm(f"  '{filename}' already exists. Overwrite?"):
                click.echo(f"  {click.style('-', fg='yellow')}  {filename:<25} skipped")
                skipped += 1
                continue

        with open(filename, "w", encoding="utf-8") as f:
            f.write(code)

        cfg_commands[cmd_name] = {
            "file": filename,
            "aliases": aliases
        }
        config.update_lock_for_file(filename)
        click.echo(f"  {click.style('[+]', fg='green')}  {filename:<25} <- {cmd_name}")
        created += 1

    config.save_config(cfg)
    click.echo()
    click.echo(f"  Done! {click.style(str(created), fg='green')} pulled, {skipped} skipped.")


# ─── logs ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--limit", "-n", default=10, help="Number of recent errors to show (default: 10)")
def logs(limit):
    """Show recent error logs for your bot."""
    require_login()
    require_config()

    cfg = config.load_config()
    bot_id = cfg.get("bot_id")

    result = api.get_bot_errors(bot_id)
    if not result.get("ok"):
        click.echo(click.style(f"[-] Failed to fetch logs: {result.get('error', 'Unknown error')}", fg="red"))
        sys.exit(1)

    errors = result.get("errors") or result.get("result", [])

    if not errors:
        click.echo(click.style("[+] No recent errors. Your bot is running clean!", fg="green"))
        return

    click.echo(f"\n  Recent errors for bot {click.style(bot_id, fg='cyan')}:\n")

    for i, err in enumerate(errors[:limit]):
        cmd = err.get("command_name", "?")
        msg = err.get("error_message", "?")
        ts = err.get("created_at", "")
        click.echo(f"  [{click.style(str(i+1), fg='yellow')}] {click.style(cmd, fg='cyan')} — {ts}")
        for line in msg.splitlines():
            click.echo(f"      {line}")
        click.echo()


# ─── bots ────────────────────────────────────────────────────────────────────

@cli.command()
def bots():
    """List all your bots."""
    require_login()

    result = api.list_bots()
    if not result.get("ok"):
        click.echo(click.style(f"[-] {result.get('error', 'Failed to list bots')}", fg="red"))
        sys.exit(1)

    bots_list = result.get("result", {}).get("bots", [])

    if not bots_list:
        click.echo("No bots found.")
        return

    click.echo(f"\n  {click.style(str(len(bots_list)), fg='cyan')} bot(s) found:\n")
    for b in bots_list:
        status_color = "green" if b.get("is_active") else "red"
        status = "Running" if b.get("is_active") else "Stopped"
        
        name = b.get("name") or b.get("first_name") or ""
        username = b.get("username", "?")
        display_name = f"{name} (@{username})" if name else f"@{username}"
        
        click.echo(
            f"  {click.style(str(b.get('id', '?')), fg='cyan'):<12}"
            f"  {display_name:<40}"
            f"  {click.style(status, fg=status_color)}"
        )
    click.echo()


# ─── start / stop ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("bot_id", required=False)
def start(bot_id):
    """Start your bot on the server.
    
    If BOT_ID is not provided, it uses the one from blp.json or asks you.
    """
    require_login()
    if not bot_id:
        if config.config_exists():
            bot_id = config.load_config().get("bot_id")
        else:
            bot_id = click.prompt("Bot ID to start")
            
    bot_id = str(bot_id).strip()
    result = api.start_bot(bot_id)
    if result.get("ok"):
        click.echo(click.style(f"[+] Bot {bot_id} started successfully.", fg="green"))
    else:
        err = result.get("error") or result.get("detail", "Unknown error")
        click.echo(click.style(f"[-] Failed to start bot: {err}", fg="red"))


@cli.command()
@click.argument("bot_id", required=False)
def stop(bot_id):
    """Stop your bot on the server.
    
    If BOT_ID is not provided, it uses the one from blp.json or asks you.
    """
    require_login()
    if not bot_id:
        if config.config_exists():
            bot_id = config.load_config().get("bot_id")
        else:
            bot_id = click.prompt("Bot ID to stop")
            
    bot_id = str(bot_id).strip()
    result = api.stop_bot(bot_id)
    if result.get("ok"):
        click.echo(click.style(f"[+] Bot {bot_id} stopped successfully.", fg="green"))
    else:
        err = result.get("error") or result.get("detail", "Unknown error")
        click.echo(click.style(f"[-] Failed to stop bot: {err}", fg="red"))


# ─── commands ─────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("bot_id", required=False)
def commands(bot_id):
    """List all commands for your bot on the server.
    
    If BOT_ID is not provided, it uses the one from blp.json or asks you.
    """
    require_login()
    if not bot_id:
        if config.config_exists():
            bot_id = config.load_config().get("bot_id")
        else:
            bot_id = click.prompt("Bot ID to fetch commands")
            
    bot_id = str(bot_id).strip()
    click.echo(f"Fetching commands for bot {click.style(bot_id, fg='cyan')}...\n")
    
    result = api.get_all_commands(bot_id)
    if not result.get("ok"):
        err = result.get("error") or result.get("detail", "Unknown error")
        click.echo(click.style(f"[-] Failed to fetch commands: {err}", fg="red"))
        sys.exit(1)

    cmds = result.get("commands") or result.get("result", {}).get("commands", [])

    if not cmds:
        click.echo(click.style(f"[+] No commands found for bot {bot_id}.", fg="yellow"))
        return

    click.echo(f"  {click.style(str(len(cmds)), fg='green')} command(s) found:\n")
    for c in cmds:
        cmd_name = c.get("command") or c.get("name") or c.get("trigger", "?")
        aliases = c.get("aliases", [])
        
        aliases_str = f" (Aliases: {', '.join(aliases)})" if aliases else ""
        click.echo(f"  {click.style(cmd_name, fg='cyan')}{click.style(aliases_str, fg='bright_black')}")
        
    click.echo()


# ─── delete ───────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("command_name")
@click.argument("bot_id", required=False)
def delete(command_name, bot_id):
    """Delete a command from the server.
    
    If BOT_ID is not provided, it uses the one from blp.json or asks you.
    """
    require_login()
    if not bot_id:
        if config.config_exists():
            bot_id = config.load_config().get("bot_id")
        else:
            bot_id = click.prompt("Bot ID to delete from")
            
    bot_id = str(bot_id).strip()
    click.echo(f"Deleting command {click.style(command_name, fg='yellow')} from bot {click.style(bot_id, fg='cyan')}...")
    
    result = api.delete_command(bot_id, command_name)
    
    if result.get("ok"):
        click.echo(click.style(f"[+] Command '{command_name}' deleted successfully.", fg="green"))
        
        # Remove from local blp.json if it exists
        if config.config_exists():
            cfg = config.load_config()
            cmds = cfg.get("commands", {})
            if command_name in cmds:
                del cmds[command_name]
                config.save_config(cfg)
                click.echo(click.style(f"  [+] Removed '{command_name}' from local blp.json", fg="green"))
    else:
        err = result.get("error") or result.get("detail", "Unknown error")
        click.echo(click.style(f"[-] Failed to delete command: {err}", fg="red"))


# ─── view ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("command_name")
@click.argument("bot_id", required=False)
def view(command_name, bot_id):
    """View the code of a specific command from the server.
    
    If BOT_ID is not provided, it uses the one from blp.json or asks you.
    """
    require_login()
    if not bot_id:
        if config.config_exists():
            bot_id = config.load_config().get("bot_id")
        else:
            bot_id = click.prompt("Bot ID to view command from")
            
    bot_id = str(bot_id).strip()
    click.echo(f"Fetching code for {click.style(command_name, fg='yellow')} from bot {click.style(bot_id, fg='cyan')}...\n")
    
    code = api.get_command_code(bot_id, command_name)
    if code is not None:
        click.echo(click.style(f"--- Code for {command_name} ---", fg="green"))
        click.echo(code)
        click.echo(click.style("-" * 40, fg="green"))
    else:
        click.echo(click.style(f"[-] Command '{command_name}' not found or failed to fetch.", fg="red"))


if __name__ == "__main__":
    cli()

@cli.command()
def docs():
    """Fetch the latest AI agent context (AGENTS.md) from the docs."""
    generate_agent_rules()
    click.echo(click.style("[+] Documentation rules updated successfully.", fg="green"))
