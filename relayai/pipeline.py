from typing import Optional

from rich.console import Console
from rich.panel import Panel

from . import claude_client, gemini_bridge, file_manager, project_scanner

console = Console()


def run(
    query: str,
    history: list,
    file_content: Optional[dict] = None,
    piped_content: Optional[str] = None,
    scan_project: bool = True,
) -> Optional[str]:
    """Main pipeline: Claude plans → Gemini 3 Flash implements.

    Returns the plan text for history tracking, or None on error.
    """
    # Scan project context
    project_context = ""
    if scan_project:
        with console.status("[dim]Scanning project...[/dim]", spinner="dots"):
            try:
                project = project_scanner.scan_project(".")
                project_context = project_scanner.format_for_claude(project)
            except Exception:
                pass

    # Build full query
    full_query = _build_query(query, file_content, piped_content)

    # Claude plans
    with console.status("[bold cyan]Claude is planning...[/bold cyan]", spinner="dots"):
        try:
            plan, input_tokens, output_tokens = claude_client.think(
                full_query, history, project_context
            )
        except Exception as exc:
            console.print(f"\n[red]Claude error: {exc}[/red]")
            if any(w in str(exc).lower() for w in ("authentication", "api_key", "unauthorized")):
                console.print("[dim]Check your Claude API key with: relayai status[/dim]")
            return None

    # Display plan in dim panel
    console.print(
        Panel(
            f"[dim]{plan}[/dim]",
            title=f"[bold]Claude's plan ({output_tokens} tokens)[/bold]",
            border_style="dim",
        )
    )

    # Gemini implements
    console.print("\n[bold cyan]Gemini 3 Flash implementing...[/bold cyan]\n")
    gemini_output = gemini_bridge.execute(plan)

    # Parse file operations from Gemini output and write them
    operations = file_manager.parse_file_operations(gemini_output)
    if operations:
        file_manager.confirm_and_execute(operations)

    # Cost summary
    _show_cost_summary(input_tokens, output_tokens, gemini_output)

    return plan


def _build_query(
    query: str,
    file_content: Optional[dict],
    piped_content: Optional[str],
) -> str:
    parts = []
    if query:
        parts.append(query)
    if file_content:
        lang = file_content.get("extension", "")
        parts.append(
            f"\n--- File: {file_content['name']} ---\n"
            f"```{lang}\n{file_content['content']}\n```"
        )
    if piped_content:
        parts.append(f"\n--- Piped content ---\n```\n{piped_content}\n```")
    return "\n".join(parts)


def _show_cost_summary(input_tokens: int, output_tokens: int, gemini_output: str):
    actual_cost = claude_client.estimate_cost(input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens

    # Savings: compare actual cost vs if Claude had generated the full implementation
    estimated_gemini_tokens = max(len(gemini_output) // 4, 1)
    hypothetical_output_cost = estimated_gemini_tokens * 15.0 / 1_000_000
    hypothetical_total = (input_tokens * 3.0 / 1_000_000) + hypothetical_output_cost
    saved_pct = max(0, int((1 - actual_cost / hypothetical_total) * 100)) if hypothetical_total > actual_cost else 80

    console.print()
    console.print(f"  [blue]🧠 Claude:[/blue] ${actual_cost:.5f} ({total_tokens} tokens — plan only)")
    console.print(f"  [green]⚡ Gemini 3 Flash:[/green] FREE")
    console.print(f"  [yellow]💰 Saved:[/yellow] ~{saved_pct}% vs direct Claude output")
