from fastapi import APIRouter, HTTPException
from starlette.concurrency import iterate_in_threadpool
from starlette.responses import StreamingResponse

from api import state
from api.models import ResumeRequest, SendMessageRequest
from api.services import agent_runner
from api.sse import ErrorEvent, format_sse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{session_id}/send")
async def send_message(session_id: str, body: SendMessageRequest):
    lock = state.get_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Session busy — a turn is already in progress.")

    gen = agent_runner.run_turn(session_id, body.message, body.provider, body.model)

    async def event_stream():
        try:
            async for event in iterate_in_threadpool(gen):
                yield format_sse(event)
        except Exception as e:
            yield format_sse(ErrorEvent(message=str(e)))
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{session_id}/resume")
async def resume_message(session_id: str, body: ResumeRequest):
    lock = state.get_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Session busy — a turn is already in progress.")

    gen = agent_runner.resume_turn(session_id, body.tool_call_id, body.answer)

    async def event_stream():
        try:
            async for event in iterate_in_threadpool(gen):
                yield format_sse(event)
        except Exception as e:
            yield format_sse(ErrorEvent(message=str(e)))
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
