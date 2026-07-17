import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".pi" / "config.json"

DEFAULTS: dict = {
    "provider": "gemini",
    "models": {
        "gemini": "gemini-2.0-flash",
        "openai": "gpt-4o-mini",
    },
    "sessions_dir": "sessions",
    "compact_threshold": 30000,
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        cfg = {**DEFAULTS, "models": dict(DEFAULTS["models"])}
        save(cfg)
        return cfg
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = {**DEFAULTS, **saved}
        cfg["models"] = {**DEFAULTS["models"], **saved.get("models", {})}
        return cfg
    except (json.JSONDecodeError, OSError):
        return {**DEFAULTS, "models": dict(DEFAULTS["models"])}


def save(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def set_value(key: str, value: str) -> tuple[bool, str]:
    cfg = load()
    if key == "provider":
        if value not in ("gemini", "openai"):
            return False, f"provider must be 'gemini' or 'openai', got {value!r}"
        cfg["provider"] = value
    elif key == "sessions_dir":
        cfg["sessions_dir"] = value
    elif key.startswith("model."):
        provider_name = key.split(".", 1)[1]
        cfg["models"][provider_name] = value
    elif key == "compact_threshold":
        try:
            cfg["compact_threshold"] = int(value)
        except ValueError:
            return False, f"compact_threshold must be an integer, got {value!r}"
    elif key == "telegram_token":
        cfg["telegram_token"] = value
    else:
        return False, f"Unknown key {key!r}. Valid: provider, sessions_dir, model.<provider>, compact_threshold, telegram_token"
    save(cfg)
    return True, f"Set {key} = {value!r}"
