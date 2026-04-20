import time
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from . import claude_client, gemini_client, file_manager, project_scanner

console = Console()


def run(query: str, verbose: bool = False, history: list = None,
        file_content: dict = None, piped_content: str = None, scan_project: bool = True):
    """
    Main RelayAI pipeline:
    1. Scan project context
    2. Claude thinks (with file op markers in output)
    3. Parse file operations from Claude's output
    4. Pass explanation to Gemini for presentation
    5. Confirm and execute file operations
    """
    start_time = time.time()

    # Step 1: Scan project
    project_context = None
    if scan_project:
        with console.status("[dim]📂 Scanning project...[/dim]", spinner="dots"):
            try:
                project = project_scanner.scan_project(".")
                project_context = project_scanner.format_for_claude(project)
                console.print(
                    f"[dim]📂 Project: {project['name']} ({project['type']}) "
                    f"| {len(project['files'])} files scanned[/dim]"
                )
            except Exception:
                pass

    # Step 2: Build full query
    full_query = _build_query(query, file_content, piped_content)

    # Step 3: Claude thinks
    claude_output = None
    with console.status("[bold cyan]🧠 Claude is thinking...[/bold cyan]", spinner="dots"):
        try:
            claude_output = claude_client.think(
                full_query,
                history=history,
                project_context=project_context
            )
        except Exception as e:
            console.print(f"\n[red]❌ Claude error: {e}[/red]")
            _claude_key_hint(str(e))
            return

    if verbose:
        console.print(Panel(claude_output, title="[dim]Claude's Raw Output[/dim]", border_style="dim"))

    # Step 4: Parse file operations from Claude's output
    operations = file_manager.parse_file_operations(claude_output)
    explanation = file_manager.strip_file_ops(claude_output)

    # Step 5: Gemini presents the explanation
    if explanation.strip():
        gemini_output = None
        with console.status("[bold magenta]⚡ Gemini is responding...[/bold magenta]", spinner="dots"):
            try:
                gemini_output = gemini_client.speak(explanation, full_query)
            except Exception as e:
                console.print(f"\n[red]❌ Gemini error: {e}[/red]")
                _gemini_key_hint(str(e))

        if gemini_output:
            console.print()
            console.print(Markdown(gemini_output))

    # Step 6: Confirm and execute file operations
    if operations:
        file_manager.confirm_and_execute(operations)

    elapsed = time.time() - start_time
    console.print()
    _show_cost_summary(full_query, claude_output, elapsed, len(operations))


def _build_query(query: str, file_content: dict = None, piped_content: str = None) -> str:
    parts = []
    if query:
        parts.append(query)
    if file_content:
        lang = file_content["extension"].lstrip(".") or "text"
        parts.append(f"\n--- File: {file_content['name']} ---\n```{lang}\n{file_content['content']}\n```")
    if piped_content:
        parts.append(f"\n--- Piped Content ---\n```\n{piped_content}\n```")
    return "\n".join(parts)


def _show_cost_summary(query: str, claude_output: str, elapsed: float, file_ops: int = 0):
    input_tokens = len(query) // 4
    claude_output_tokens = len(claude_output) // 4
    normal_cost = claude_client.estimate_cost(input_tokens, claude_output_tokens)
    actual_cost = claude_client.estimate_cost(input_tokens, claude_output_tokens // 10)
    savings_pct = int(((normal_cost - actual_cost) / normal_cost) * 100) if normal_cost > 0 else 0
    file_ops_str = f"| 📁 {file_ops} file(s) written " if file_ops else ""
    console.print(
        f"[dim]⏱ {elapsed:.1f}s  |  🧠 Claude: ${actual_cost:.5f}  |  "
        f"⚡ Gemini: [green]FREE[/green]  |  {file_ops_str}💰 Saved: ~{savings_pct}%[/dim]"
    )


def _claude_key_hint(error: str):
    if any(w in error.lower() for w in ["authentication", "api_key", "unauthorized"]):
        console.print("[dim]Tip: Check your Claude API key with [bold]relayai status[/bold][/dim]")


def _gemini_key_hint(error: str):
    if any(w in error.lower() for w in ["api_key", "credentials", "unauthorized"]):
        console.print("[dim]Tip: Check your Gemini key with [bold]relayai status[/bold][/dim]")
