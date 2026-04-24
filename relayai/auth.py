import json
import shutil
import subprocess
import sys
from pathlib import Path

import keyring
from rich.console import Console
from rich.table import Table

CONFIG_DIR = Path.home() / ".relayai"
CONFIG_FILE = CONFIG_DIR / "config.json"
KEYRING_SERVICE = "relayai"
KEYRING_CLAUDE_KEY = "claude_api_key"


def _gemini_exe() -> str:
    """Resolve the gemini executable — handles gemini.cmd on Windows and
    varied npm global bin locations on macOS/Linux."""
    return shutil.which("gemini") or "gemini"


# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------

def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_config(data: dict):
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    # Restrict to owner-only on macOS/Linux (config may hold fallback keys)
    if sys.platform != "win32":
        CONFIG_FILE.chmod(0o600)


# ---------------------------------------------------------------------------
# Keyring with config-file fallback
# On headless Linux (no GNOME/KDE keyring daemon) keyring raises
# NoKeyringError or similar — we fall back to the config file and warn once.
# ---------------------------------------------------------------------------

def _keyring_get(key: str) -> str:
    try:
        value = keyring.get_password(KEYRING_SERVICE, key)
        return value or ""
    except Exception:
        return _load_config().get(key, "")


def _keyring_set(key: str, value: str, console: Console = None):
    try:
        keyring.set_password(KEYRING_SERVICE, key, value)
    except Exception:
        if console:
            console.print(
                "[yellow]No keyring backend found (common on headless Linux). "
                "Storing key in ~/.relayai/config.json instead.[/yellow]"
            )
        config = _load_config()
        config[key] = value
        _save_config(config)


def _keyring_delete(key: str):
    try:
        keyring.delete_password(KEYRING_SERVICE, key)
    except Exception:
        pass
    # Also wipe from config-file fallback
    config = _load_config()
    if key in config:
        del config[key]
        _save_config(config)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    return bool(get_claude_key())


def get_claude_key() -> str:
    return _keyring_get(KEYRING_CLAUDE_KEY)


def setup_credentials(console: Console):
    console.print("[bold]Step 1: Claude API Key[/bold]")
    console.print("[dim]Get your key from: https://console.anthropic.com[/dim]\n")

    key = console.input("[cyan]Enter your Claude API key (sk-ant-...):[/cyan] ").strip()
    if not key.startswith("sk-ant-"):
        console.print(
            "[yellow]Warning: key doesn't look like a Claude API key "
            "(expected sk-ant- prefix)[/yellow]"
        )
    _keyring_set(KEYRING_CLAUDE_KEY, key, console)
    console.print("[green]Claude API key saved.[/green]\n")

    console.print("[bold]Step 2: Gemini CLI[/bold]")
    gemini_ok = _check_gemini_installed(console)
    if gemini_ok:
        _check_gemini_auth(console)

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run [cyan]relayai status[/cyan] to verify everything is working.")


def clear_credentials():
    _keyring_delete(KEYRING_CLAUDE_KEY)
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def show_status(console: Console):
    table = Table(title="RelayAI Status", border_style="cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status")

    claude_key = get_claude_key()
    if claude_key:
        table.add_row("Claude API Key", "[green]Configured[/green]")
    else:
        table.add_row("Claude API Key", "[red]Not configured[/red]  ->  relayai login")

    gemini_installed = _gemini_installed()
    if gemini_installed:
        table.add_row("Gemini CLI", "[green]Installed[/green]")
    else:
        table.add_row(
            "Gemini CLI",
            "[red]Not installed[/red]  ->  npm install -g @google/gemini-cli",
        )

    if gemini_installed:
        if _gemini_auth_ok():
            table.add_row("Gemini CLI Auth", "[green]Authenticated[/green]")
        else:
            table.add_row("Gemini CLI Auth", "[yellow]Not authenticated[/yellow]  ->  run: gemini")
    else:
        table.add_row("Gemini CLI Auth", "[dim]N/A (Gemini CLI not installed)[/dim]")

    console.print()
    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Gemini CLI checks — explicit UTF-8 encoding on all subprocess calls
# so non-UTF-8 system locales (some Linux distros) don't cause failures.
# ---------------------------------------------------------------------------

def _check_gemini_installed(console: Console) -> bool:
    try:
        result = subprocess.run(
            [_gemini_exe(), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
            [_gemini_exe(), "-p", "ping", "--output-format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        combined = (result.stdout + result.stderr).lower()
        if any(w in combined for w in ("auth", "login", "unauthorized")) or result.returncode != 0:
            console.print("[yellow]Gemini CLI not authenticated.[/yellow]")
            console.print(
                "Run [cyan]gemini[/cyan] in your terminal and log in with your Google account."
            )
            return False
        console.print("[green]Gemini CLI authenticated.[/green]")
        return True
    except Exception:
        return False


def _gemini_installed() -> bool:
    try:
        result = subprocess.run(
            [_gemini_exe(), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _gemini_auth_ok() -> bool:
    try:
        result = subprocess.run(
            [_gemini_exe(), "-p", "ping", "--output-format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        combined = (result.stdout + result.stderr).lower()
        if any(w in combined for w in ("auth", "login", "unauthorized")) or result.returncode != 0:
            return False
        return True
    except Exception:
        return False
