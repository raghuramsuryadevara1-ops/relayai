import click
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from . import auth, pipeline

console = Console()

BANNER = """
[bold cyan]
██████╗ ███████╗██╗      █████╗ ██╗   ██╗ █████╗ ██╗
██╔══██╗██╔════╝██║     ██╔══██╗╚██╗ ██╔╝██╔══██╗██║
██████╔╝█████╗  ██║     ███████║ ╚████╔╝ ███████║██║
██╔══██╗██╔══╝  ██║     ██╔══██║  ╚██╔╝  ██╔══██║██║
██║  ██║███████╗███████╗██║  ██║   ██║   ██║  ██║██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝
[/bold cyan]
[dim]Claude thinks. Gemini speaks. You save.[/dim]
"""

@click.group(invoke_without_command=True)
@click.argument("prompt", required=False, nargs=-1)
@click.option("--chat", "-c", is_flag=True, help="Start interactive chat mode")
@click.option("--verbose", "-v", is_flag=True, help="Show Claude's internal plan")
@click.option("--file", "-f", "file_path", default=None, help="Attach a file to your query")
@click.pass_context
def cli(ctx, prompt, chat, verbose, file_path):
    """RelayAI - Claude plans, Gemini speaks. Save up to 80% on API costs."""
    if ctx.invoked_subcommand:
        return

    if not auth.is_configured():
        console.print("\n[yellow]⚠ Not configured yet. Run:[/yellow] [bold]relayai login[/bold]\n")
        return

    if chat:
        interactive_mode(verbose)
        return

    # Read from stdin pipe (cat file.py | relayai "review this")
    piped_content = None
    if not sys.stdin.isatty():
        piped_content = sys.stdin.read().strip()

    # Auto-detect if last argument is a file path
    prompt_list = list(prompt)
    if prompt_list and not file_path:
        last_arg = prompt_list[-1]
        if os.path.isfile(last_arg):
            file_path = last_arg
            prompt_list = prompt_list[:-1]

    if prompt_list or piped_content or file_path:
        query = " ".join(prompt_list) if prompt_list else ""
        file_content = _read_file(file_path) if file_path else None
        pipeline.run(query, verbose=verbose, file_content=file_content, piped_content=piped_content)
    else:
        console.print(BANNER)
        console.print("[dim]Usage:[/dim] [bold]relayai[/bold] [cyan]\"your question here\"[/cyan]")
        console.print("[dim]      [/dim] [bold]relayai --file main.py[/bold] [cyan]\"fix this code\"[/cyan]")
        console.print("[dim]      [/dim] [bold]relayai --chat[/bold]   [dim]for interactive mode[/dim]\n")


def _read_file(file_path: str) -> dict:
    """Read a file and return its content with metadata."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        return None

    # Check file size (limit to 100KB)
    size = path.stat().st_size
    if size > 100_000:
        console.print(f"[yellow]⚠ File is large ({size // 1000}KB). Only first 100KB will be used.[/yellow]")

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(100_000)
        console.print(f"[dim]📎 Attached: {path.name} ({len(content.splitlines())} lines)[/dim]")
        return {"name": path.name, "content": content, "extension": path.suffix}
    except Exception as e:
        console.print(f"[red]❌ Could not read file: {e}[/red]")
        return None


@cli.command()
def login():
    """Configure your Claude and Gemini credentials."""
    console.print(BANNER)
    console.print(Panel("[bold]Setup RelayAI[/bold]\nConfigure your Claude and Gemini access.", border_style="cyan"))
    auth.setup_credentials(console)


@cli.command()
def logout():
    """Remove saved credentials."""
    auth.clear_credentials()
    console.print("[green]✓ Credentials cleared.[/green]")


@cli.command()
def status():
    """Show current configuration status."""
    auth.show_status(console)


@cli.command()
def version():
    """Show RelayAI version."""
    console.print("[bold cyan]RelayAI[/bold cyan] v1.0.0")


def interactive_mode(verbose=False):
    """Start an interactive REPL session."""
    console.print(BANNER)
    console.print(Panel(
        "[bold cyan]Interactive Mode[/bold cyan]\n"
        "[dim]Type your questions below. Type [bold]exit[/bold] or [bold]quit[/bold] to stop.[/dim]",
        border_style="cyan"
    ))
    history = []
    while True:
        try:
            query = console.input("\n[bold cyan]You >[/bold cyan] ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                console.print("\n[dim]Goodbye! 👋[/dim]\n")
                break
            pipeline.run(query, verbose=verbose, history=history)
            history.append({"role": "user", "content": query})
        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrupted. Goodbye! 👋[/dim]\n")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
