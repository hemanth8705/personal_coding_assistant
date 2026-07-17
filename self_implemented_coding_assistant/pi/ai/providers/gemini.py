from google.genai import types
from pi.ai.base import BaseChat, ToolCall, ToolResult, ToolDefinition, Usage
from pi.ai.client import get_client
from pi.session import Message

MODEL = "gemini-3-flash-preview"


def _to_gemini_schema(schema: dict) -> types.Schema:
    type_map = {
        "string": types.Type.STRING,
        "integer": types.Type.INTEGER,
        "number": types.Type.NUMBER,
        "boolean": types.Type.BOOLEAN,
        "array": types.Type.ARRAY,
        "object": types.Type.OBJECT,
    }
    gemini_type = type_map.get(schema.get("type", "string"), types.Type.STRING)
    properties = {
        k: _to_gemini_schema(v)
        for k, v in schema.get("properties", {}).items()
    }
    return types.Schema(
        type=gemini_type,
        description=schema.get("description", ""),
        properties=properties or None,
        required=schema.get("required"),
    )


def _to_gemini_history(history: list) -> list[types.Content]:
    result = []
    i = 0
    while i < len(history):
        msg = history[i]
        if msg.role == "user":
            result.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg.content or "")],
            ))
            i += 1
        elif msg.role == "assistant":
            parts = []
            if msg.content:
                parts.append(types.Part.from_text(text=msg.content))
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    parts.append(types.Part(
                        function_call=types.FunctionCall(
                            id=tc.get("id", ""),
                            name=tc["name"],
                            args=tc["args"],
                        )
                    ))
            result.append(types.Content(role="model", parts=parts or [types.Part.from_text(text="")]))
            i += 1
        elif msg.role == "tool":
            # Gemini requires consecutive tool results grouped into one user message
            parts = []
            while i < len(history) and history[i].role == "tool":
                t = history[i]
                parts.append(types.Part.from_function_response(
                    name=t.name or "",
                    response={"output": t.content or ""},
                ))
                i += 1
            result.append(types.Content(role="user", parts=parts))
        else:
            i += 1
    return result


class GeminiChat(BaseChat):
    def __init__(self, system_prompt: str, tools: list[ToolDefinition], history: list[Message], model: str | None = None):
        client = get_client()
        declarations = [
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=_to_gemini_schema(t.parameters),
            )
            for t in tools
        ]
        gemini_history = _to_gemini_history(history)
        self._chat = client.chats.create(
            model=model or MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(function_declarations=declarations)] if declarations else [],
            ),
            history=gemini_history,
        )
        self.last_usage = Usage()

    def send_stream(self, message: str):
        self.last_usage = Usage()
        tool_calls = []
        for chunk in self._chat.send_message_stream(message):
            if chunk.text:
                yield chunk.text
            if chunk.function_calls:
                for fc in chunk.function_calls:
                    tool_calls.append(
                        ToolCall(name=fc.name, args=dict(fc.args), id=getattr(fc, "id", ""))
                    )
            if chunk.usage_metadata:
                self.last_usage = Usage(
                    input_tokens=chunk.usage_metadata.prompt_token_count or 0,
                    output_tokens=chunk.usage_metadata.candidates_token_count or 0,
                )
        if tool_calls:
            yield tool_calls

    def send(self, message: str | list[ToolResult]) -> tuple[str, list[ToolCall]]:
        if isinstance(message, str):
            response = self._chat.send_message(message)
        else:
            parts = [
                types.Part.from_function_response(
                    name=r.name,
                    response={"output": r.output},
                )
                for r in message
            ]
            response = self._chat.send_message(parts)

        if response.usage_metadata:
            self.last_usage = Usage(
                input_tokens=response.usage_metadata.prompt_token_count or 0,
                output_tokens=response.usage_metadata.candidates_token_count or 0,
            )
        tool_calls = [
            ToolCall(name=fc.name, args=dict(fc.args), id=getattr(fc, "id", ""))
            for fc in (response.function_calls or [])
        ]
        return response.text or "", tool_calls
