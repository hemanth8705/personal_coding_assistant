import json
import os
from openai import OpenAI
from pi.ai.base import BaseChat, ToolCall, ToolResult, ToolDefinition, Usage
from pi.session import Message

MODEL = "gpt-4o-mini"


class OpenAIChat(BaseChat):
    def __init__(self, system_prompt: str, tools: list[ToolDefinition], history: list[Message], model: str | None = None):
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._model = model or MODEL
        self._tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
        self._messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for msg in history:
            if msg.role == "user":
                self._messages.append({"role": "user", "content": msg.content or ""})
            elif msg.role == "assistant" and not msg.tool_calls:
                self._messages.append({"role": "assistant", "content": msg.content})
            elif msg.role == "assistant" and msg.tool_calls:
                self._messages.append({
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"]),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            elif msg.role == "tool":
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or "",
                })
        self.last_usage = Usage()

    def send_stream(self, message: str):
        self._messages.append({"role": "user", "content": message})
        self.last_usage = Usage()
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            tools=self._tools or None,
            stream=True,
            stream_options={"include_usage": True},
        )
        collected_text = ""
        raw_tcs: dict[int, dict] = {}

        for chunk in stream:
            # OpenAI sends a final empty chunk with usage when stream_options includes it
            if chunk.usage:
                self.last_usage = Usage(
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                )
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                collected_text += delta.content
                yield delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    i = tc.index
                    if i not in raw_tcs:
                        raw_tcs[i] = {"id": "", "name": "", "args": ""}
                    if tc.id:
                        raw_tcs[i]["id"] = tc.id
                    if tc.function and tc.function.name:
                        raw_tcs[i]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        raw_tcs[i]["args"] += tc.function.arguments

        if raw_tcs:
            openai_tcs = [
                {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["args"]}}
                for tc in raw_tcs.values()
            ]
            self._messages.append({"role": "assistant", "content": collected_text or None, "tool_calls": openai_tcs})
            yield [
                ToolCall(name=tc["name"], args=json.loads(tc["args"]), id=tc["id"])
                for tc in raw_tcs.values()
            ]
        else:
            self._messages.append({"role": "assistant", "content": collected_text})

    def send(self, message: str | list[ToolResult]) -> tuple[str, list[ToolCall]]:
        if isinstance(message, str):
            self._messages.append({"role": "user", "content": message})
        else:
            for r in message:
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": r.id,
                    "content": r.output,
                })

        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            tools=self._tools or None,
        )

        msg = response.choices[0].message
        self._messages.append(msg)

        if response.usage:
            self.last_usage = Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        tool_calls = []
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    name=tc.function.name,
                    args=json.loads(tc.function.arguments),
                    id=tc.id,
                )
                for tc in msg.tool_calls
            ]

        return msg.content or "", tool_calls
