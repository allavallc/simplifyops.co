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

import people_service
import runtime_config as rc
import soul_file as sf
from audit import log_audit
from db import DEFAULT_SESSION_MESSAGE_CAP, DEFAULT_TIMEZONE, Db, get_setting, set_setting
from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

log = logging.getLogger("simplifyops-admin")
router = APIRouter(prefix="/api/admin/settings")
runtime_router = APIRouter(prefix="/api/admin/runtime")

APPROVALS_MODES = ("smart", "off", "manual")


def _require_admin_authority(admin: dict) -> None:
    if admin["authority"] not in ("super_admin", "admin"):
        raise HTTPException(403, "admin_required")


def _require_super_admin(admin: dict) -> None:
    if admin["authority"] != "super_admin":
        raise HTTPException(403, "super_admin_required")


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


# ── Identity file (soul) download / upload (super-admin) ────────────────────
# The soul file IS the agent's personality (loaded verbatim as SOUL.md). Upload replaces
# souls/soul.md and restarts the runtime so the new soul loads. Content is never logged.

class SoulUpload(BaseModel):
    content: str
    filename: str | None = None


@router.get("/identity-file/download")
async def download_identity_file(admin=Depends(require_admin)):
    _require_super_admin(admin)
    return PlainTextResponse(
        sf.read(), media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="soul.md"'},
    )


@router.post("/identity-file/upload")
async def upload_identity_file(body: SoulUpload, admin=Depends(require_admin)):
    _require_super_admin(admin)
    try:
        meta = sf.write_atomic(body.content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None

    log_audit(admin["email"], "settings_identity_file_upload",
              new_value={"filename": body.filename, "bytes": meta["bytes"], "sha256": meta["sha256"]})

    restarted = True
    try:
        rc.restart_runtime()  # owner: restart on upload so the new soul is loaded
    except Exception as e:
        restarted = False
        log.error("identity-file upload: runtime restart failed: %s", e)
    return {"ok": True, "bytes": meta["bytes"], "restarted": restarted}


# ── Admin contact (primary/secondary from active admins; stored in admin_settings) ──

CONTACT_PRIMARY_KEY = "admin_contact_primary"
CONTACT_SECONDARY_KEY = "admin_contact_secondary"


class AdminContactPatch(BaseModel):
    primary: str
    secondary: str | None = None


@router.get("/admin-contact")
async def get_admin_contact(admin=Depends(require_admin)):
    with Db() as conn:
        options = [r["person_email"] for r in people_service.active_admin_emails(conn)]
        with conn.cursor() as cur:
            primary = get_setting(cur, CONTACT_PRIMARY_KEY, None) or None
            secondary = get_setting(cur, CONTACT_SECONDARY_KEY, None) or None
    return {"primary": primary, "secondary": secondary, "options": options}


@router.patch("/admin-contact")
async def patch_admin_contact(body: AdminContactPatch, admin=Depends(require_admin)):
    _require_admin_authority(admin)
    primary = (body.primary or "").strip()
    secondary = (body.secondary or "").strip() or None

    with Db() as conn:
        valid = {r["person_email"] for r in people_service.active_admin_emails(conn)}
        if primary not in valid:
            raise HTTPException(400, "primary_must_be_active_admin")
        if secondary is not None and secondary not in valid:
            raise HTTPException(400, "secondary_must_be_active_admin")
        if secondary is not None and secondary == primary:
            raise HTTPException(400, "secondary_must_differ_from_primary")

        with conn.cursor() as cur:
            old = {"primary": get_setting(cur, CONTACT_PRIMARY_KEY, None) or None,
                   "secondary": get_setting(cur, CONTACT_SECONDARY_KEY, None) or None}
        with conn.cursor() as cur:
            set_setting(cur, CONTACT_PRIMARY_KEY, primary, admin["email"])
            set_setting(cur, CONTACT_SECONDARY_KEY, secondary or "", admin["email"])

    log_audit(admin["email"], "settings_admin_contact_update",
              old_value=old, new_value={"primary": primary, "secondary": secondary})
    return {"ok": True, "primary": primary, "secondary": secondary}


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
