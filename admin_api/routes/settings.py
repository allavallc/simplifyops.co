"""
Settings API — runtime config + session settings.

Config reads/writes go through the single config-ownership service `runtime_config` (story-44):
env-owned `config.yaml`, tracked per-env base, allowlisted structured writes. Mutations here
persist + return `restart_required`; the runtime reload is the explicit shared action
`POST /api/admin/runtime/restart` (decision B) — nothing restarts implicitly.

  GET  /api/admin/settings/state            — aggregate non-secret settings state (page/SPA)
  GET  /api/admin/settings/runtime          — runtime config metadata (redacted)
  PATCH/api/admin/settings/runtime          — provider/model/memory_url (allowlisted)
  GET/PATCH /api/admin/settings/approvals   — tool approvals mode
  GET/PATCH /api/admin/settings/session-health — session message cap (DB)
  GET/PATCH /api/admin/settings/default-timezone — org default tz (DB)
  POST /api/admin/runtime/restart           — the one shared explicit runtime restart
  POST/PATCH/DELETE /api/admin/runtime/mcp  — MCP server registrations
"""

import logging
from pathlib import Path

import runtime_config as rc
from audit import log_audit
from db import DEFAULT_SESSION_MESSAGE_CAP, DEFAULT_TIMEZONE, Db, get_setting, set_setting
from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

log = logging.getLogger("simplifyops-admin")
router = APIRouter(prefix="/api/admin/settings")
runtime_router = APIRouter(prefix="/api/admin/runtime")

APPROVALS_MODES = ("smart", "off", "manual")


def _require_admin_authority(admin: dict) -> None:
    if admin["authority"] not in ("super_admin", "admin"):
        raise HTTPException(403, "admin_required")


def _clear_session_mappings() -> None:
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hermes_session_mappings")
    log.info("settings: session mappings cleared after runtime config change")


# ── Read ──────────────────────────────────────────────────────────────────

@router.get("/state")
async def get_state(admin=Depends(require_admin)):
    """Aggregate non-secret settings state for the page — one call."""
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

    meta = rc.read_metadata()
    return {
        "health": [
            {"name": "Admin API", "detail": "http://localhost:3000", "ok": True},
            {"name": "Soul", "detail": str(soul), "ok": soul.exists()},
            {"name": "Memory URL (Hindsight)", "detail": "http://127.0.0.1:8888", "ok": hindsight_ok},
            {"name": "Postgres", "detail": "whitelist_app (unix socket)", "ok": db_ok},
        ],
        "runtime": {
            "provider": meta["provider"],
            "model": meta["model"],
            "memory_url": meta["memory_url"],
            "has_credentials": bool(meta["provider"]),
        },
        "approvals_mode": meta["approvals_mode"],
        "mcp_servers": meta["mcp_servers"],
        "env": meta["env"],
        "session_message_cap": session_cap,
        "default_timezone": default_tz,
        "approvals_modes": list(APPROVALS_MODES),
    }


@router.get("/runtime")
async def get_runtime(admin=Depends(require_admin)):
    return rc.read_metadata()


@router.get("/session-health")
async def get_session_health(admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            cap = get_setting(cur, "session_message_cap", DEFAULT_SESSION_MESSAGE_CAP)
    return {"session_message_cap": int(cap)}


# ── Runtime config mutation (persist; restart is the separate shared action) ─

class RuntimePatch(BaseModel):
    provider:   str | None = None
    model:      str | None = None
    memory_url: str | None = None


@router.patch("/runtime")
async def patch_runtime(body: RuntimePatch, admin=Depends(require_admin)):
    _require_admin_authority(admin)

    patch = {}
    if body.provider is not None:
        patch["model.provider"] = body.provider
    if body.model is not None:
        patch["model.default"] = body.model
    if body.memory_url is not None:
        patch["memory.url"] = body.memory_url
    if not patch:
        return {"ok": True, "changed": False, "restart_required": False}

    try:
        res = rc.apply(patch)
    except rc.ConfigError as e:
        raise HTTPException(400, str(e)) from None

    if not res["changed"]:
        return {"ok": True, "changed": False, "restart_required": False}

    log_audit(admin["email"], "settings_runtime_update",
              old_value=res["before"], new_value=res["after"])

    # provider/model change invalidates existing physical sessions
    if "model.provider" in patch or "model.default" in patch:
        _clear_session_mappings()

    return {"ok": True, "changed": True, "restart_required": res["restart_required"],
            "after": res["after"]}


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


# ── Organization default timezone (applied live — no runtime restart) ────────

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
        raise HTTPException(400, "invalid_timezone") from None

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
# smart = auto-run safe tools, pause only for risky ones; off = never pause;
# manual = always pause (stalls tools until an approval UI exists). Change needs a restart.

class ApprovalsPatch(BaseModel):
    mode: str


@router.get("/approvals")
async def get_approvals(admin=Depends(require_admin)):
    return {"mode": rc.read_metadata()["approvals_mode"]}


@router.patch("/approvals")
async def patch_approvals(body: ApprovalsPatch, admin=Depends(require_admin)):
    _require_admin_authority(admin)

    mode = body.mode.strip().lower()
    if mode not in APPROVALS_MODES:
        raise HTTPException(400, f"invalid_mode (allowed: {', '.join(APPROVALS_MODES)})")

    res = rc.apply({"approvals.mode": mode})
    if not res["changed"]:
        return {"ok": True, "changed": False, "restart_required": False, "mode": mode}

    log_audit(admin["email"], "settings_approvals_mode_update",
              old_value={"mode": res["before"]["approvals.mode"]}, new_value={"mode": mode})

    return {"ok": True, "changed": True, "restart_required": res["restart_required"], "mode": mode}


# ── Shared explicit runtime restart (decision B) ────────────────────────────

@runtime_router.post("/restart")
async def restart_runtime(admin=Depends(require_admin)):
    _require_admin_authority(admin)
    try:
        rc.restart_runtime()
    except Exception as e:
        log_audit(admin["email"], "runtime_restart_failed", new_value={"error": str(e)[:200]})
        raise HTTPException(500, "runtime_restart_failed") from None
    log_audit(admin["email"], "runtime_restart", new_value={"service": rc.RESTART_SERVICE})
    return {"ok": True, "restarted": True}


# ── MCP server registrations (non-secret structure; env-owned live config) ──

class McpServerBody(BaseModel):
    name: str
    command: str
    args: list[str] | None = None
    enabled: bool = True
    env: dict[str, str] | None = None


class McpTogglePatch(BaseModel):
    enabled: bool


@runtime_router.post("/mcp")
async def upsert_mcp_server(body: McpServerBody, admin=Depends(require_admin)):
    _require_admin_authority(admin)
    try:
        res = rc.set_mcp_server(body.name, command=body.command, args=body.args,
                                enabled=body.enabled, env=body.env)
    except rc.ConfigError as e:
        raise HTTPException(400, str(e)) from None
    log_audit(admin["email"], "settings_mcp_upsert", new_value={"server": body.name,
              "enabled": body.enabled})
    return {"ok": True, **res}


@runtime_router.patch("/mcp/{name}")
async def toggle_mcp_server(name: str, body: McpTogglePatch, admin=Depends(require_admin)):
    _require_admin_authority(admin)
    try:
        res = rc.toggle_mcp_server(name, body.enabled)
    except rc.ConfigError as e:
        raise HTTPException(404, str(e)) from None
    log_audit(admin["email"], "settings_mcp_toggle", new_value={"server": name, "enabled": body.enabled})
    return {"ok": True, **res}


@runtime_router.delete("/mcp/{name}")
async def delete_mcp_server(name: str, admin=Depends(require_admin)):
    _require_admin_authority(admin)
    try:
        res = rc.remove_mcp_server(name)
    except rc.ConfigError as e:
        raise HTTPException(404, str(e)) from None
    log_audit(admin["email"], "settings_mcp_delete", new_value={"server": name})
    return {"ok": True, **res}
