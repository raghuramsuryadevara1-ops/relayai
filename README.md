# RelayAI v2.0

Claude thinks. Gemini 3 Flash speaks.
Save up to 80% on AI API costs.

## How it works

- You type a query in terminal
- Claude generates a short precise plan
- Gemini 3 Flash CLI implements it fully
- You get production ready code for free

```
User query
    ↓
Claude API → short numbered plan (300-400 tokens)
    ↓
Gemini CLI streams full implementation to terminal
    ↓
Files written to disk
```

## Requirements

- Python 3.9+
- Node.js + npm (for Gemini CLI)
- Claude API key

## Install

```bash
pip install relayai
npm install -g @google/gemini-cli
```

## Setup

```bash
relayai login
```

You will be prompted for your Claude API key.
Then the setup checks that Gemini CLI is installed and authenticated.

To authenticate Gemini CLI:

```bash
gemini
```

Log in with your Google account when prompted. Gemini CLI is free (1000 requests/day).

## Use

```bash
# Single query
relayai "write a FastAPI server with /health endpoint"

# Attach a file
relayai "fix the bug" --file main.py

# Auto-detect file as last argument
relayai "review this code" main.py

# Pipe content
cat main.py | relayai "explain this"

# Interactive mode
relayai --chat

# Check configuration
relayai status

# Clear credentials
relayai logout
```

## Cost comparison

| | Direct Claude | RelayAI |
|---|---|---|
| Planning | Claude | Claude (~400 tokens) |
| Implementation | Claude ($15/M tokens) | Gemini CLI (FREE) |
| Per query savings | — | ~80% |

## Project structure

```
relayai/
├── relayai/
│   ├── cli.py             # Terminal commands
│   ├── auth.py            # Credential management
│   ├── claude_client.py   # Claude planning engine
│   ├── gemini_bridge.py   # Gemini CLI subprocess bridge
│   ├── pipeline.py        # Main orchestration
│   ├── file_manager.py    # Parse and write files
│   └── project_scanner.py # Scan project for context
├── .gemini/
│   └── system.md          # Gemini CLI system prompt
├── setup.py
├── pyproject.toml
└── requirements.txt
```

## License

MIT
