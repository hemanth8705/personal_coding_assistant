from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    message: str
    provider: str | None = None
    model: str | None = None


class ResumeRequest(BaseModel):
    tool_call_id: str
    answer: str


class SessionInfo(BaseModel):
    name: str
    message_count: int
    last_modified: str


class MessageOut(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: str = ""


class SessionDetail(BaseModel):
    name: str
    messages: list[MessageOut]


class CreateSessionRequest(BaseModel):
    name: str


class ConfigOut(BaseModel):
    provider: str
    models: dict[str, str]
    sessions_dir: str
    compact_threshold: int
    telegram_token: str | None = None


class ConfigSetRequest(BaseModel):
    key: str
    value: str
