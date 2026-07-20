"""HTTP-facing port of pi/chat.py's agent loop.

Reuses pi.chat.TOOLS/EXECUTORS/_build_system_prompt/COMPACT_PROMPT/_session_file,
pi.ai.providers.get_chat, pi.session and pi.config directly. pi/chat.py itself is
untouched — this module replaces its REPL/console loop with a generator of Event
objects that the API layer streams out as SSE.

Persistence rule: a tool-call batch is written to the session JSONL only once it is
*fully* resolved (every call in the batch has a result). If the batch contains an
ask_user call, nothing is persisted until the human answers and the batch resolves —
this avoids ever leaving a "dangling tool_call" turn in the JSONL that the provider
would reject on replay after a mid-pause process restart.
"""

import os
from typing import Generator

from pi import config as _config
from pi import session
from pi.ai.base import ToolCall, ToolResult
from pi.ai.providers import get_chat
from pi.chat import COMPACT_PROMPT, EXECUTORS, TOOLS, _build_system_prompt, _session_file

from api import state
from api.sse import (
    AwaitingInputEvent,
    CompactedEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    UsageEvent,
)


def _sessions_dir() -> str:
    cfg = _config.load()
    d = os.path.expanduser(cfg["sessions_dir"])
    os.makedirs(d, exist_ok=True)
    return d


def _get_or_build(session_id: str, provider: str | None, model: str | None) -> state.SessionState:
    cfg = _config.load()
    provider = provider or cfg["provider"]
    if provider not in ("gemini", "openai"):
        raise ValueError(f"Unknown provider: {provider!r}. Choose 'gemini' or 'openai'.")
    model = model or cfg["models"].get(provider, provider)

    cached = state.get_cached(session_id)
    if cached is not None and cached.provider == provider and cached.model == model:
        return cached

    system_prompt = _build_system_prompt()
    history = session.load(_session_file(_sessions_dir(), session_id))
    chat = get_chat(provider, system_prompt, TOOLS, history, model=model)
    new_state = state.SessionState(chat=chat, provider=provider, model=model, system_prompt=system_prompt)
    state.put(session_id, new_state)
    return new_state


def _execute_batch(
    st: state.SessionState,
    text: str | None,
    original_tool_calls: list[ToolCall],
    start_index: int,
    results: list[ToolResult],
) -> Generator[Event, None, bool]:
    """Executes original_tool_calls[start_index:], appending each ToolResult to `results`.

    Returns True (via StopIteration value, capture with `yield from`) if it paused on an
    ask_user call — st.paused is set in that case, carrying `text` so it can be persisted
    together with the rest of the round once resumed. Returns False if the tail resolved.
    """
    i = start_index
    while i < len(original_tool_calls):
        tc = original_tool_calls[i]
        if tc.name == "ask_user":
            st.paused = state.PausedBatch(
                text=text,
                original_tool_calls=original_tool_calls,
                partial_results=list(results),
                pending_index=i,
            )
            yield AwaitingInputEvent(tool_call_id=tc.id, question=tc.args.get("question", ""))
            return True

        yield ToolCallEvent(id=tc.id, name=tc.name, args=tc.args)
        output = EXECUTORS[tc.name](**tc.args)
        yield ToolResultEvent(id=tc.id, name=tc.name, output=output)
        results.append(ToolResult(name=tc.name, output=output, id=tc.id))
        i += 1
    return False


def _settle_batch(
    sess_file: str,
    st: state.SessionState,
    text: str | None,
    original_tool_calls: list[ToolCall],
    results: list[ToolResult],
) -> tuple[str, list[ToolCall]]:
    """Persists a fully-resolved round (its text + tool-call request + all results) atomically,
    then calls chat.send() and returns the next (text, tool_calls)."""
    session.append_assistant(sess_file, text or None, [
        {"id": tc.id, "name": tc.name, "args": tc.args} for tc in original_tool_calls
    ])
    for r in results:
        session.append_tool_result(sess_file, r.id, r.name, r.output)
    return st.chat.send(results)


def _process_round(
    session_id: str, st: state.SessionState, text: str | None, tool_calls: list[ToolCall]
) -> Generator[Event, None, None]:
    """Handles one (text, tool_calls) round. If tool_calls is empty, this is the terminal
    round for the turn — persist the plain text and stop. Otherwise execute the batch
    (which may pause on ask_user) and, once fully resolved, persist + continue recursively
    with the next round produced by chat.send()."""
    sess_file = _session_file(_sessions_dir(), session_id)

    if not tool_calls:
        if text:
            session.append(sess_file, "assistant", text)
        return

    results: list[ToolResult] = []
    paused = yield from _execute_batch(st, text, tool_calls, 0, results)
    if paused:
        return

    new_text, new_tool_calls = _settle_batch(sess_file, st, text, tool_calls, results)
    if new_text:
        yield TextEvent(chunk=new_text)
    yield from _process_round(session_id, st, new_text, new_tool_calls)


def _compact(session_id: str, st: state.SessionState) -> str | None:
    summary, _ = st.chat.send(COMPACT_PROMPT)
    if not summary:
        return None
    sess_file = _session_file(_sessions_dir(), session_id)
    if os.path.exists(sess_file):
        os.remove(sess_file)
    session.append(sess_file, "assistant", f"[Compacted context]\n{summary}")
    history = session.load(sess_file)
    st.chat = get_chat(st.provider, st.system_prompt, TOOLS, history, model=st.model)
    return summary


def compact_now(session_id: str) -> str | None:
    cfg = _config.load()
    st = _get_or_build(session_id, cfg["provider"], None)
    return _compact(session_id, st)


def _finish_turn(session_id: str, st: state.SessionState) -> Generator[Event, None, None]:
    usage = st.chat.last_usage
    yield UsageEvent(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, model=st.model)

    cfg = _config.load()
    threshold = cfg.get("compact_threshold", 30000)
    if usage.input_tokens > threshold:
        summary = _compact(session_id, st)
        if summary is not None:
            yield CompactedEvent(summary=summary)

    yield DoneEvent()


def run_turn(
    session_id: str, message: str, provider: str | None = None, model: str | None = None
) -> Generator[Event, None, None]:
    try:
        st = _get_or_build(session_id, provider, model)
    except Exception as e:
        yield ErrorEvent(message=str(e))
        yield DoneEvent()
        return

    if st.paused is not None:
        yield ErrorEvent(message="This session has a pending question — resume it before sending a new message.")
        yield DoneEvent()
        return

    try:
        sess_file = _session_file(_sessions_dir(), session_id)
        session.append(sess_file, "user", message)

        text_buffer = ""
        tool_calls: list[ToolCall] = []
        for chunk in st.chat.send_stream(message):
            if isinstance(chunk, str):
                text_buffer += chunk
                yield TextEvent(chunk=chunk)
            elif isinstance(chunk, list):
                tool_calls = chunk

        yield from _process_round(session_id, st, text_buffer, tool_calls)

        if st.paused is not None:
            return

        yield from _finish_turn(session_id, st)
    except Exception as e:
        yield ErrorEvent(message=str(e))
        yield DoneEvent()


def resume_turn(session_id: str, tool_call_id: str, answer: str) -> Generator[Event, None, None]:
    st = state.get_cached(session_id)
    if st is None or st.paused is None:
        yield ErrorEvent(message="No pending question for this session.")
        yield DoneEvent()
        return
    if st.paused.pending_call.id != tool_call_id:
        yield ErrorEvent(message="tool_call_id does not match the pending question.")
        yield DoneEvent()
        return

    try:
        paused = st.paused
        st.paused = None
        results = list(paused.partial_results)
        results.append(ToolResult(name="ask_user", output=answer.strip() or "No answer provided.", id=tool_call_id))

        still_paused = yield from _execute_batch(
            st, paused.text, paused.original_tool_calls, paused.pending_index + 1, results
        )
        if still_paused:
            return

        sess_file = _session_file(_sessions_dir(), session_id)
        new_text, new_tool_calls = _settle_batch(sess_file, st, paused.text, paused.original_tool_calls, results)
        if new_text:
            yield TextEvent(chunk=new_text)
        yield from _process_round(session_id, st, new_text, new_tool_calls)

        if st.paused is not None:
            return

        yield from _finish_turn(session_id, st)
    except Exception as e:
        yield ErrorEvent(message=str(e))
        yield DoneEvent()
