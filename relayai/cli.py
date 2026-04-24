import os
import sys

import click
from rich.console import Console

console = Console()

BANNER = """[bold cyan]
██████╗ ███████╗██╗      █████╗ ██╗   ██╗ █████╗ ██╗
██╔══██╗██╔════╝██║     ██╔══██╗╚██╗ ██╔╝██╔══██╗██║
██████╔╝█████╗  ██║     ███████║ ╚████╔╝ ███████║██║
██╔══██╗██╔══╝  ██║     ██╔══██║  ╚██╔╝  ██╔══██║██║
██║  ██║███████╗███████╗██║  ██║   ██║   ██║  ██║██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝
[/bold cyan][dim]Claude thinks. Gemini 3 Flash speaks.[/dim]
"""

_SUBCOMMANDS = frozenset({"login", "logout", "status"})


@click.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--chat", "-c", is_flag=True, help="Start interactive chat mode")
@click.option("--file", "-f", "file_path", default=None, help="Attach a file to your query")
def cli(args, chat, file_path):
    """RelayAI — Claude plans. Gemini 3 Flash speaks.

    \b
    relayai "write a FastAPI server"   single query
    relayai --chat                     interactive mode
    relayai --file main.py "fix bug"   attach a file
    relayai login                      set up credentials
    relayai status                     show config
    relayai logout                     clear credentials
    """
    args = list(args)

    # Named subcommands — dispatch manually so nargs=-1 never swallows them
    if args and args[0] in _SUBCOMMANDS:
        _dispatch_subcommand(args[0])
        return

    from . import auth, pipeline

    if not auth.is_configured():
        console.print("[yellow]Not configured. Run:[/yellow] [cyan]relayai login[/cyan]")
        sys.exit(1)

    # Detect piped stdin
    piped_content = None
    if not sys.stdin.isatty():
        piped_content = sys.stdin.read().strip() or None

    # Auto-detect file path as last positional argument
    if args and not file_path:
        last = args[-1]
        if os.path.isfile(last):
            file_path = last
            args = args[:-1]

    file_content = _read_file(file_path) if file_path else None

    if chat:
        interactive_mode(file_content, piped_content)
        return

    if not args and not piped_content and not file_content:
        console.print(BANNER)
        console.print('Usage: [cyan]relayai "your query"[/cyan]  or  [cyan]relayai --chat[/cyan]')
        return

    query = " ".join(args)
    pipeline.run(
        query=query,
        history=[],
        file_content=file_content,
        piped_content=piped_content,
        scan_project=True,
    )


def _dispatch_subcommand(name: str):
    from . import auth

    if name == "login":
        console.print(BANNER)
        auth.setup_credentials(console)

    elif name == "status":
        auth.show_status(console)

    elif name == "logout":
        auth.clear_credentials()
        console.print("[green]Credentials cleared.[/green]")


def interactive_mode(file_content=None, piped_content=None):
    from . import pipeline

    console.print(BANNER)
    console.print("[dim]Interactive mode — type 'quit' to exit.[/dim]\n")

    history = []
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        plan = pipeline.run(
            query=user_input,
            history=history,
            file_content=file_content,
            piped_content=piped_content,
            scan_project=len(history) == 0,
        )
        if plan:
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": plan})

        # File and pipe content only apply to the first turn
        file_content = None
        piped_content = None


def _read_file(file_path: str):
    MAX_SIZE = 100 * 1024  # 100 KB
    ext = os.path.splitext(file_path)[1].lstrip(".")
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_SIZE)
        return {"name": os.path.basename(file_path), "content": content, "extension": ext}
    except Exception as exc:
        console.print(f"[red]Could not read file {file_path}: {exc}[/red]")
        return None


def main():
    cli()
