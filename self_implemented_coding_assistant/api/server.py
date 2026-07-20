"""FastAPI entry point for the Pi coding assistant.

Run with: uv run uvicorn api.server:app --port 8000 --reload

IMPORTANT: this process keeps per-session chat state (cached BaseChat instances,
ask_user pause state, locks) in memory — see api/state.py. It MUST run as a single
worker process (no `--workers > 1`), and any load balancer/reverse proxy in front of
it must not buffer the streaming (text/event-stream) responses.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import cors_origins
from api.routers import chat, config, sessions

app = FastAPI(title="Pi Coding Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(config.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
