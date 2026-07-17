import json
import os
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str           # "user", "assistant", "tool"
    content: str | None = None
    tool_calls: list[dict] | None = None  # [{"id": ..., "name": ..., "args": {...}}]
    tool_call_id: str | None = None       # for role="tool": which call this answers
    name: str | None = None               # for role="tool": which tool ran
    timestamp: str = ""


def load(path: str) -> list[Message]:
    if not os.path.exists(path):
        return []
    messages = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                messages.append(Message(
                    role=data["role"],
                    content=data.get("content"),
                    tool_calls=data.get("tool_calls"),
                    tool_call_id=data.get("tool_call_id"),
                    name=data.get("name"),
                    timestamp=data.get("timestamp", ""),
                ))
    return messages


def _write(path: str, entry: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def append(path: str, role: str, content: str) -> None:
    _write(path, {"role": role, "content": content, "timestamp": datetime.now().isoformat()})


def append_assistant(path: str, content: str | None, tool_calls: list[dict]) -> None:
    """Append an assistant message that requested tool calls."""
    entry: dict = {"role": "assistant", "timestamp": datetime.now().isoformat()}
    if content:
        entry["content"] = content
    entry["tool_calls"] = tool_calls
    _write(path, entry)


def append_tool_result(path: str, tool_call_id: str, name: str, content: str) -> None:
    """Append a tool result message."""
    _write(path, {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
