"""Event types streamed to the frontend over Server-Sent Events, and the wire formatter."""

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TextEvent:
    chunk: str
    type: str = field(default="text", init=False)


@dataclass
class ToolCallEvent:
    id: str
    name: str
    args: dict[str, Any]
    type: str = field(default="tool_call", init=False)


@dataclass
class ToolResultEvent:
    id: str
    name: str
    output: str
    type: str = field(default="tool_result", init=False)


@dataclass
class AwaitingInputEvent:
    tool_call_id: str
    question: str
    type: str = field(default="awaiting_input", init=False)


@dataclass
class UsageEvent:
    input_tokens: int
    output_tokens: int
    model: str
    type: str = field(default="usage", init=False)


@dataclass
class CompactedEvent:
    summary: str
    type: str = field(default="compacted", init=False)


@dataclass
class DoneEvent:
    type: str = field(default="done", init=False)


@dataclass
class ErrorEvent:
    message: str
    type: str = field(default="error", init=False)


Event = (
    TextEvent
    | ToolCallEvent
    | ToolResultEvent
    | AwaitingInputEvent
    | UsageEvent
    | CompactedEvent
    | DoneEvent
    | ErrorEvent
)


def format_sse(event: Event) -> str:
    payload = asdict(event)
    return f"data: {json.dumps(payload)}\n\n"
