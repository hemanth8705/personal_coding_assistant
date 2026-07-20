"use client";

import { useState } from "react";
import { SessionSidebar } from "@/components/sessions/SessionSidebar";
import { ConfigPanel } from "@/components/settings/ConfigPanel";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const [activeSession, setActiveSession] = useState("default");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);

  const { messages, loading, isStreaming, awaitingInput, error, send, answer } = useChat(activeSession);

  const handleSend = (text: string) => {
    send(text, provider || undefined, model || undefined);
    setSidebarRefreshKey((k) => k + 1);
  };

  const inputDisabled = isStreaming || loading || !!awaitingInput;

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <SessionSidebar activeSession={activeSession} onSelect={setActiveSession} refreshKey={sidebarRefreshKey} />

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-4 py-2.5">
          <div>
            <h1 className="text-sm font-semibold">Pi Coding Assistant</h1>
            <p className="text-xs text-muted-foreground">session: {activeSession}</p>
          </div>
          <ConfigPanel provider={provider} model={model} onChange={(p, m) => { setProvider(p); setModel(m); }} />
        </header>

        {loading ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">Loading…</div>
        ) : (
          <ChatWindow messages={messages} onAnswer={answer} awaitingToolCallId={awaitingInput?.toolCallId ?? null} />
        )}

        {error && !awaitingInput && (
          <div className="border-t bg-destructive/5 px-4 py-1.5 text-xs text-destructive">{error}</div>
        )}

        <ChatInput
          disabled={inputDisabled}
          placeholder={awaitingInput ? "Answer the question above to continue…" : undefined}
          onSend={handleSend}
        />
      </div>
    </div>
  );
}
