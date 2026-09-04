"""Google Workspace OAuth connection endpoints (story-59).

Browser flow: GET /integrations/google/connect → Google consent → GET /integrations/google/callback.
JSON: GET /status, POST /disconnect. Admin-gated; raw tokens never returned. The callback path must be
registered as an authorized redirect URI in the Google Cloud Console OAuth client.
"""

import logging
import secrets

import google_workspace as gw
from audit import log_audit
from deps import require_admin
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

log = logging.getLogger("simplifyops-admin")
router = APIRouter(prefix="/integrations/google")


@router.get("/connect")
async def connect(request: Request, admin=Depends(require_admin)):
    state = secrets.token_urlsafe(16)
    request.session["gw_oauth_state"] = state
    log.info("gw: connect initiated by %s", admin["email"])
    return RedirectResponse(gw.build_auth_url(state))


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        log.error("gw: Google returned error=%s", error)
        return RedirectResponse(f"/admin/settings?gw_error={error}")
    if not state or state != request.session.get("gw_oauth_state"):
        log.error("gw: bad_state on callback")
        return RedirectResponse("/admin/settings?gw_error=bad_state")
    email = request.session.get("admin_email")
    if not email:
        return RedirectResponse("/?error=not_logged_in")
    try:
        token = await gw.exchange_code(code)
        gw.store_tokens(email, token)
    except Exception as e:
        log.error("gw: token exchange/store failed: %s", e, exc_info=True)
        return RedirectResponse("/admin/settings?gw_error=exchange_failed")
    log_audit(email, "google_workspace_connect",
              new_value={"scopes": [s.split("/")[-1] for s in gw.WORKSPACE_SCOPES]})
    return RedirectResponse("/admin/settings?gw=connected")


@router.get("/status")
async def status(admin=Depends(require_admin)):
    return gw.get_status(admin["email"])


@router.post("/disconnect")
async def disconnect(admin=Depends(require_admin)):
    await gw.revoke_and_disconnect(admin["email"])
    log_audit(admin["email"], "google_workspace_disconnect")
    return {"ok": True, "connected": False}
