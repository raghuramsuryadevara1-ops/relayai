# ⚡ RelayAI

> **Claude thinks. Gemini speaks. Save up to 80% on AI API costs.**

RelayAI is an open-source terminal AI tool (like Claude Code) where **Claude plans and reasons**, then **passes the answer to Gemini to output** — dramatically reducing your Claude API costs by offloading output tokens to Gemini's free tier.

```
User Input → Claude (thinks & reasons) → Gemini (presents output) → Terminal
```

---

## 💡 Why RelayAI?

Claude charges **$15/million output tokens**. Output tokens are 5x more expensive than input.

RelayAI flips this: Claude produces a concise internal plan/answer, then Gemini (free tier) handles the expensive output step.

| | Normal Claude | RelayAI |
|---|---|---|
| Per query (avg) | $0.031 | $0.006 |
| 100 queries/day | ~$95/mo | ~$18/mo |
| 1000 queries/day | ~$945/mo | ~$180/mo |
| **Savings** | | **~80%** |

---

## 🚀 Install

```bash
pip install relayai
```

Or from source:
```bash
git clone https://github.com/yourusername/relayai
cd relayai
pip install -e .
```

---

## ⚙️ Setup

```bash
relayai login
```

You'll be asked to provide:
1. **Claude API Key** — from [console.anthropic.com](https://console.anthropic.com)
2. **Gemini access** — either:
   - Gemini API Key (from [ai.google.dev](https://ai.google.dev) — free)
   - Google Account Login (OAuth — no key needed)

---

## 🧑‍💻 Usage

```bash
# Ask a single question
relayai "write a binary search in python"

# Fix code / debug
relayai "fix this bug in my FastAPI route"

# Pipe files
cat main.py | relayai "review this code"

# Interactive chat mode
relayai --chat

# Show Claude's internal reasoning (debug)
relayai --verbose "explain transformers"

# Check your config
relayai status
```

---

## 🔁 How It Works

```
┌─────────────┐
│  User Input │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Claude Sonnet (via your API key)   │
│  • Understands the full request     │
│  • Reasons step by step             │
│  • Produces complete answer         │
│  • Uses minimal output tokens       │
└──────────────┬──────────────────────┘
               │ Claude's answer becomes
               │ Gemini's INPUT (free)
               ▼
┌─────────────────────────────────────┐
│  Gemini Flash (free tier)           │
│  • Receives Claude's answer         │
│  • Presents it clearly              │
│  • All output tokens are FREE       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────┐
│  Terminal   │
│  Output     │
└─────────────┘
```

---

## 📂 Project Structure

```
relayai/
├── relayai/
│   ├── __init__.py
│   ├── cli.py            # Terminal commands
│   ├── auth.py           # Login & credential management
│   ├── claude_client.py  # Claude API (thinker)
│   ├── gemini_client.py  # Gemini API (speaker)
│   └── pipeline.py       # The bridge logic
├── setup.py
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

PRs welcome! This is fully open source. Feel free to:
- Add streaming support
- Add more model options
- Improve the OAuth flow
- Build a config TUI

---

## 📄 License

MIT — free to use, modify, and distribute.
