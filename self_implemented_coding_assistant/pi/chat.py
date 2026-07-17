import os
import glob
import platform
import subprocess
import sys
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from pi.ai.base import ToolResult, Usage
from pi.ai.providers import get_chat
from pi.tools import bash as bash_tool
from pi.tools import read as read_tool
from pi.tools import write as write_tool
from pi.tools import edit as edit_tool
from pi.tools import grep as grep_tool
from pi.tools import ls as ls_tool
from pi.tools import ask_user as ask_user_tool
from pi.tools import find as find_tool
from pi import session
from pi import config as _config

console = Console()

# Approximate cost per 1M tokens (input, output) in USD
_COST_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-3-flash-preview": (0.10, 0.40),
}

COMPACT_PROMPT = (
    "Summarize our entire conversation so far into a single detailed paragraph. "
    "Include: the main goal, key decisions made, important code written or changed, "
    "and any context needed to continue. Be thorough — this replaces the full history."
)


def _build_system_prompt() -> str:
    """Build system prompt with live environment context injected at startup."""
    cwd = os.getcwd()
    os_name = f"{platform.system()} {platform.release()}"
    py_ver = sys.version.split()[0]

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        git_branch = result.stdout.strip() if result.returncode == 0 else "not a git repo"
    except Exception:
        git_branch = "unknown"

    pi_md_section = ""
    pi_md_path = os.path.join(cwd, "pi.md")
    if os.path.isfile(pi_md_path):
        try:
            with open(pi_md_path, "r", encoding="utf-8") as f:
                pi_md_section = f"\nProject context (from pi.md):\n{f.read().strip()}\n"
        except OSError:
            pass

    return (
        "You are Pi, an AI coding assistant running in the terminal.\n\n"
        f"Environment:\n"
        f"  cwd: {cwd}\n"
        f"  os: {os_name}\n"
        f"  python: {py_ver}\n"
        f"  git branch: {git_branch}\n"
        + pi_md_section +
        "\nGuidelines:\n"
        "  - Prefer 'edit' over 'write' for targeted changes to existing files.\n"
        "  - Use 'grep' instead of 'read' when searching for something specific across files.\n"
        "  - Use 'find' to locate files by name pattern; use 'grep' to search file contents.\n"
        "  - After each tool result, give a brief status update: what you found and your next step.\n"
        "  - If a file read is truncated, use the 'offset' parameter to continue reading.\n"
        "  - Use recursive=True with 'ls' for a comprehensive view of project structure.\n"
        "  - Be concise, technical, and direct.\n\n"
        "Safety:\n"
        "  - Before any operation that deletes files, removes directories, or makes irreversible changes,\n"
        "    use the 'ask_user' tool to describe what you are about to do and get explicit confirmation.\n"
        "  - If the user declines, do NOT attempt the same operation through any other method or tool.\n"
        "  - This applies to shell commands, Python one-liners, file rewrites, and any other approach.\n"
        "  - Use 'ask_user' whenever the task is ambiguous, multiple valid approaches exist, or you\n"
        "    need more context before proceeding. Prefer asking over guessing."
    )


TOOLS = [
    bash_tool.DEFINITION,
    read_tool.DEFINITION,
    write_tool.DEFINITION,
    edit_tool.DEFINITION,
    grep_tool.DEFINITION,
    ls_tool.DEFINITION,
    ask_user_tool.DEFINITION,
    find_tool.DEFINITION,
]

EXECUTORS = {
    "bash": bash_tool.execute,
    "read": read_tool.execute,
    "write": write_tool.execute,
    "edit": edit_tool.execute,
    "grep": grep_tool.execute,
    "ls": ls_tool.execute,
    "ask_user": ask_user_tool.execute,
    "find": find_tool.execute,
}


def _session_file(sessions_dir: str, name: str) -> str:
    return os.path.join(sessions_dir, f"{name}.jsonl")


def _list_sessions(sessions_dir: str) -> None:
    files = glob.glob(os.path.join(sessions_dir, "*.jsonl"))
    if not files:
        console.print("[dim]No sessions found.[/dim]\n")
        return
    table = Table(title="Saved Sessions", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Messages", justify="right")
    table.add_column("Last Modified")
    for path in sorted(files, key=os.path.getmtime, reverse=True):
        name = os.path.splitext(os.path.basename(path))[0]
        msgs = session.load(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        table.add_row(name, str(len(msgs)), mtime)
    console.print(table)
    console.print()


def _print_config(cfg: dict) -> None:
    table = Table(title="Pi Config", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("provider", cfg["provider"])
    table.add_row("sessions_dir", cfg["sessions_dir"])
    for provider_name, model_name in cfg["models"].items():
        table.add_row(f"model.{provider_name}", model_name)
    table.add_row("compact_threshold", f"{cfg.get('compact_threshold', 30000):,} tokens")
    table.add_row("[dim]config file[/dim]", str(_config.CONFIG_PATH))
    console.print(table)
    console.print()


def _print_help() -> None:
    table = Table(title="Pi Slash Commands", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="bold")
    table.add_column("Description")
    table.add_row("/help", "Show this help message")
    table.add_row("/clear", "Wipe the current session's history")
    table.add_row("/model [name]", "Show current model or switch to a new one")
    table.add_row("/provider <name>", "Switch provider: gemini or openai")
    table.add_row("/sessions", "List all saved sessions")
    table.add_row("/session <name>", "Switch to a named session (creates if new)")
    table.add_row("/delete [name]", "Delete a session (default: current)")
    table.add_row("/config", "Show current config")
    table.add_row("/config set <key> <value>", "Save a config value persistently")
    table.add_row("/compact", "Summarize and compress the current session history")
    console.print(table)
    console.print()


def _print_usage(usage: Usage, model: str) -> None:
    if not usage.input_tokens and not usage.output_tokens:
        return
    parts = [f"↑{usage.input_tokens:,} ↓{usage.output_tokens:,} tokens"]
    model_lower = model.lower()
    rate = next((v for k, v in _COST_PER_1M.items() if model_lower.startswith(k) or k in model_lower), None)
    if rate:
        cost = (usage.input_tokens * rate[0] + usage.output_tokens * rate[1]) / 1_000_000
        parts.append(f"~${cost:.4f}")
    console.print(f"[dim]  {'  ·  '.join(parts)}[/dim]\n")


def _compact_session(
    chat, sessions_dir: str, current_session: str,
    current_provider: str, current_model: str,
    system_prompt: str,
):
    console.print("[yellow]Context getting long — compacting session history...[/yellow]")
    summary, _ = chat.send(COMPACT_PROMPT)
    if not summary:
        console.print("[red]Compaction failed — continuing with full history.[/red]\n")
        return chat
    path = _session_file(sessions_dir, current_session)
    if os.path.exists(path):
        os.remove(path)
    session.append(path, "assistant", f"[Compacted context]\n{summary}")
    history = session.load(path)
    new_chat = get_chat(current_provider, system_prompt, TOOLS, history, model=current_model)
    console.print("[dim]Session compacted. Continuing with summarized context.[/dim]\n")
    return new_chat


def start_chat_loop(provider: str = "gemini", session_name: str = "default") -> None:
    cfg = _config.load()

    current_provider = provider
    current_model = cfg["models"].get(current_provider, provider)
    current_session = session_name
    sessions_dir = os.path.expanduser(cfg["sessions_dir"])

    os.makedirs(sessions_dir, exist_ok=True)

    system_prompt = _build_system_prompt()

    history = session.load(_session_file(sessions_dir, current_session))

    if history:
        console.print(
            f"[dim]Resuming session [bold]{current_session}[/bold] "
            f"({len(history)} messages). Type /clear to start fresh.[/dim]\n"
        )
    else:
        console.print(
            f"[bold]Pi[/bold] — coding assistant "
            f"[[cyan]{current_provider}[/cyan]] [[dim]{current_model}[/dim]] "
            f"session [bold]{current_session}[/bold]. "
            f"Type /help for commands.\n"
        )

    chat = get_chat(current_provider, system_prompt, TOOLS, history, model=current_model)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("exit", "quit"):
            console.print("[dim]Goodbye![/dim]")
            break

        # --- Slash commands ---
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=2)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            arg2 = parts[2].strip() if len(parts) > 2 else ""

            if cmd == "/help":
                _print_help()

            elif cmd == "/clear":
                path = _session_file(sessions_dir, current_session)
                if os.path.exists(path):
                    os.remove(path)
                chat = get_chat(current_provider, system_prompt, TOOLS, [], model=current_model)
                console.print(f"[dim]Session [bold]{current_session}[/bold] cleared.[/dim]\n")

            elif cmd == "/model":
                if not arg:
                    console.print(f"[dim]Current model: {current_model}[/dim]\n")
                else:
                    current_model = arg
                    history = session.load(_session_file(sessions_dir, current_session))
                    chat = get_chat(current_provider, system_prompt, TOOLS, history, model=current_model)
                    console.print(f"[dim]Switched to model: {current_model}.[/dim]\n")

            elif cmd == "/provider":
                if arg not in ("gemini", "openai"):
                    console.print(f"[red]Unknown provider: {arg!r}. Use 'gemini' or 'openai'.[/red]\n")
                else:
                    current_provider = arg
                    current_model = cfg["models"].get(current_provider, current_provider)
                    history = session.load(_session_file(sessions_dir, current_session))
                    chat = get_chat(current_provider, system_prompt, TOOLS, history, model=current_model)
                    console.print(f"[dim]Switched to {current_provider} ({current_model}).[/dim]\n")

            elif cmd == "/sessions":
                _list_sessions(sessions_dir)

            elif cmd == "/session":
                if not arg:
                    console.print(f"[dim]Current session: [bold]{current_session}[/bold][/dim]\n")
                else:
                    current_session = arg
                    history = session.load(_session_file(sessions_dir, current_session))
                    chat = get_chat(current_provider, system_prompt, TOOLS, history, model=current_model)
                    if history:
                        console.print(
                            f"[dim]Switched to session [bold]{current_session}[/bold] "
                            f"({len(history)} messages).[/dim]\n"
                        )
                    else:
                        console.print(f"[dim]Started new session [bold]{current_session}[/bold].[/dim]\n")

            elif cmd == "/delete":
                target = arg or current_session
                path = _session_file(sessions_dir, target)
                if not os.path.exists(path):
                    console.print(f"[red]Session {target!r} not found.[/red]\n")
                else:
                    os.remove(path)
                    console.print(f"[dim]Deleted session [bold]{target}[/bold].[/dim]")
                    if target == current_session:
                        current_session = "default"
                        chat = get_chat(current_provider, system_prompt, TOOLS, [], model=current_model)
                        console.print(f"[dim]Switched to session [bold]{current_session}[/bold].[/dim]")
                    console.print()

            elif cmd == "/compact":
                chat = _compact_session(
                    chat, sessions_dir, current_session,
                    current_provider, current_model, system_prompt,
                )

            elif cmd == "/config":
                if arg == "set":
                    # /config set <key> <value>
                    if not arg2:
                        console.print("[red]Usage: /config set <key> <value>[/red]\n")
                    else:
                        # arg2 may be "value" alone if key was in arg — re-split from original
                        raw = user_input.split(maxsplit=3)
                        key = raw[2] if len(raw) > 2 else ""
                        val = raw[3] if len(raw) > 3 else ""
                        if not key or not val:
                            console.print("[red]Usage: /config set <key> <value>[/red]\n")
                        else:
                            ok, msg = _config.set_value(key, val)
                            if ok:
                                cfg = _config.load()
                                console.print(f"[dim]{msg}[/dim]\n")
                            else:
                                console.print(f"[red]{msg}[/red]\n")
                else:
                    _print_config(cfg)

            else:
                console.print(f"[red]Unknown command: {cmd}. Type /help for a list.[/red]\n")

            continue

        if not user_input:
            continue

        session.append(_session_file(sessions_dir, current_session), "user", user_input)

        # Stream the initial response
        text_buffer = ""
        tool_calls = []
        got_text = False

        for chunk in chat.send_stream(user_input):
            if isinstance(chunk, str):
                if not got_text:
                    console.print("\n[bold green]Pi:[/bold green] ", end="")
                    got_text = True
                console.print(chunk, end="")
                text_buffer += chunk
            elif isinstance(chunk, list):
                tool_calls = chunk

        if got_text:
            console.print("\n")

        # Persist initial assistant turn
        _sess = _session_file(sessions_dir, current_session)
        if tool_calls:
            session.append_assistant(_sess, text_buffer or None, [
                {"id": tc.id, "name": tc.name, "args": tc.args} for tc in tool_calls
            ])
        else:
            session.append(_sess, "assistant", text_buffer)

        # Agent loop — runs until no more tool calls
        while tool_calls:
            results = []
            for tc in tool_calls:
                label = tc.args.get("command") or tc.args.get("path") or tc.name

                if tc.name == "ask_user":
                    output = EXECUTORS[tc.name](**tc.args)
                    session.append_tool_result(_sess, tc.id, tc.name, output)
                    results.append(ToolResult(name=tc.name, output=output, id=tc.id))
                    continue

                console.print(
                    Panel(f"[dim]{label}[/dim]", title=f"[bold cyan]{tc.name}[/bold cyan]", expand=False)
                )

                output = EXECUTORS[tc.name](**tc.args)
                console.print(f"[dim]{output[:600]}[/dim]\n")
                session.append_tool_result(_sess, tc.id, tc.name, output)
                results.append(ToolResult(name=tc.name, output=output, id=tc.id))

            new_text, tool_calls = chat.send(results)
            if new_text:
                if not got_text:
                    console.print("\n[bold green]Pi:[/bold green]")
                    got_text = True
                console.print(Markdown(new_text))
                text_buffer += "\n" + new_text

            # Persist this round's assistant response
            if tool_calls:
                session.append_assistant(_sess, new_text or None, [
                    {"id": tc.id, "name": tc.name, "args": tc.args} for tc in tool_calls
                ])
            elif new_text:
                session.append(_sess, "assistant", new_text)

        # Final response after tool calls (non-streamed) - ONLY if we haven't printed anything yet
        if not got_text and text_buffer:
            console.print()
            console.print("[bold green]Pi:[/bold green]")
            console.print(Markdown(text_buffer))
            console.print()

        # Show token usage and estimated cost
        _print_usage(chat.last_usage, current_model)

        # Auto-compact when context grows too large
        threshold = cfg.get("compact_threshold", 30000)
        if chat.last_usage.input_tokens > threshold:
            chat = _compact_session(
                chat, sessions_dir, current_session,
                current_provider, current_model, system_prompt,
            )
