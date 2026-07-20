"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { UIMessage } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { ToolCallCard } from "./ToolCallCard";
import { AskUserPrompt } from "./AskUserPrompt";

export function ChatWindow({
  messages,
  onAnswer,
  awaitingToolCallId,
}: {
  messages: UIMessage[];
  onAnswer: (answer: string) => void;
  awaitingToolCallId: string | null;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
        <Sparkles className="h-8 w-8" />
        <p className="text-sm">Ask Pi to explore, edit, or run something in this workspace.</p>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-3 p-4">
        {messages.map((m) => {
          switch (m.kind) {
            case "user":
              return <MessageBubble key={m.id} role="user" content={m.content} />;
            case "assistant":
              return <MessageBubble key={m.id} role="assistant" content={m.content} />;
            case "tool":
              return (
                <ToolCallCard key={m.id} name={m.name} args={m.args} output={m.output} status={m.status} />
              );
            case "awaiting_input":
              return (
                <AskUserPrompt
                  key={m.id}
                  question={m.question}
                  answer={m.answer}
                  onAnswer={m.toolCallId === awaitingToolCallId ? onAnswer : undefined}
                />
              );
            case "compacted":
              return (
                <div key={m.id} className="mx-auto max-w-[85%] rounded-md bg-muted px-3 py-1.5 text-xs text-muted-foreground">
                  Context compacted — {m.summary}
                </div>
              );
            case "error":
              return (
                <div
                  key={m.id}
                  className="flex max-w-[85%] items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{m.message}</span>
                </div>
              );
            default:
              return null;
          }
        })}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
