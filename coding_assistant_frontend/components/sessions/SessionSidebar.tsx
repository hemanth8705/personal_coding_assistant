"use client";

import { useEffect, useState } from "react";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { createSession, deleteSession, listSessions } from "@/lib/api";
import type { SessionInfo } from "@/lib/types";

export function SessionSidebar({
  activeSession,
  onSelect,
  refreshKey,
}: {
  activeSession: string;
  onSelect: (name: string) => void;
  refreshKey: number;
}) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    listSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  };

  useEffect(refresh, [refreshKey]);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setBusy(true);
    try {
      await createSession(name);
      setDialogOpen(false);
      setNewName("");
      refresh();
      onSelect(name);
    } catch {
      // session may already exist — just switch to it
      onSelect(name);
      setDialogOpen(false);
      setNewName("");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(name);
      refresh();
      if (name === activeSession) onSelect("default");
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-full w-60 flex-col border-r bg-muted/30">
      <div className="flex items-center justify-between px-3 py-3">
        <span className="text-sm font-semibold">Sessions</span>
        <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setDialogOpen(true)}>
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>
      <ScrollArea className="flex-1 px-2">
        <div className="flex flex-col gap-0.5 pb-2">
          {sessions.length === 0 && (
            <p className="px-2 py-1 text-xs text-muted-foreground">No sessions yet.</p>
          )}
          {sessions.map((s) => (
            <button
              key={s.name}
              onClick={() => onSelect(s.name)}
              className={cn(
                "group flex items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent",
                s.name === activeSession && "bg-accent font-medium"
              )}
            >
              <span className="truncate">{s.name}</span>
              <span className="flex items-center gap-1">
                <span className="text-xs text-muted-foreground group-hover:hidden">{s.message_count}</span>
                <Trash2
                  className="hidden h-3.5 w-3.5 text-muted-foreground hover:text-destructive group-hover:block"
                  onClick={(e) => handleDelete(s.name, e)}
                />
              </span>
            </button>
          ))}
        </div>
      </ScrollArea>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New session</DialogTitle>
          </DialogHeader>
          <Input
            autoFocus
            placeholder="session name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <DialogFooter>
            <Button onClick={handleCreate} disabled={busy || !newName.trim()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
