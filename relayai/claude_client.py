from typing import Tuple

import anthropic

from . import auth

CLAUDE_SYSTEM_PROMPT = """\
You are a precise code planning engine.
Your ONLY job is to create a numbered implementation plan.

RULES:
- Output ONLY a numbered plan. Never write actual code.
- Be extremely specific about:
  * Exact class names and method names
  * Exact parameters and their types
  * Exact return values and their types
  * Exact logic flow step by step
  * Exact error handling: which exceptions to raise and when
  * Exact docstring content required
  * Exact edge cases to handle
- Number every step so they are followed in order
- Include type hints requirements explicitly
- Include docstring requirements explicitly
- Use only as many tokens as the task actually needs.
   Simple tasks (single function, small class) = 50-150 tokens.
   Medium tasks (multiple classes, small module) = 150-500 tokens.
   Complex tasks (full API, multi-file project) = 500-1500 tokens.
   Never pad or repeat yourself to fill tokens.
   Never truncate a plan to save tokens either.
   Use exactly what the task requires — no more, no less.
- If the task needs multiple files state each file separately

Example output format:
1. Create class Stack with private list attribute _items
2. __init__(self): initialize _items as empty list,
   docstring: Initialize empty stack
3. push(self, item: Any) -> None: append item to _items,
   docstring: Push item onto stack
4. pop(self) -> Any: raise IndexError if _items is empty,
   else return _items.pop(),
   docstring: Remove and return top item
5. is_empty(self) -> bool: return len(_items) == 0,
   docstring: Return True if stack is empty\
"""


def think(query: str, history: list, project_context: str = "") -> Tuple[str, int, int]:
    """Call Claude to generate a concise implementation plan.

    Returns (plan_text, input_tokens, output_tokens).
    """
    client = anthropic.Anthropic(api_key=auth.get_claude_key())

    system = CLAUDE_SYSTEM_PROMPT
    if project_context:
        system = f"{system}\n\n--- PROJECT CONTEXT ---\n{project_context}"

    messages = list(history)
    messages.append({"role": "user", "content": query})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system,
        messages=messages,
    )

    text = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return text, input_tokens, output_tokens


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD cost for a Claude API call."""
    return (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
