"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { getConfig } from "@/lib/api";

export function ConfigPanel({
  provider,
  model,
  onChange,
}: {
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
}) {
  const [defaults, setDefaults] = useState<Record<string, string>>({});

  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setDefaults(cfg.models);
        if (!provider) onChange(cfg.provider, cfg.models[cfg.provider] ?? "");
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex items-center gap-2">
      <Select
        value={provider}
        onValueChange={(p) => p && onChange(p, defaults[p] ?? "")}
      >
        <SelectTrigger size="sm" className="w-28">
          <SelectValue placeholder="Provider" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="gemini">Gemini</SelectItem>
          <SelectItem value="openai">OpenAI</SelectItem>
        </SelectContent>
      </Select>
      <Input
        value={model}
        onChange={(e) => onChange(provider, e.target.value)}
        placeholder="model"
        className="h-8 w-48 text-xs"
      />
    </div>
  );
}
