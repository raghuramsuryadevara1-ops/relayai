import os
import json
import keyring
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

CONFIG_DIR = Path.home() / ".relayai"
CONFIG_FILE = CONFIG_DIR / "config.json"
SERVICE_NAME = "relayai"

GEMINI_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"
GEMINI_CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
GEMINI_SCOPES = ["https://www.googleapis.com/auth/generative-language"]


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
    CONFIG_FILE.chmod(0o600)


def is_configured() -> bool:
    config = _load_config()
    has_claude = bool(keyring.get_password(SERVICE_NAME, "claude_api_key"))
    has_gemini = (
        bool(keyring.get_password(SERVICE_NAME, "gemini_api_key")) or
        bool(keyring.get_password(SERVICE_NAME, "gemini_oauth_token"))
    )
    return has_claude and has_gemini


def get_claude_key() -> str:
    return keyring.get_password(SERVICE_NAME, "claude_api_key") or ""


def get_gemini_key() -> str:
    return keyring.get_password(SERVICE_NAME, "gemini_api_key") or ""


def get_gemini_oauth_token() -> str:
    return keyring.get_password(SERVICE_NAME, "gemini_oauth_token") or ""


def get_gemini_mode() -> str:
    config = _load_config()
    return config.get("gemini_mode", "api_key")


def setup_credentials(console: Console):
    console.print("\n[bold]Step 1: Claude Setup[/bold]")
    console.print("[dim]Get your API key from: https://console.anthropic.com[/dim]\n")

    claude_key = Prompt.ask("[cyan]Enter Claude API Key[/cyan]", password=True)
    if not claude_key.startswith("sk-ant-"):
        console.print("[red]⚠ That doesn't look like a valid Claude API key (should start with sk-ant-)[/red]")
        if not Confirm.ask("Continue anyway?"):
            return

    console.print("\n[bold]Step 2: Gemini Setup[/bold]")
    console.print("Choose how to connect Gemini:\n")
    console.print("  [bold cyan]1[/bold cyan]  API Key  [dim](from https://ai.google.dev — free tier)[/dim]")
    console.print("  [bold cyan]2[/bold cyan]  Google Account Login  [dim](OAuth — no key needed)[/dim]\n")

    choice = Prompt.ask("[cyan]Choose[/cyan]", choices=["1", "2"], default="1")

    config = _load_config()

    if choice == "1":
        gemini_key = Prompt.ask("[cyan]Enter Gemini API Key[/cyan]", password=True)
        keyring.set_password(SERVICE_NAME, "gemini_api_key", gemini_key)
        config["gemini_mode"] = "api_key"
        console.print("[green]✓ Gemini API key saved.[/green]")
    else:
        _google_oauth_login(console)
        config["gemini_mode"] = "oauth"

    keyring.set_password(SERVICE_NAME, "claude_api_key", claude_key)
    _save_config(config)
    console.print("\n[bold green]✓ RelayAI is ready! Try:[/bold green] [bold]relayai \"write a hello world in python\"[/bold]\n")


def _google_oauth_login(console: Console):
    """Perform Google OAuth flow for Gemini access."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        import json

        console.print("\n[dim]Opening browser for Google login...[/dim]")

        client_config = {
            "installed": {
                "client_id": GEMINI_CLIENT_ID,
                "client_secret": GEMINI_CLIENT_SECRET,
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, GEMINI_SCOPES)
        creds = flow.run_local_server(port=0)

        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
        }
        keyring.set_password(SERVICE_NAME, "gemini_oauth_token", json.dumps(token_data))
        console.print("[green]✓ Google account connected successfully.[/green]")

    except ImportError:
        console.print("[red]Missing dependency. Run: pip install google-auth-oauthlib[/red]")
    except Exception as e:
        console.print(f"[red]OAuth failed: {e}[/red]")
        console.print("[dim]Tip: You can also use a Gemini API key instead (option 1).[/dim]")


def clear_credentials():
    for key in ["claude_api_key", "gemini_api_key", "gemini_oauth_token"]:
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except Exception:
            pass
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def show_status(console: Console):
    config = _load_config()
    table = Table(title="RelayAI Status", border_style="cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    claude_key = get_claude_key()
    if claude_key:
        table.add_row("Claude", "[green]✓ Connected[/green]", f"API Key: ...{claude_key[-6:]}")
    else:
        table.add_row("Claude", "[red]✗ Not configured[/red]", "Run: relayai login")

    gemini_mode = config.get("gemini_mode", "not set")
    if gemini_mode == "api_key" and get_gemini_key():
        key = get_gemini_key()
        table.add_row("Gemini", "[green]✓ Connected[/green]", f"API Key: ...{key[-6:]}")
    elif gemini_mode == "oauth" and get_gemini_oauth_token():
        table.add_row("Gemini", "[green]✓ Connected[/green]", "Google OAuth")
    else:
        table.add_row("Gemini", "[red]✗ Not configured[/red]", "Run: relayai login")

    console.print()
    console.print(table)
    console.print()
