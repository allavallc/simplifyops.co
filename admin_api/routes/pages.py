"""Server-rendered admin pages (Jinja).

Extracted from main.py (story-35) so main.py is a pure composition root. Every
server-rendered admin page (login + /admin/*) lives here as one APIRouter, with
the templates env and the render/guard helpers.
"""

import os
from pathlib import Path

import people_service as svc
import psycopg2.extras
from db import DEFAULT_SESSION_MESSAGE_CAP, DEFAULT_TIMEZONE, Db, get_setting
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates as _Jinja2Templates

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent  # admin_api/
_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=True,
    cache_size=0,
)
templates = _Jinja2Templates(env=_jinja_env)


def render(request: Request, template: str, ctx: dict):
    ctx.pop("request", None)
    # Compute the active nav item (top-level section) for sidebar highlighting
    path = request.url.path
    active = "/admin"
    if path.startswith("/admin/"):
        active = "/" + "/".join(path.split("/")[1:3])  # e.g. /admin/people
    ctx.setdefault("active_page", active)
    return templates.TemplateResponse(request, template, ctx)

def _user(request: Request) -> dict | None:
    email = request.session.get("admin_email")
    if not email:
        return None
    return {"email": email, "authority": request.session.get("authority")}


def _actor(request: Request) -> dict:
    """Acting admin for people_service calls (needs id for the self-deactivation guard)."""
    return {
        "email": request.session.get("admin_email"),
        "authority": request.session.get("authority"),
        "id": request.session.get("admin_id"),
    }


def _guard(request: Request):
    """Return redirect if not signed in, else None."""
    if not request.session.get("admin_email"):
        return RedirectResponse("/")
    return None


# ---------------------------------------------------------------------------
# Admin pages
# ---------------------------------------------------------------------------

@router.get("/")
async def index(request: Request, error: str = None):
    if request.session.get("admin_email"):
        return RedirectResponse("/admin")
    return render(request, "login.html", {"request": request, "error": error})


@router.get("/admin")
async def admin_index(request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::int FROM contact_requests WHERE status='pending'")
            pending_count = cur.fetchone()[0]
    return render(request, "admin/index.html", {
        "request": request, "user": _user(request), "pending_count": pending_count,
    })


@router.get("/admin/people")
async def people_index(request: Request, status: str = "active"):
    if g := _guard(request): return g
    with Db() as conn:
        status, people = svc.list_index(conn, status)
    return render(request, "admin/people/index.html", {
        "request": request, "user": _user(request), "people": people, "status": status,
    })


@router.get("/admin/people/new")
async def person_new(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/people/form.html", {
        "request": request, "user": _user(request), "is_edit": False,
        "person": {"can_converse": True, "can_influence": True},
        "authorities": svc.AUTHORITIES, "timezones": svc.TIMEZONES,
    })


@router.post("/admin/people/new")
async def person_create(request: Request):
    if g := _guard(request): return g
    form = await request.form()
    values = {
        "first_name": str(form.get("first_name", "")).strip(),
        "last_name": str(form.get("last_name", "")).strip(),
        "person_email": str(form.get("primary_email", "")).strip().lower(),
        "authority": form.get("authority", "member"),
        "can_converse": bool(form.get("can_converse")),
        "can_influence": bool(form.get("can_influence")),
        "timezone": str(form.get("timezone", "")).strip(),
        "notes": str(form.get("notes", "")).strip(),
    }
    try:
        with Db() as conn:
            svc.create_person(
                conn, _actor(request),
                first_name=values["first_name"], last_name=values["last_name"],
                primary_email=values["person_email"], authority=values["authority"],
                can_converse=values["can_converse"], can_influence=values["can_influence"],
                timezone=values["timezone"] or None, notes=values["notes"] or None)
    except svc.PeopleError as e:
        return render(request, "admin/people/form.html", {
            "request": request, "user": _user(request), "person": values, "is_edit": False,
            "authorities": svc.AUTHORITIES, "timezones": svc.TIMEZONES, "error": e.code,
        })
    return RedirectResponse(f"/admin/people/{values['person_email']}", status_code=303)


@router.get("/admin/people/{email}/edit")
async def person_edit(email: str, request: Request):
    if g := _guard(request): return g
    try:
        with Db() as conn:
            person = svc.get_detail(conn, svc.person_id_for_email(conn, email))
    except svc.PeopleError:
        return RedirectResponse("/admin/people")
    return render(request, "admin/people/form.html", {
        "request": request, "user": _user(request), "person": person, "is_edit": True,
        "authorities": svc.AUTHORITIES, "timezones": svc.TIMEZONES,
    })


@router.post("/admin/people/{email}/edit")
async def person_update(email: str, request: Request):
    if g := _guard(request): return g
    form = await request.form()
    values = {
        "first_name": str(form.get("first_name", "")).strip(),
        "last_name": str(form.get("last_name", "")).strip(),
        "person_email": email.lower(),
        "authority": form.get("authority", "member"),
        "can_converse": bool(form.get("can_converse")),
        "can_influence": bool(form.get("can_influence")),
        "timezone": str(form.get("timezone", "")).strip(),
        "notes": str(form.get("notes", "")).strip(),
    }
    try:
        with Db() as conn:
            pid = svc.person_id_for_email(conn, email)
            svc.update_person(
                conn, _actor(request), pid,
                first_name=values["first_name"], last_name=values["last_name"],
                authority=values["authority"], can_converse=values["can_converse"],
                can_influence=values["can_influence"],
                timezone=values["timezone"] or None, notes=values["notes"] or None)
    except svc.PeopleError as e:
        return render(request, "admin/people/form.html", {
            "request": request, "user": _user(request), "person": values, "is_edit": True,
            "authorities": svc.AUTHORITIES, "timezones": svc.TIMEZONES, "error": e.code,
        })
    return RedirectResponse(f"/admin/people/{email.lower()}", status_code=303)


@router.post("/admin/people/{email}/deactivate")
async def person_deactivate(email: str, request: Request):
    if g := _guard(request): return g
    form = await request.form()
    try:
        with Db() as conn:
            pid = svc.person_id_for_email(conn, email)
            svc.deactivate_person(conn, _actor(request), pid, str(form.get("confirm", "")))
    except svc.PeopleError as e:
        return RedirectResponse(f"/admin/people/{email.lower()}?error={e.code}", status_code=303)
    return RedirectResponse("/admin/people", status_code=303)


@router.post("/admin/people/{email}/activate")
async def person_activate(email: str, request: Request):
    if g := _guard(request): return g
    try:
        with Db() as conn:
            svc.activate_person(conn, _actor(request), svc.person_id_for_email(conn, email))
    except svc.PeopleError:
        pass
    return RedirectResponse(f"/admin/people/{email.lower()}", status_code=303)


@router.post("/admin/people/{email}/identities")
async def person_identity_add(email: str, request: Request):
    if g := _guard(request): return g
    form = await request.form()
    try:
        with Db() as conn:
            pid = svc.person_id_for_email(conn, email)
            svc.add_identity(conn, _actor(request), pid,
                             str(form.get("identity_type", "")), str(form.get("value", "")))
    except svc.PeopleError as e:
        return RedirectResponse(f"/admin/people/{email.lower()}?error={e.code}", status_code=303)
    return RedirectResponse(f"/admin/people/{email.lower()}", status_code=303)


@router.post("/admin/people/{email}/identities/{identity_id}/delete")
async def person_identity_delete(email: str, identity_id: int, request: Request):
    if g := _guard(request): return g
    try:
        with Db() as conn:
            pid = svc.person_id_for_email(conn, email)
            svc.delete_identity(conn, _actor(request), pid, identity_id)
    except svc.PeopleError as e:
        return RedirectResponse(f"/admin/people/{email.lower()}?error={e.code}", status_code=303)
    return RedirectResponse(f"/admin/people/{email.lower()}", status_code=303)


@router.get("/admin/people/{email}")
async def person_view(email: str, request: Request):
    if g := _guard(request): return g
    try:
        with Db() as conn:
            person = svc.get_detail(conn, svc.person_id_for_email(conn, email))
    except svc.PeopleError:
        return RedirectResponse("/admin/people")
    return render(request, "admin/people/view.html", {
        "request": request, "user": _user(request), "person": person,
        "identity_types": svc.IDENTITY_TYPES, "error": request.query_params.get("error"),
    })


@router.get("/admin/inbox")
async def inbox_page(request: Request, status: str = "pending"):
    if g := _guard(request): return g
    where = "" if status == "all" else "WHERE status=%s"
    params = [] if status == "all" else [status]
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT id, request_id, channel, from_id, from_name, chat_id,
                       left(message_text,300) AS message_preview, status, created_at
                FROM contact_requests {where} ORDER BY created_at DESC
            """, params)
            reqs = list(cur.fetchall())
    return render(request, "admin/inbox.html", {
        "request": request, "user": _user(request),
        "requests": reqs, "current_filter": status,
    })


@router.post("/admin/inbox/{req_id}/approve")
async def inbox_approve_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/approve",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@router.post("/admin/inbox/{req_id}/reject")
async def inbox_reject_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/reject",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@router.post("/admin/inbox/{req_id}/ignore")
async def inbox_ignore_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/ignore",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@router.get("/admin/activity")
async def activity_page(request: Request, status: str = "all"):
    if g := _guard(request): return g
    where = "" if status == "all" else "WHERE w.status=%s"
    params = [100] if status == "all" else [status, 100]
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT w.id, w.request_id, w.status, w.attempt_count, w.error_summary,
                       left(w.reply_text,120) AS reply_preview, w.created_at,
                       r.channel, r.from_id, r.from_name,
                       left(r.message_text,200) AS message_preview
                FROM work_items w JOIN requests r ON r.id=w.request_id
                {where} ORDER BY w.created_at DESC LIMIT %s
            """, params)
            items = list(cur.fetchall())
    return render(request, "admin/activity.html", {
        "request": request, "user": _user(request),
        "items": items, "current_filter": status,
    })


@router.get("/admin/settings")
async def settings_page(request: Request):
    if g := _guard(request): return g
    import urllib.request

    import yaml

    # Health checks — name / detail / ok
    profile_root = Path("/home/pi/.hermes/profiles/simplifyops")
    soul_path = profile_root / "SOUL.md"

    db_ok = False
    try:
        with Db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                db_ok = True
    except Exception:
        pass

    hindsight_ok = False
    try:
        urllib.request.urlopen("http://127.0.0.1:8888/health", timeout=2)
        hindsight_ok = True
    except Exception:
        pass

    health = [
        {"name": "Admin API", "detail": "http://localhost:3000", "ok": True},
        {"name": "Soul", "detail": str(soul_path), "ok": soul_path.exists()},
        {"name": "Memory URL (Hindsight)", "detail": "http://127.0.0.1:8888", "ok": hindsight_ok},
        {"name": "Postgres", "detail": "whitelist_app (unix socket)", "ok": db_ok},
    ]

    # Runtime config (non-secret fields only)
    runtime = {"provider": None, "model": None, "memory_url": None, "has_credentials": False}
    try:
        config_path = Path("/home/pi/.hermes/profiles/simplifyops/config.yaml")
        if config_path.exists():
            cfg = yaml.safe_load(config_path.read_text())
            runtime["provider"] = cfg.get("model", {}).get("provider")
            runtime["model"] = cfg.get("model", {}).get("default")
            runtime["memory_url"] = cfg.get("memory", {}).get("url")
            runtime["has_credentials"] = bool(cfg.get("model", {}).get("provider"))
            runtime["approvals_mode"] = cfg.get("approvals", {}).get("mode")
    except Exception:
        pass

    # Session cap + org default timezone
    settings = {}
    with Db() as conn:
        with conn.cursor() as cur:
            settings["session_message_cap"] = int(
                get_setting(cur, "session_message_cap", DEFAULT_SESSION_MESSAGE_CAP))
            settings["default_timezone"] = get_setting(
                cur, "default_timezone", DEFAULT_TIMEZONE)

    # File locations (presence/status only — no contents)
    profile_root = Path("/home/pi/.hermes/profiles/simplifyops")
    files = {
        "runtime_home_status": "Present" if profile_root.exists() else "Missing",
        "runtime_config_status": "Present" if (profile_root / "config.yaml").exists() else "Missing",
        "soul_file_status": "Present" if (profile_root / "SOUL.md").exists() else "Missing",
        "base_config_status": "N/A (bare metal — no tracked template)",
    }

    # Channels (non-secret)
    import os as _os
    channels = {
        "telegram": {
            "has_token": bool(_os.environ.get("TELEGRAM_BOT_TOKEN")),
            "bot_username": None,
        }
    }

    # Workspace connection
    workspace = {"connected": False}
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            email = request.session.get("admin_email")
            cur.execute("SELECT scopes, token_expiry FROM google_tokens WHERE person_email=%s", (email,))
            row = cur.fetchone()
            if row:
                workspace = {
                    "connected": True,
                    "scopes": [s.split("/")[-1] for s in (row["scopes"] or [])],
                    "token_expiry": row["token_expiry"].strftime("%Y-%m-%d %H:%M UTC") if row["token_expiry"] else None,
                }

    # Admin contact (placeholder until admin_contact_settings table is built)
    admin_contact = {"primary": request.session.get("admin_email"), "secondary": None}

    # Tools summary (placeholder)
    tools = {"mcp_health": None, "active_count": None}

    return render(request, "admin/settings.html", {
        "user": _user(request),
        "health": health,
        "runtime": runtime,
        "settings": settings,
        "files": files,
        "channels": channels,
        "workspace": workspace,
        "admin_contact": admin_contact,
        "tools": tools,
    })


@router.get("/admin/activity/{item_id}")
async def activity_detail_page(item_id: int, request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT w.*, r.channel, r.from_id, r.from_name, r.chat_id,
                       r.message_text, r.created_at AS requested_at
                FROM work_items w JOIN requests r ON r.id=w.request_id
                WHERE w.id=%s
            """, (item_id,))
            item = cur.fetchone()
    if not item:
        return RedirectResponse("/admin/activity")
    return render(request, "admin/activity_detail.html", {
        "request": request, "user": _user(request), "item": item,
    })


# ---------------------------------------------------------------------------
# UI-only pages (Story 13) — no backend logic yet
# ---------------------------------------------------------------------------

@router.get("/admin/knowledge")
async def knowledge_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/knowledge.html", {"user": _user(request), "documents": []})


@router.get("/admin/memories")
async def memories_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/memories.html", {"user": _user(request)})


@router.get("/admin/companies")
async def companies_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/companies.html", {"user": _user(request), "companies": []})


@router.get("/admin/tools")
async def tools_page(request: Request):
    if g := _guard(request): return g
    # Read MCP servers from config.yaml (non-secret structure only)
    import yaml
    mcp_servers = []
    try:
        cfg = yaml.safe_load(Path("/home/pi/.hermes/profiles/simplifyops/config.yaml").read_text()) or {}
        for name, s in (cfg.get("mcp_servers", {}) or {}).items():
            mcp_servers.append({
                "name": name,
                "services": (s.get("env", {}) or {}).get("GOOGLE_WORKSPACE_SERVICES", "—"),
                "enabled": s.get("enabled", False),
                "health": None,
            })
    except Exception:
        pass
    return render(request, "admin/tools.html", {"user": _user(request), "mcp_servers": mcp_servers})


@router.get("/admin/automations")
async def automations_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/automations.html", {"user": _user(request), "automations": []})


@router.get("/admin/job-credentials")
async def job_credentials_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/job_credentials.html", {"user": _user(request), "credentials": []})
