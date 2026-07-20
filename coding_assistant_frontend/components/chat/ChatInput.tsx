"use client";

import { useState } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  disabled,
  placeholder,
  onSend,
}: {
  disabled: boolean;
  placeholder?: string;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="flex items-end gap-2 border-t bg-background p-3">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder ?? "Message Pi…"}
        disabled={disabled}
        className="min-h-11 max-h-40 flex-1 resize-none"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <Button size="icon" onClick={submit} disabled={disabled || !text.trim()}>
        <ArrowUp className="h-4 w-4" />
      </Button>
    </div>
  );
}
