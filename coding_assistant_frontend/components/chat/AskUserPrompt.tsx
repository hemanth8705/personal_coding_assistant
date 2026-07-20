"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function AskUserPrompt({
  question,
  answer,
  onAnswer,
}: {
  question: string;
  answer: string | null;
  onAnswer?: (answer: string) => void;
}) {
  const [text, setText] = useState("");
  const pending = answer === null && !!onAnswer;

  return (
    <div className="w-full max-w-[85%] rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
      <div className="flex items-start gap-2">
        <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
        <p className="font-medium text-foreground">{question}</p>
      </div>

      {answer !== null ? (
        <p className="mt-2 whitespace-pre-wrap pl-6 text-muted-foreground">
          <span className="font-medium text-foreground">You: </span>
          {answer}
        </p>
      ) : pending ? (
        <form
          className="mt-3 flex flex-col gap-2 pl-6"
          onSubmit={(e) => {
            e.preventDefault();
            const trimmed = text.trim();
            if (trimmed) onAnswer?.(trimmed);
          }}
        >
          <Textarea
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your answer…"
            className="min-h-16 bg-background"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const trimmed = text.trim();
                if (trimmed) onAnswer?.(trimmed);
              }
            }}
          />
          <Button type="submit" size="sm" className="self-end" disabled={!text.trim()}>
            Answer
          </Button>
        </form>
      ) : null}
    </div>
  );
}
