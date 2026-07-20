"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getSession, resumeMessage, sendMessage } from "@/lib/api";
import { parseSSEStream } from "@/lib/sse";
import type { ChatEvent, MessageOut, UIMessage } from "@/lib/types";

let counter = 0;
function nextId(prefix: string): string {
  counter += 1;
  return `${prefix}-${counter}`;
}

function historyToMessages(history: MessageOut[]): UIMessage[] {
  const out: UIMessage[] = [];
  const toolById = new Map<string, number>();

  for (const msg of history) {
    if (msg.role === "user") {
      out.push({ kind: "user", id: nextId("u"), content: msg.content ?? "" });
    } else if (msg.role === "assistant") {
      if (msg.content) {
        out.push({ kind: "assistant", id: nextId("a"), content: msg.content });
      }
      for (const tc of msg.tool_calls ?? []) {
        if (tc.name === "ask_user") {
          out.push({
            kind: "awaiting_input",
            id: nextId("ai"),
            toolCallId: tc.id,
            question: String(tc.args?.question ?? ""),
            answer: null,
          });
          toolById.set(tc.id, out.length - 1);
        } else {
          out.push({
            kind: "tool",
            id: nextId("t"),
            toolCallId: tc.id,
            name: tc.name,
            args: tc.args,
            output: null,
            status: "running",
          });
          toolById.set(tc.id, out.length - 1);
        }
      }
    } else if (msg.role === "tool") {
      const idx = msg.tool_call_id ? toolById.get(msg.tool_call_id) : undefined;
      if (idx !== undefined) {
        const existing = out[idx];
        if (existing.kind === "tool") {
          out[idx] = { ...existing, output: msg.content ?? "", status: "done" };
        } else if (existing.kind === "awaiting_input") {
          out[idx] = { ...existing, answer: msg.content ?? "" };
        }
      }
    }
  }
  return out;
}

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [awaitingInput, setAwaitingInput] = useState<{ toolCallId: string; question: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const openAssistantIndex = useRef<number | null>(null);
  const toolIndexByCallId = useRef<Map<string, number>>(new Map());

  const [loadedSessionId, setLoadedSessionId] = useState(sessionId);
  if (sessionId !== loadedSessionId) {
    setLoadedSessionId(sessionId);
    setMessages([]);
    setLoading(true);
    setError(null);
    setAwaitingInput(null);
  }

  useEffect(() => {
    let cancelled = false;

    getSession(sessionId)
      .then((detail) => {
        if (cancelled) return;
        setMessages(historyToMessages(detail.messages));
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setMessages([]);
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const applyEvent = useCallback((event: ChatEvent) => {
    switch (event.type) {
      case "text": {
        setMessages((prev) => {
          const idx = openAssistantIndex.current;
          if (idx !== null && prev[idx]?.kind === "assistant") {
            const next = [...prev];
            const m = next[idx];
            if (m.kind === "assistant") next[idx] = { ...m, content: m.content + event.chunk };
            return next;
          }
          const next = [...prev, { kind: "assistant" as const, id: nextId("a"), content: event.chunk }];
          openAssistantIndex.current = next.length - 1;
          return next;
        });
        break;
      }
      case "tool_call": {
        openAssistantIndex.current = null;
        setMessages((prev) => {
          const next: UIMessage[] = [
            ...prev,
            {
              kind: "tool",
              id: nextId("t"),
              toolCallId: event.id,
              name: event.name,
              args: event.args,
              output: null,
              status: "running",
            },
          ];
          toolIndexByCallId.current.set(event.id, next.length - 1);
          return next;
        });
        break;
      }
      case "tool_result": {
        setMessages((prev) => {
          const idx = toolIndexByCallId.current.get(event.id);
          if (idx === undefined) return prev;
          const existing = prev[idx];
          if (existing.kind !== "tool") return prev;
          const next = [...prev];
          next[idx] = { ...existing, output: event.output, status: "done" };
          return next;
        });
        break;
      }
      case "awaiting_input": {
        openAssistantIndex.current = null;
        setAwaitingInput({ toolCallId: event.tool_call_id, question: event.question });
        setMessages((prev) => [
          ...prev,
          {
            kind: "awaiting_input",
            id: nextId("ai"),
            toolCallId: event.tool_call_id,
            question: event.question,
            answer: null,
          },
        ]);
        break;
      }
      case "compacted": {
        setMessages((prev) => [...prev, { kind: "compacted", id: nextId("c"), summary: event.summary }]);
        break;
      }
      case "error": {
        openAssistantIndex.current = null;
        setError(event.message);
        setMessages((prev) => [...prev, { kind: "error", id: nextId("e"), message: event.message }]);
        break;
      }
      case "usage":
      case "done":
        break;
    }
  }, []);

  const consume = useCallback(
    async (responsePromise: Promise<Response>) => {
      setIsStreaming(true);
      setError(null);
      openAssistantIndex.current = null;
      try {
        const response = await responsePromise;
        for await (const event of parseSSEStream(response)) {
          applyEvent(event);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setError("This session is busy — a turn is already in progress.");
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        setIsStreaming(false);
        openAssistantIndex.current = null;
      }
    },
    [applyEvent]
  );

  const send = useCallback(
    (text: string, provider?: string, model?: string) => {
      if (!text.trim()) return;
      setMessages((prev) => [...prev, { kind: "user", id: nextId("u"), content: text }]);
      return consume(sendMessage(sessionId, text, provider, model));
    },
    [consume, sessionId]
  );

  const answer = useCallback(
    (text: string) => {
      if (!awaitingInput) return;
      const toolCallId = awaitingInput.toolCallId;
      setAwaitingInput(null);
      setMessages((prev) =>
        prev.map((m) => (m.kind === "awaiting_input" && m.toolCallId === toolCallId ? { ...m, answer: text } : m))
      );
      return consume(resumeMessage(sessionId, toolCallId, text));
    },
    [awaitingInput, consume, sessionId]
  );

  return { messages, loading, isStreaming, awaitingInput, error, send, answer };
}
