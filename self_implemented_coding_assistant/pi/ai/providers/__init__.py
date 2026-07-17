from pi.ai.base import BaseChat, ToolDefinition
from pi.session import Message


def get_chat(
    provider: str,
    system_prompt: str,
    tools: list[ToolDefinition],
    history: list[Message] | None = None,
    model: str | None = None,
) -> BaseChat:
    if provider == "gemini":
        from pi.ai.providers.gemini import GeminiChat
        return GeminiChat(system_prompt, tools, history or [], model=model)
    if provider == "openai":
        from pi.ai.providers.openai import OpenAIChat
        return OpenAIChat(system_prompt, tools, history or [], model=model)
    raise ValueError(f"Unknown provider: {provider!r}. Choose 'gemini' or 'openai'.")
