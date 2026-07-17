import os
import time
import requests

from pi.ai.providers import get_chat
from pi.ai.base import ToolResult
from pi import session, config as _config
from pi.chat import TOOLS, EXECUTORS, _build_system_prompt, _compact_session, COMPACT_PROMPT

_API = "https://api.telegram.org/bot{token}/{method}"

# ask_user requires stdin — not usable in Telegram mode
_TOOLS = [t for t in TOOLS if t.name != "ask_user"]
_EXECUTORS = {k: v for k, v in EXECUTORS.items() if k != "ask_user"}


def _call(token: str, method: str, **params) -> dict:
    resp = requests.post(_API.format(token=token, method=method), json=params, timeout=30)
    return resp.json()


def _send(token: str, chat_id: str, text: str) -> None:
    for i in range(0, len(text), 4096):
        _call(token, "sendMessage", chat_id=chat_id, text=text[i:i + 4096])


def _typing(token: str, chat_id: str) -> None:
    _call(token, "sendChatAction", chat_id=chat_id, action="typing")


def run(token: str) -> None:
    cfg = _config.load()
    provider = cfg["provider"]
    model = cfg["models"].get(provider, provider)
    sessions_dir = os.path.join(os.path.expanduser(cfg["sessions_dir"]), "telegram")
    os.makedirs(sessions_dir, exist_ok=True)

    system_prompt = _build_system_prompt()
    chats: dict[str, object] = {}

    # Verify token
    me = _call(token, "getMe")
    if not me.get("ok"):
        print(f"Invalid token: {me}")
        return
    username = me["result"].get("username", "?")
    print(f"Pi Telegram bot running as @{username}. Ctrl+C to stop.")

    offset = 0
    while True:
        try:
            result = _call(token, "getUpdates", offset=offset, timeout=20)
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(5)
            continue

        for update in result.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            chat_id = str(msg["chat"]["id"])
            text = msg["text"].strip()
            if not text:
                continue

            sess_path = os.path.join(sessions_dir, f"{chat_id}.jsonl")

            if chat_id not in chats:
                history = session.load(sess_path)
                chats[chat_id] = get_chat(provider, system_prompt, _TOOLS, history, model=model)

            chat = chats[chat_id]
            session.append(sess_path, "user", text)
            _typing(token, chat_id)

            response_text, tool_calls = chat.send(text)

            while tool_calls:
                session.append_assistant(sess_path, response_text or None, [
                    {"id": tc.id, "name": tc.name, "args": tc.args} for tc in tool_calls
                ])

                results = []
                for tc in tool_calls:
                    if tc.name in _EXECUTORS:
                        output = _EXECUTORS[tc.name](**tc.args)
                    else:
                        output = f"Tool '{tc.name}' not available in Telegram mode."
                    session.append_tool_result(sess_path, tc.id, tc.name, output)
                    results.append(ToolResult(name=tc.name, output=output, id=tc.id))

                _typing(token, chat_id)
                response_text, tool_calls = chat.send(results)

            if response_text:
                session.append(sess_path, "assistant", response_text)
                _send(token, chat_id, response_text)

            # Auto-compact
            threshold = cfg.get("compact_threshold", 30000)
            if chat.last_usage.input_tokens > threshold:
                print(f"[{chat_id}] Auto-compacting session...")
                chats[chat_id] = _compact_session(
                    chat, sessions_dir, chat_id, provider, model, system_prompt,
                )
