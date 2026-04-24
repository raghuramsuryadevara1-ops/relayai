import json
import subprocess
from pathlib import Path

import keyring
from rich.console import Console
from rich.table import Table

CONFIG_DIR = Path.home() / ".relayai"
CONFIG_FILE = CONFIG_DIR / "config.json"
KEYRING_SERVICE = "relayai"
KEYRING_CLAUDE_KEY = "claude_api_key"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def _save_config(data: dict):
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_configured() -> bool:
    return bool(get_claude_key())


def get_claude_key() -> str:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_CLAUDE_KEY) or ""


def setup_credentials(console: Console):
    console.print("[bold]Step 1: Claude API Key[/bold]")
    console.print("[dim]Get your key from: https://console.anthropic.com[/dim]\n")

    key = console.input("[cyan]Enter your Claude API key (sk-ant-...):[/cyan] ").strip()
    if not key.startswith("sk-ant-"):
        console.print(
            "[yellow]Warning: key doesn't look like a Claude API key "
            "(expected sk-ant- prefix)[/yellow]"
        )
    keyring.set_password(KEYRING_SERVICE, KEYRING_CLAUDE_KEY, key)
    console.print("[green]Claude API key saved.[/green]\n")

    # Step 2: Check Gemini CLI
    console.print("[bold]Step 2: Gemini CLI[/bold]")
    gemini_ok = _check_gemini_installed(console)
    if gemini_ok:
        _check_gemini_auth(console)

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run [cyan]relayai status[/cyan] to verify everything is working.")


def _check_gemini_installed(console: Console) -> bool:
    try:
        result = subprocess.run(
            ["gemini", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = (result.stdout + result.stderr).strip()
            console.print(f"[green]Gemini CLI installed:[/green] {version}")
            return True
    except FileNotFoundError:
        pass
    except Exception:
        pass

    console.print("[red]Gemini CLI not found.[/red]")
    console.print("Install with: [cyan]npm install -g @google/gemini-cli[/cyan]")
    console.print("Then login:   [cyan]gemini[/cyan]")
    return False


def _check_gemini_auth(console: Console) -> bool:
    try:
        result = subprocess.run(
            ["gemini", "-p", "ping", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = (result.stdout + result.stderr).lower()
        if "auth" in combined or "login" in combined or "unauthorized" in combined or result.returncode != 0:
            console.print("[yellow]Gemini CLI not authenticated.[/yellow]")
            console.print(
                "Run [cyan]gemini[/cyan] in your terminal and log in with your Google account."
            )
            return False
        console.print("[green]Gemini CLI authenticated.[/green]")
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def clear_credentials():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_CLAUDE_KEY)
    except Exception:
        pass
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def show_status(console: Console):
    table = Table(title="RelayAI Status", border_style="cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status")

    # Claude API key
    claude_key = get_claude_key()
    if claude_key:
        table.add_row("Claude API Key", "[green]Configured[/green]")
    else:
        table.add_row("Claude API Key", "[red]Not configured[/red]  →  relayai login")

    # Gemini CLI installed
    gemini_installed = _gemini_installed()
    if gemini_installed:
        table.add_row("Gemini CLI", "[green]Installed[/green]")
    else:
        table.add_row(
            "Gemini CLI",
            "[red]Not installed[/red]  →  npm install -g @google/gemini-cli",
        )

    # Gemini CLI authenticated
    if gemini_installed:
        auth_ok = _gemini_auth_ok()
        if auth_ok:
            table.add_row("Gemini CLI Auth", "[green]Authenticated[/green]")
        else:
            table.add_row("Gemini CLI Auth", "[yellow]Not authenticated[/yellow]  →  run: gemini")
    else:
        table.add_row("Gemini CLI Auth", "[dim]N/A (Gemini CLI not installed)[/dim]")

    console.print()
    console.print(table)
    console.print()


def _gemini_installed() -> bool:
    try:
        result = subprocess.run(
            ["gemini", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _gemini_auth_ok() -> bool:
    try:
        result = subprocess.run(
            ["gemini", "-p", "ping", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = (result.stdout + result.stderr).lower()
        if "auth" in combined or "login" in combined or "unauthorized" in combined or result.returncode != 0:
            return False
        return True
    except Exception:
        return False
