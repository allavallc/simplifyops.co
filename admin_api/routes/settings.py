"""
Settings API — core runtime settings.
GET /api/admin/settings/runtime      — read provider, model, memory URL
PATCH /api/admin/settings/runtime    — save + restart runtime + clear sessions
PATCH /api/admin/settings/session-health — save session message cap
"""

import logging
import subprocess
import tempfile
from pathlib import Path

import yaml
from audit import log_audit
from db import DEFAULT_SESSION_MESSAGE_CAP, DEFAULT_TIMEZONE, Db, get_setting, set_setting
from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

log = logging.getLogger("simplifyops-admin")
router = APIRouter(prefix="/api/admin/settings")

HERMES_CONFIG = Path("/home/pi/.hermes/profiles/simplifyops/config.yaml")


def _read_config() -> dict:
    if not HERMES_CONFIG.exists():
        return {}
    return yaml.safe_load(HERMES_CONFIG.read_text()) or {}


def _write_config(cfg: dict) -> None:
    """Atomic write — write to temp file then rename."""
    tmp = Path(tempfile.mktemp(dir=HERMES_CONFIG.parent, prefix=".config.yaml."))
    try:
        tmp.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True))
        tmp.replace(HERMES_CONFIG)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _restart_runtime() -> None:
    result = subprocess.run(
        ["sudo", "/bin/systemctl", "restart", "simplifyops-agent-runtime.service"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Runtime restart failed: {result.stderr[:200]}")
    log.info("settings: runtime restarted")


def _clear_session_mappings() -> None:
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hermes_session_mappings")
    log.info("settings: session mappings cleared after runtime config change")


# ── Read ──────────────────────────────────────────────────────────────────

@router.get("/state")
async def get_state(admin=Depends(require_admin)):
    """Aggregate non-secret settings state for the SPA — one call."""
    import urllib.request

    profile_root = Path("/home/pi/.hermes/profiles/simplifyops")
    soul = profile_root / "SOUL.md"

    db_ok = False
    session_cap = DEFAULT_SESSION_MESSAGE_CAP
    default_tz = DEFAULT_TIMEZONE
    try:
        with Db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1"); db_ok = True
                session_cap = int(get_setting(cur, "session_message_cap", DEFAULT_SESSION_MESSAGE_CAP))
                default_tz = get_setting(cur, "default_timezone", DEFAULT_TIMEZONE)
    except Exception:
        pass

    hindsight_ok = False
    try:
        urllib.request.urlopen("http://127.0.0.1:8888/health", timeout=2); hindsight_ok = True
    except Exception:
        pass

    cfg = _read_config()
    return {
        "health": [
            {"name": "Admin API", "detail": "http://localhost:3000", "ok": True},
            {"name": "Soul", "detail": str(soul), "ok": soul.exists()},
            {"name": "Memory URL (Hindsight)", "detail": "http://127.0.0.1:8888", "ok": hindsight_ok},
            {"name": "Postgres", "detail": "whitelist_app (unix socket)", "ok": db_ok},
        ],
        "runtime": {
            "provider": cfg.get("model", {}).get("provider"),
            "model": cfg.get("model", {}).get("default"),
            "memory_url": cfg.get("memory", {}).get("url"),
            "has_credentials": bool(cfg.get("model", {}).get("provider")),
        },
        "approvals_mode": cfg.get("approvals", {}).get("mode"),
        "session_message_cap": session_cap,
        "default_timezone": default_tz,
        "approvals_modes": list(APPROVALS_MODES),
    }


@router.get("/runtime")
async def get_runtime(admin=Depends(require_admin)):
    cfg = _read_config()
    model_cfg = cfg.get("model", {})
    memory_cfg = cfg.get("memory", {})
    return {
        "provider":   model_cfg.get("provider"),
        "model":      model_cfg.get("default"),
        "memory_url": memory_cfg.get("url"),
    }


@router.get("/session-health")
async def get_session_health(admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            cap = get_setting(cur, "session_message_cap", DEFAULT_SESSION_MESSAGE_CAP)
    return {"session_message_cap": int(cap)}


# ── Mutation ──────────────────────────────────────────────────────────────

class RuntimePatch(BaseModel):
    provider:   str | None = None
    model:      str | None = None
    memory_url: str | None = None


@router.patch("/runtime")
async def patch_runtime(body: RuntimePatch, admin=Depends(require_admin)):
    if admin["authority"] not in ("super_admin", "admin"):
        raise HTTPException(403, "admin_required")

    cfg = _read_config()
    before = {
        "provider": cfg.get("model", {}).get("provider"),
        "model":    cfg.get("model", {}).get("default"),
        "memory_url": cfg.get("memory", {}).get("url"),
    }

    cfg.setdefault("model", {})
    cfg.setdefault("memory", {})

    if body.provider is not None:
        cfg["model"]["provider"] = body.provider
    if body.model is not None:
        cfg["model"]["default"] = body.model
    if body.memory_url is not None:
        cfg["memory"]["url"] = body.memory_url

    after = {
        "provider": cfg["model"].get("provider"),
        "model":    cfg["model"].get("default"),
        "memory_url": cfg["memory"].get("url"),
    }

    if before == after:
        return {"ok": True, "changed": False, "restarted": False}

    _write_config(cfg)
    log.info("settings: runtime config updated provider=%s model=%s", after["provider"], after["model"])

    log_audit(admin["email"], "settings_runtime_update",
              old_value=before, new_value=after)

    _restart_runtime()
    _clear_session_mappings()

    return {"ok": True, "changed": True, "restarted": True,
            "after": after}


class SessionHealthPatch(BaseModel):
    session_message_cap: int


@router.patch("/session-health")
async def patch_session_health(body: SessionHealthPatch, admin=Depends(require_admin)):
    if body.session_message_cap < 1:
        raise HTTPException(400, "cap_must_be_positive")

    with Db() as conn:
        with conn.cursor() as cur:
            old_val = int(get_setting(cur, "session_message_cap", DEFAULT_SESSION_MESSAGE_CAP))

        with conn.cursor() as cur:
            set_setting(cur, "session_message_cap", body.session_message_cap, admin["email"])

    log_audit(admin["email"], "settings_session_cap_update",
              old_value={"session_message_cap": old_val},
              new_value={"session_message_cap": body.session_message_cap})

    return {"ok": True, "session_message_cap": body.session_message_cap}


# ── Organization default timezone ───────────────────────────────────────────
# A person with no timezone inherits this. Read live by the gateway from
# admin_settings on every lookup — no runtime restart required.

class DefaultTimezonePatch(BaseModel):
    default_timezone: str


@router.get("/default-timezone")
async def get_default_timezone(admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            tz = get_setting(cur, "default_timezone", DEFAULT_TIMEZONE)
    return {"default_timezone": tz}


@router.patch("/default-timezone")
async def patch_default_timezone(body: DefaultTimezonePatch, admin=Depends(require_admin)):
    tz = body.default_timezone.strip()
    if not tz:
        raise HTTPException(400, "timezone_required")
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz)  # validate it's a real IANA zone
    except Exception:
        raise HTTPException(400, "invalid_timezone")

    with Db() as conn:
        with conn.cursor() as cur:
            old_val = get_setting(cur, "default_timezone", None)
        with conn.cursor() as cur:
            set_setting(cur, "default_timezone", tz, admin["email"])

    log_audit(admin["email"], "settings_default_timezone_update",
              old_value={"default_timezone": old_val},
              new_value={"default_timezone": tz})

    return {"ok": True, "default_timezone": tz}


# ── Tool approvals (approvals.mode) ─────────────────────────────────────────
# smart  = auto-run safe tools, pause only for risky ones
# off    = never pause
# manual = always pause for human approval (stalls tools until an approval UI exists)
# Changing the mode restarts the runtime (config re-read) but does NOT clear
# session mappings — the mode does not invalidate conversation continuity.

APPROVALS_MODES = ("smart", "off", "manual")


class ApprovalsPatch(BaseModel):
    mode: str


@router.get("/approvals")
async def get_approvals(admin=Depends(require_admin)):
    cfg = _read_config()
    return {"mode": cfg.get("approvals", {}).get("mode")}


@router.patch("/approvals")
async def patch_approvals(body: ApprovalsPatch, admin=Depends(require_admin)):
    if admin["authority"] not in ("super_admin", "admin"):
        raise HTTPException(403, "admin_required")

    mode = body.mode.strip().lower()
    if mode not in APPROVALS_MODES:
        raise HTTPException(400, f"invalid_mode (allowed: {', '.join(APPROVALS_MODES)})")

    cfg = _read_config()
    before = cfg.get("approvals", {}).get("mode")
    if before == mode:
        return {"ok": True, "changed": False, "restarted": False, "mode": mode}

    cfg.setdefault("approvals", {})
    cfg["approvals"]["mode"] = mode
    _write_config(cfg)
    log.info("settings: approvals.mode %s -> %s", before, mode)

    log_audit(admin["email"], "settings_approvals_mode_update",
              old_value={"mode": before}, new_value={"mode": mode})

    _restart_runtime()

    return {"ok": True, "changed": True, "restarted": True, "mode": mode}
