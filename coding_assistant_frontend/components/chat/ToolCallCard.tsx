"use client";

import { useState } from "react";
import { ChevronRight, Loader2, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

function summarizeArgs(name: string, args: Record<string, unknown>): string {
  if (typeof args.command === "string") return args.command;
  if (typeof args.path === "string") return args.path;
  if (typeof args.pattern === "string") return args.pattern;
  const entries = Object.entries(args);
  return entries.length ? entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(" ") : name;
}

export function ToolCallCard({
  name,
  args,
  output,
  status,
}: {
  name: string;
  args: Record<string, unknown>;
  output: string | null;
  status: "running" | "done";
}) {
  const [open, setOpen] = useState(false);
  const label = summarizeArgs(name, args);

  return (
    <div className="w-full max-w-[85%] rounded-lg border bg-card/50 text-sm">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <ChevronRight className={cn("h-3.5 w-3.5 shrink-0 transition-transform text-muted-foreground", open && "rotate-90")} />
        <Terminal className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="font-mono text-xs font-medium text-foreground">{name}</span>
        <span className="truncate font-mono text-xs text-muted-foreground">{label}</span>
        {status === "running" && <Loader2 className="ml-auto h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />}
      </button>
      {open && (
        <div className="border-t px-3 py-2">
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-muted-foreground">
            {output ?? "…"}
          </pre>
        </div>
      )}
    </div>
  );
}
