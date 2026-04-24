import os
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# <<<FILE:CREATE|EDIT|DELETE:path>>> ... <<<END_FILE>>>
FILE_OP_PATTERN = re.compile(
    r"<<<FILE:(CREATE|EDIT|DELETE):([^>]+)>>>\n(.*?)<<<END_FILE>>>",
    re.DOTALL,
)

# <<<RUN:command here>>>  (single-line, no closing tag needed)
RUN_PATTERN = re.compile(r"<<<RUN:(.+?)>>>")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_file_operations(output: str) -> list:
    """Return list of {action, path, content} dicts from file-op markers."""
    operations = []
    for match in FILE_OP_PATTERN.finditer(output):
        action = match.group(1)
        path = match.group(2).strip()
        content = match.group(3).strip()
        operations.append({
            "action": action,
            "path": path,
            "content": content if action != "DELETE" else None,
        })
    return operations


def parse_run_commands(output: str) -> list:
    """Return list of command strings from RUN markers."""
    return [m.group(1).strip() for m in RUN_PATTERN.finditer(output)]


def strip_file_ops(output: str) -> str:
    """Remove all file-op and run markers, return plain explanation text."""
    text = FILE_OP_PATTERN.sub("", output)
    text = RUN_PATTERN.sub("", text)
    return text.strip()


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def preview_operations(operations: list):
    console.print()
    table = Table(title="Planned File Operations", border_style="cyan", show_lines=True)
    table.add_column("Action", style="bold", width=8)
    table.add_column("File Path")
    table.add_column("Size")

    for op in operations:
        action = op["action"]
        size = f"{len(op['content'])} chars" if op["content"] else "-"
        style = {
            "CREATE": "[bold green]CREATE[/bold green]",
            "EDIT":   "[bold yellow]EDIT[/bold yellow]",
            "DELETE": "[bold red]DELETE[/bold red]",
        }.get(action, action)
        table.add_row(style, op["path"], size)

    console.print(table)
    console.print()


def preview_file_content(op: dict):
    if not op["content"]:
        return
    ext = Path(op["path"]).suffix.lstrip(".")
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
        "json": "json", "yaml": "yaml", "yml": "yaml", "md": "markdown",
        "sh": "bash", "sql": "sql", "go": "go", "rs": "rust",
    }
    syntax = Syntax(
        op["content"],
        lang_map.get(ext, "text"),
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )
    console.print(Panel(syntax, title=f"[bold]{op['path']}[/bold]", border_style="cyan"))


def confirm_and_execute(operations: list) -> bool:
    """Preview, confirm, and write file operations. Returns True if all succeeded."""
    if not operations:
        return True

    preview_operations(operations)

    if any(op["content"] for op in operations):
        if Confirm.ask("[dim]Preview file contents before writing?[/dim]", default=False):
            for op in operations:
                if op["content"]:
                    preview_file_content(op)

    console.print()
    if not Confirm.ask(
        f"[bold cyan]Proceed with {len(operations)} file operation(s)?[/bold cyan]",
        default=True,
    ):
        console.print("[dim]Cancelled. No files were changed.[/dim]")
        return False

    success = True
    for op in operations:
        if not _execute_operation(op):
            success = False

    console.print()
    return success


def _execute_operation(op: dict) -> bool:
    action = op["action"]
    path = Path(op["path"])
    try:
        if action in ("CREATE", "EDIT"):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(op["content"])
            icon = "+" if action == "CREATE" else "~"
            console.print(f"  [{icon}] [green]{action}[/green] {path}")
            return True

        elif action == "DELETE":
            if path.exists():
                os.remove(path)
                console.print(f"  [-] [red]DELETED[/red] {path}")
            else:
                console.print(f"  [yellow]File not found, skipping delete: {path}[/yellow]")
            return True

    except Exception as exc:
        console.print(f"  [red]Failed {action} {path}: {exc}[/red]")
        return False


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

def confirm_and_run(commands: list) -> bool:
    """For each RUN command: show it, ask confirmation, stream output live.
    Returns True if all confirmed commands exited with code 0."""
    if not commands:
        return True

    all_ok = True
    for command in commands:
        console.print()
        console.print(
            Panel(
                f"[bold yellow]{command}[/bold yellow]",
                title="[bold]Command[/bold]",
                border_style="yellow",
            )
        )

        if not Confirm.ask("Run this command?", default=True):
            console.print("[dim]Skipped.[/dim]")
            continue

        console.print()
        ok = _run_command(command)
        console.print()
        if ok:
            console.print("[green]Command succeeded.[/green]")
        else:
            console.print("[red]Command failed.[/red]")
            all_ok = False

    return all_ok


def _run_command(command: str) -> bool:
    """Execute command via shell, stream stdout+stderr live. Returns True on exit 0."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,          # lets the shell parse pip install x y, python main.py, etc.
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr so output appears in order
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in process.stdout:
            try:
                sys.stdout.write(line)
            except UnicodeEncodeError:
                sys.stdout.write(
                    line.encode(sys.stdout.encoding, errors="replace")
                        .decode(sys.stdout.encoding)
                )
            sys.stdout.flush()

        process.wait()
        return process.returncode == 0

    except Exception as exc:
        console.print(f"[red]Error running command: {exc}[/red]")
        return False
