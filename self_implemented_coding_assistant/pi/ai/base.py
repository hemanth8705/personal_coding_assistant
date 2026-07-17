from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generator


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    id: str = ""


@dataclass
class ToolResult:
    name: str
    output: str
    id: str = ""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class BaseChat(ABC):
    @abstractmethod
    def send(self, message: str | list[ToolResult]) -> tuple[str, list[ToolCall]]:
        """Send a user message or tool results. Returns (text, tool_calls)."""
        ...

    @abstractmethod
    def send_stream(self, message: str) -> Generator[str | list[ToolCall], None, None]:
        """Stream a user message. Yields str chunks, then list[ToolCall] at the end if tools were called."""
        ...
