import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

import psycopg2.extras
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from db import init_pool, Db
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.messages import router as messages_router
from routes.people import router as people_router
from routes.inbox import router as inbox_router
from routes.activity import router as activity_router
from routes.tool_contexts import router as tool_contexts_router
from routes.settings import router as settings_router

SESSION_SECRET = os.environ["ADMIN_SESSION_SECRET"]
BASE_DIR = Path(__file__).parent
from jinja2 import Environment, FileSystemLoader
from starlette.templating import Jinja2Templates as _Jinja2Templates
_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=True,
    cache_size=0,
)
templates = _Jinja2Templates(env=_jinja_env)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    _apply_schema()
    yield


def _apply_schema():
    sql = (BASE_DIR / "schema.sql").read_text()
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


app = FastAPI(title="SimplifyOps Admin API", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60 * 60 * 24 * 7)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(messages_router)
app.include_router(people_router)
app.include_router(inbox_router)
app.include_router(activity_router)
app.include_router(tool_contexts_router)
app.include_router(settings_router)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

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


def _guard(request: Request):
    """Return redirect if not signed in, else None."""
    if not request.session.get("admin_email"):
        return RedirectResponse("/")
    return None


# ---------------------------------------------------------------------------
# Admin pages
# ---------------------------------------------------------------------------

@app.get("/")
async def index(request: Request, error: str = None):
    if request.session.get("admin_email"):
        return RedirectResponse("/admin")
    return render(request, "login.html", {"request": request, "error": error})


@app.get("/admin")
async def admin_index(request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::int FROM contact_requests WHERE status='pending'")
            pending_count = cur.fetchone()[0]
    return render(request, "admin/index.html", {
        "request": request, "user": _user(request), "pending_count": pending_count,
    })


@app.get("/admin/people")
async def people_index(request: Request):
    if g := _guard(request): return g
    show_deleted = request.query_params.get("show_deleted") in ("1", "true", "yes")
    where = "" if show_deleted else "WHERE deleted_at IS NULL"
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM people {where} ORDER BY created_at DESC")
            people = list(cur.fetchall())
    return render(request, "admin/people/index.html", {
        "request": request, "user": _user(request), "people": people,
        "show_deleted": show_deleted,
    })


@app.get("/admin/people/new")
async def person_new(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/people/form.html", {
        "request": request, "user": _user(request), "person": None,
    })


@app.post("/admin/people/new")
async def person_create(request: Request):
    if g := _guard(request): return g
    form = await request.form()
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            email = str(form.get("person_email", "")).lower().strip()
            tg = str(form.get("telegram_id", "")).strip() or None
            cur.execute("""
                INSERT INTO people (person_name, person_email, authority, can_converse, can_influence,
                    status, admin, notes, telegram_id, phone_country_code, phone_number, timezone, created_by, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT (person_email) DO UPDATE SET
                    person_name=EXCLUDED.person_name, authority=EXCLUDED.authority,
                    can_converse=EXCLUDED.can_converse, can_influence=EXCLUDED.can_influence,
                    status=EXCLUDED.status, admin=EXCLUDED.admin, notes=EXCLUDED.notes,
                    telegram_id=EXCLUDED.telegram_id, phone_country_code=EXCLUDED.phone_country_code,
                    phone_number=EXCLUDED.phone_number, timezone=EXCLUDED.timezone, updated_at=now()
                RETURNING id
            """, (
                str(form.get("person_name", "")).strip() or None, email,
                form.get("authority", "member"), bool(form.get("can_converse")),
                bool(form.get("can_influence")), form.get("status", "allowed"),
                bool(form.get("admin")), str(form.get("notes", "")).strip() or None,
                tg, str(form.get("phone_country_code", "")).strip() or None,
                str(form.get("phone_number", "")).strip() or None,
                str(form.get("timezone", "")).strip() or None,
                request.session["admin_email"],
            ))
            person_id = cur.fetchone()["id"]
        if tg:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
                    VALUES (%s,'telegram',%s,%s,true)
                    ON CONFLICT (identity_type, normalized_value) DO UPDATE SET person_id=EXCLUDED.person_id
                """, (person_id, tg, tg))
    return RedirectResponse(f"/admin/people/{email}", status_code=303)


@app.get("/admin/people/{email}/edit")
async def person_edit(email: str, request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM people WHERE person_email=%s", (email.lower(),))
            person = cur.fetchone()
    if not person:
        return RedirectResponse("/admin/people")
    return render(request, "admin/people/form.html", {
        "request": request, "user": _user(request), "person": person,
    })


@app.post("/admin/people/{email}/edit")
async def person_update(email: str, request: Request):
    if g := _guard(request): return g
    form = await request.form()
    tg = str(form.get("telegram_id", "")).strip() or None
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                UPDATE people SET
                    person_name=COALESCE(%s,person_name), authority=%s,
                    can_converse=%s, can_influence=%s, status=%s, admin=%s,
                    notes=COALESCE(%s,notes), telegram_id=COALESCE(%s,telegram_id),
                    phone_country_code=COALESCE(%s,phone_country_code),
                    phone_number=COALESCE(%s,phone_number),
                    timezone=%s, updated_at=now()
                WHERE person_email=%s RETURNING id
            """, (
                str(form.get("person_name", "")).strip() or None,
                form.get("authority","member"), bool(form.get("can_converse")),
                bool(form.get("can_influence")), form.get("status","allowed"),
                bool(form.get("admin")), str(form.get("notes","")).strip() or None,
                tg, str(form.get("phone_country_code","")).strip() or None,
                str(form.get("phone_number","")).strip() or None,
                str(form.get("timezone","")).strip() or None, email.lower(),
            ))
            row = cur.fetchone()
        if row and tg:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
                    VALUES (%s,'telegram',%s,%s,true)
                    ON CONFLICT (identity_type, normalized_value) DO UPDATE SET person_id=EXCLUDED.person_id
                """, (row["id"], tg, tg))
    return RedirectResponse(f"/admin/people/{email}", status_code=303)


@app.post("/admin/people/{email}/delete")
async def person_delete(email: str, request: Request):
    if g := _guard(request): return g
    # Soft delete (story-20): never physically remove. Restorable via /restore.
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE people SET deleted_at=now(), updated_at=now() "
                "WHERE person_email=%s AND deleted_at IS NULL",
                (email.lower(),),
            )
    return RedirectResponse("/admin/people", status_code=303)


@app.post("/admin/people/{email}/restore")
async def person_restore(email: str, request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE people SET deleted_at=NULL, updated_at=now() WHERE person_email=%s",
                (email.lower(),),
            )
    return RedirectResponse(f"/admin/people/{email}", status_code=303)


@app.get("/admin/people/{email}")
async def person_view(email: str, request: Request):
    if g := _guard(request): return g
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM people WHERE person_email=%s", (email.lower(),))
            person = cur.fetchone()
    if not person:
        return RedirectResponse("/admin/people")
    return render(request, "admin/people/view.html", {
        "request": request, "user": _user(request), "person": person,
    })


@app.get("/admin/inbox")
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


@app.post("/admin/inbox/{req_id}/approve")
async def inbox_approve_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/approve",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@app.post("/admin/inbox/{req_id}/reject")
async def inbox_reject_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/reject",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@app.post("/admin/inbox/{req_id}/ignore")
async def inbox_ignore_page(req_id: int, request: Request):
    if g := _guard(request): return g
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(f"http://127.0.0.1:{os.environ.get('PORT', '3002')}/api/inbox/{req_id}/ignore",
                          cookies=dict(request.cookies))
    return RedirectResponse("/admin/inbox", status_code=303)


@app.get("/admin/activity")
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


@app.get("/admin/settings")
async def settings_page(request: Request):
    if g := _guard(request): return g
    import yaml
    import urllib.request

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
            cur.execute("SELECT value FROM admin_settings WHERE key='session_message_cap'")
            row = cur.fetchone()
            settings["session_message_cap"] = int(row[0]) if row else 100
            cur.execute("SELECT value FROM admin_settings WHERE key='default_timezone'")
            row = cur.fetchone()
            settings["default_timezone"] = row[0] if row else "America/New_York"

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


@app.get("/admin/activity/{item_id}")
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

@app.get("/admin/knowledge")
async def knowledge_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/knowledge.html", {"user": _user(request), "documents": []})


@app.get("/admin/memories")
async def memories_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/memories.html", {"user": _user(request)})


@app.get("/admin/companies")
async def companies_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/companies.html", {"user": _user(request), "companies": []})


@app.get("/admin/tools")
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


@app.get("/admin/automations")
async def automations_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/automations.html", {"user": _user(request), "automations": []})


@app.get("/admin/job-credentials")
async def job_credentials_page(request: Request):
    if g := _guard(request): return g
    return render(request, "admin/job_credentials.html", {"user": _user(request), "credentials": []})
