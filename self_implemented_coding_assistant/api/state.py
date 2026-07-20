"""In-memory per-session state: cached BaseChat instances, ask_user pause state, and locks.

Single-process design: this registry lives in process memory only, so uvicorn MUST run
with a single worker (no --workers > 1). A paused tool-call batch is never persisted to
the session JSONL until it fully resolves (see agent_runner.py) — if the process restarts
mid-pause, the in-flight turn is simply lost rather than leaving a corrupt "dangling
tool_call" history that would be rejected by the provider on the next request.
"""

import threading
from dataclasses import dataclass

from pi.ai.base import BaseChat, ToolCall, ToolResult


@dataclass
class PausedBatch:
    text: str | None                     # text that accompanied this round's tool-call request
    original_tool_calls: list[ToolCall]
    partial_results: list[ToolResult]
    pending_index: int

    @property
    def pending_call(self) -> ToolCall:
        return self.original_tool_calls[self.pending_index]


@dataclass
class SessionState:
    chat: BaseChat
    provider: str
    model: str
    system_prompt: str
    paused: PausedBatch | None = None


_sessions: dict[str, SessionState] = {}
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def get_lock(session_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(session_id)
        if lock is None:
            lock = threading.Lock()
            _locks[session_id] = lock
        return lock


def get_cached(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


def put(session_id: str, state: SessionState) -> None:
    _sessions[session_id] = state


def clear(session_id: str) -> None:
    _sessions.pop(session_id, None)
    with _locks_guard:
        _locks.pop(session_id, None)
