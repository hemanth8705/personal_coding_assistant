# Pi — AI Coding Assistant

Pi is a terminal-based AI coding agent. It can read, write, edit, and search your codebase, run shell commands, and hold persistent sessions — all from your terminal or Telegram.

---

## Installation

**Requirements:** Python 3.11+, [uv](https://github.com/astral-sh/uv)

```bash
cd Python
uv sync
```

**API keys** — create a `.env` file in the `Python/` directory:

```env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here   # optional
```

---

## Running Pi

```bash
# Start a chat session (default provider: gemini)
python main.py

# Choose a provider
python main.py --provider openai

# Resume a named session
python main.py --session my-project

# Start as a Telegram bot
python main.py telegram --token YOUR_BOT_TOKEN
```

---

## Slash Commands

| Command | Description |
|---|---|
| `/help` | Show all commands |
| `/clear` | Wipe current session history |
| `/model [name]` | Show or switch the model |
| `/provider <name>` | Switch provider: `gemini` or `openai` |
| `/sessions` | List all saved sessions |
| `/session <name>` | Switch to a named session (creates if new) |
| `/delete [name]` | Delete a session (default: current) |
| `/compact` | Manually summarize and compress session history |
| `/config` | Show current config |
| `/config set <key> <value>` | Save a config value persistently |

### Config keys

| Key | Description | Example |
|---|---|---|
| `provider` | Default AI provider | `gemini` or `openai` |
| `model.<provider>` | Model for a provider | `model.gemini gemini-2.0-flash` |
| `sessions_dir` | Where sessions are stored | `~/pi-sessions` |
| `compact_threshold` | Token count before auto-compact | `30000` |
| `telegram_token` | Telegram bot token | `123456:AAF...` |

---

## Tools

Pi has access to these tools at runtime:

| Tool | Description |
|---|---|
| `bash` | Run a shell command |
| `read` | Read a file (with optional offset/limit) |
| `write` | Write/overwrite a file |
| `edit` | Replace a specific string in a file |
| `grep` | Search file contents by pattern |
| `find` | Locate files by name pattern (e.g. `*.py`) |
| `ls` | List directory contents (supports recursive) |
| `ask_user` | Ask the user a question and wait for input |

---

## Project Context — `pi.md`

If a `pi.md` file exists in your current working directory, Pi reads it at startup and injects it into the system prompt. Use it to give Pi persistent context about your project:

```markdown
# My Project

This is a FastAPI backend. The main app is in `src/app.py`.
Always use async functions. Never modify the `legacy/` directory.
```

Pi will follow these instructions automatically for every session in that directory.

---

## Telegram Bot

Pi can run as a Telegram bot, with each Telegram chat mapped to its own session.

**Setup:**
1. Create a bot via [@BotFather](https://t.me/botfather) and get your token
2. Save the token: `python main.py config set telegram_token <token>`
3. Start the bot: `python main.py telegram`

Sessions are stored in `sessions/telegram/<chat_id>.jsonl`. The bot has full tool access (bash, read, write, edit, grep, find, ls).

---

## Sessions

Sessions are stored as JSONL files (one message per line) in the `sessions/` directory. Each entry preserves the full conversation including tool calls and results, so Pi can resume exactly where it left off.

```
sessions/
  default.jsonl
  my-project.jsonl
  telegram/
    123456789.jsonl   ← per Telegram chat
```

---

## Architecture

```
Python/
  main.py                  ← CLI entry point (argparse)
  pi/
    chat.py                ← Main chat loop, slash commands, agent loop
    session.py             ← JSONL session storage
    config.py              ← Config load/save (~/.pi/config.json)
    telegram_bot.py        ← Telegram polling bot
    ai/
      base.py              ← Abstract types (BaseChat, ToolCall, Usage)
      client.py            ← Gemini client singleton
      providers/
        gemini.py          ← Gemini provider
        openai.py          ← OpenAI provider
    tools/
      bash.py
      read.py
      write.py
      edit.py
      grep.py
      find.py
      ls.py
      ask_user.py
```

Config is stored at `~/.pi/config.json` and persists across projects.

---

## Roadmap

- [ ] Anthropic / Claude provider
- [ ] Streaming bash output (live command output)
- [ ] Glob tool (recursive file pattern matching)
- [ ] Parallel tool execution
- [ ] `/undo` command
- [ ] Image input support
- [ ] VS Code extension
