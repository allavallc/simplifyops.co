import logging
import os
import secrets

import psycopg2.extras
from audit import log_audit
from authlib.integrations.httpx_client import AsyncOAuth2Client
from db import Db
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

log = logging.getLogger("simplifyops-admin")

router = APIRouter(prefix="/auth")

GOOGLE_CLIENT_ID     = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/callback")


async def _exchange_code(code: str) -> dict:
    async with AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_REDIRECT_URI,
    ) as client:
        await client.fetch_token(
            "https://oauth2.googleapis.com/token",
            code=code,
        )
        log.info("auth: token exchange OK, fetching userinfo")
        resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo")
        return resp.json()


@router.get("/login")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    log.info("auth: login initiated state=%s redirect_uri=%s", state[:8], GOOGLE_REDIRECT_URI)
    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid+email+profile"
        f"&state={state}"
    )
    return Response(status_code=302, headers={"Location": google_url})


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None,
                   error: str = None):
    if error:
        log.error("auth: Google returned error=%s", error)
        return RedirectResponse(f"/?error=google_{error}")

    session_state = request.session.get("oauth_state")
    log.info("auth: callback state=%s session_state=%s session_keys=%s",
             state[:8] if state else None,
             session_state[:8] if session_state else None,
             list(request.session.keys()))

    if not state or state != session_state:
        log.error("auth: bad_state — callback state=%s session=%s", state, session_state)
        return RedirectResponse("/?error=bad_state")

    try:
        userinfo = await _exchange_code(code)
        log.info("auth: userinfo=%s", {k: v for k, v in userinfo.items() if k != 'sub'})
    except Exception as e:
        log.error("auth: token exchange failed: %s", e, exc_info=True)
        return RedirectResponse("/?error=oauth_failed")

    email = userinfo.get("email", "").lower()
    if not email:
        log.error("auth: no email in userinfo")
        return RedirectResponse("/?error=no_email")

    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, admin, authority FROM people WHERE person_email = %s AND admin = true",
                (email,)
            )
            person = cur.fetchone()

    if not person:
        log.warning("auth: login rejected — %s not in people as admin", email)
        return RedirectResponse("/?error=not_admin")

    request.session["admin_email"] = email
    request.session["admin_id"] = person["id"]
    request.session["authority"] = person["authority"]

    log.info("auth: login success email=%s", email)
    log_audit(email, "admin_login")
    return RedirectResponse("/admin")


@router.post("/logout")
async def logout(request: Request):
    email = request.session.get("admin_email")
    request.session.clear()
    if email:
        log.info("auth: logout email=%s", email)
        log_audit(email, "admin_logout")
    return RedirectResponse("/", status_code=303)
