from fastapi import APIRouter, HTTPException

from pi import config as _config

from api.models import ConfigOut, ConfigSetRequest

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config():
    cfg = _config.load()
    return ConfigOut(
        provider=cfg["provider"],
        models=cfg["models"],
        sessions_dir=cfg["sessions_dir"],
        compact_threshold=cfg.get("compact_threshold", 30000),
        telegram_token=cfg.get("telegram_token"),
    )


@router.put("", response_model=ConfigOut)
def set_config(body: ConfigSetRequest):
    ok, msg = _config.set_value(body.key, body.value)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return get_config()
