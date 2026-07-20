import glob
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException

from pi import config as _config
from pi import session as _session
from pi.chat import _session_file

from api import state
from api.models import CreateSessionRequest, MessageOut, SessionDetail, SessionInfo
from api.services.agent_runner import compact_now

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _sessions_dir() -> str:
    cfg = _config.load()
    d = os.path.expanduser(cfg["sessions_dir"])
    os.makedirs(d, exist_ok=True)
    return d


@router.get("", response_model=list[SessionInfo])
def list_sessions():
    sessions_dir = _sessions_dir()
    files = glob.glob(os.path.join(sessions_dir, "*.jsonl"))
    out = []
    for path in sorted(files, key=os.path.getmtime, reverse=True):
        name = os.path.splitext(os.path.basename(path))[0]
        messages = _session.load(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
        out.append(SessionInfo(name=name, message_count=len(messages), last_modified=mtime))
    return out


@router.post("", response_model=SessionInfo)
def create_session(body: CreateSessionRequest):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Session name cannot be empty.")
    path = _session_file(_sessions_dir(), name)
    if os.path.exists(path):
        raise HTTPException(status_code=409, detail=f"Session {name!r} already exists.")
    open(path, "a", encoding="utf-8").close()
    mtime = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
    return SessionInfo(name=name, message_count=0, last_modified=mtime)


@router.get("/{name}", response_model=SessionDetail)
def get_session(name: str):
    path = _session_file(_sessions_dir(), name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Session {name!r} not found.")
    messages = _session.load(path)
    return SessionDetail(
        name=name,
        messages=[
            MessageOut(
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls,
                tool_call_id=m.tool_call_id,
                name=m.name,
                timestamp=m.timestamp,
            )
            for m in messages
        ],
    )


@router.delete("/{name}")
def delete_session(name: str):
    path = _session_file(_sessions_dir(), name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Session {name!r} not found.")
    os.remove(path)
    state.clear(name)
    return {"ok": True}


@router.post("/{name}/compact")
def compact_session(name: str):
    lock = state.get_lock(name)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Session busy — a turn is already in progress.")
    try:
        summary = compact_now(name)
        if summary is None:
            raise HTTPException(status_code=400, detail="Compaction failed — no summary produced.")
        return {"summary": summary}
    finally:
        lock.release()
