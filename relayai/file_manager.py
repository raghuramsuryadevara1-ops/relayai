import re
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm
from rich.table import Table

console = Console()

# Markers Claude uses to wrap file operations
FILE_OP_PATTERN = re.compile(
    r"<<<FILE:(CREATE|EDIT|DELETE):([^>]+)>>>\n(.*?)<<<END_FILE>>>",
    re.DOTALL
)


def parse_file_operations(claude_output: str) -> list:
    """
    Parse Claude's output for file operation blocks.
    Returns list of operations: [{action, path, content}]
    """
    operations = []
    for match in FILE_OP_PATTERN.finditer(claude_output):
        action = match.group(1)
        path = match.group(2).strip()
        content = match.group(3).strip()
        operations.append({
            "action": action,
            "path": path,
            "content": content if action != "DELETE" else None
        })
    return operations


def strip_file_ops(claude_output: str) -> str:
    """Remove file operation blocks from output, keep explanation text."""
    return FILE_OP_PATTERN.sub("", claude_output).strip()


def preview_operations(operations: list):
    """Show user a summary of what will be created/edited/deleted."""
    console.print()

    table = Table(title="📁 Planned File Operations", border_style="cyan", show_lines=True)
    table.add_column("Action", style="bold", width=8)
    table.add_column("File Path")
    table.add_column("Size")

    for op in operations:
        action = op["action"]
        path = op["path"]
        size = f"{len(op['content'])} chars" if op["content"] else "-"

        if action == "CREATE":
            style = "[bold green]CREATE[/bold green]"
        elif action == "EDIT":
            style = "[bold yellow]EDIT[/bold yellow]"
        elif action == "DELETE":
            style = "[bold red]DELETE[/bold red]"
        else:
            style = action

        table.add_row(style, path, size)

    console.print(table)
    console.print()


def preview_file_content(op: dict):
    """Show a syntax-highlighted preview of file content."""
    if not op["content"]:
        return

    ext = Path(op["path"]).suffix.lstrip(".")
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
        "json": "json", "yaml": "yaml", "yml": "yaml", "md": "markdown",
        "sh": "bash", "sql": "sql", "go": "go", "rs": "rust",
    }
    lang = lang_map.get(ext, "text")

    syntax = Syntax(
        op["content"],
        lang,
        theme="monokai",
        line_numbers=True,
        word_wrap=True
    )
    console.print(Panel(syntax, title=f"[bold]{op['path']}[/bold]", border_style="cyan"))


def confirm_and_execute(operations: list) -> bool:
    """
    Show preview, ask for confirmation, then execute file operations.
    Returns True if all operations succeeded.
    """
    if not operations:
        return True

    preview_operations(operations)

    # Ask if user wants to preview file contents
    if any(op["content"] for op in operations):
        if Confirm.ask("[dim]Preview file contents before writing?[/dim]", default=False):
            for op in operations:
                if op["content"]:
                    preview_file_content(op)

    # Final confirmation
    console.print()
    if not Confirm.ask(f"[bold cyan]Proceed with {len(operations)} file operation(s)?[/bold cyan]", default=True):
        console.print("[dim]Cancelled. No files were changed.[/dim]")
        return False

    # Execute operations
    success = True
    for op in operations:
        result = _execute_operation(op)
        if not result:
            success = False

    console.print()
    return success


def _execute_operation(op: dict) -> bool:
    """Execute a single file operation."""
    action = op["action"]
    path = Path(op["path"])

    try:
        if action in ("CREATE", "EDIT"):
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(op["content"])

            icon = "✨" if action == "CREATE" else "✏️"
            console.print(f"  {icon} [green]{action}[/green] {path}")
            return True

        elif action == "DELETE":
            if path.exists():
                os.remove(path)
                console.print(f"  🗑️  [red]DELETED[/red] {path}")
            else:
                console.print(f"  [yellow]⚠ File not found, skipping delete: {path}[/yellow]")
            return True

    except Exception as e:
        console.print(f"  [red]❌ Failed {action} {path}: {e}[/red]")
        return False
