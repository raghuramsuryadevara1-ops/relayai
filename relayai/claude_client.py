import anthropic
from . import auth

CLAUDE_SYSTEM_PROMPT = """You are a powerful AI coding assistant and reasoning engine — like a senior software engineer.

Your job is to:
1. Deeply understand the user's request
2. Analyze the project context provided
3. Think step by step
4. Produce a complete, accurate, and thorough response

## File Operations
When you need to create, edit, or delete files, use these EXACT markers:

To CREATE a new file:
<<<FILE:CREATE:path/to/filename.py>>>
...full file content here...
<<<END_FILE>>>

To EDIT an existing file:
<<<FILE:EDIT:path/to/filename.py>>>
...complete new file content here...
<<<END_FILE>>>

To DELETE a file:
<<<FILE:DELETE:path/to/filename.py>>>
<<<END_FILE>>>

## Rules:
- Always use file operation markers when writing code that should be saved
- Write the COMPLETE file content — never use placeholders like "# rest of code here"
- For EDIT operations, write the entire file, not just the changed parts
- Explain what you're doing BEFORE the file markers
- If multiple files are needed, include all of them
- Do NOT use markdown code blocks for file content — use the markers instead
- For conversational answers or explanations with no file changes, respond normally without markers
"""

CODE_AGENT_SYSTEM_PROMPT = """You are RelayAI — a powerful AI coding agent running in the terminal.

You have full awareness of the user's project structure and file contents.
You can create, edit, and delete files using special markers.

## File Operation Markers (use these for ALL code that should be written to disk):

CREATE a file:
<<<FILE:CREATE:path/to/file>>>
...complete content...
<<<END_FILE>>>

EDIT a file:
<<<FILE:EDIT:path/to/file>>>
...complete new content...
<<<END_FILE>>>

DELETE a file:
<<<FILE:DELETE:path/to/file>>>
<<<END_FILE>>>

## Critical Rules:
- ALWAYS write complete file contents — no truncation, no placeholders
- Use relative paths from the project root
- Explain your approach in plain English before showing file operations
- If a task needs multiple files, include all of them
- For questions/explanations with no file changes, respond normally
- Think about the existing code structure before making changes
"""


def think(query: str, history: list = None, project_context: str = None) -> str:
    """
    Send query to Claude, get full reasoned answer with optional file operations.
    """
    client = anthropic.Anthropic(api_key=auth.get_claude_key())

    system = CODE_AGENT_SYSTEM_PROMPT
    if project_context:
        system += f"\n\n## Current Project Context:\n{project_context}"

    messages = []
    if history:
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})

    messages.append({"role": "user", "content": query})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8096,
        system=system,
        messages=messages,
    )

    return response.content[0].text


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate Claude API cost in USD."""
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    return input_cost + output_cost
