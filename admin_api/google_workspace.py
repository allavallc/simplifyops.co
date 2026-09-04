"""Google Workspace OAuth connection management (story-59).

Governed connect / status / disconnect for a shared Google Workspace grant (Calendar, Gmail, Drive,
Sheets), storing tokens in the `google_tokens` table. Separate from admin-login OAuth (different scopes
+ a different callback path). Raw access/refresh tokens are never logged or returned to clients.

`get_fresh_google_token()` / auto-refresh are intentionally deferred until a repo-owned connector
consumes these tokens (story 55) — the current third-party Google MCP self-manages its own OAuth.

`db` / `authlib` / `httpx` are lazy-imported inside functions so the module (and the pure
`build_auth_url`) stay importable without those deps (e.g. CI).
"""

import os
from urllib.parse import urlencode

WORKSPACE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def _default_redirect_uri() -> str:
    # Derive the workspace callback from the admin-login redirect's base (different path).
    login = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/callback")
    base = login.rsplit("/auth/callback", 1)[0]
    return f"{base}/integrations/google/callback"


WORKSPACE_REDIRECT_URI = os.environ.get("GOOGLE_WORKSPACE_REDIRECT_URI") or _default_redirect_uri()


def build_auth_url(state: str, client_id: str | None = None, redirect_uri: str | None = None) -> str:
    """Google consent URL for the workspace grant. Pure (no I/O). `access_type=offline` + `prompt=consent`
    so Google returns a refresh_token."""
    params = {
        "client_id": client_id or os.environ.get("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": redirect_uri or WORKSPACE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(WORKSPACE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str | None = None) -> dict:
    from authlib.integrations.httpx_client import AsyncOAuth2Client
    async with AsyncOAuth2Client(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        redirect_uri=redirect_uri or WORKSPACE_REDIRECT_URI,
        scope=" ".join(WORKSPACE_SCOPES),
    ) as client:
        return await client.fetch_token(TOKEN_URL, code=code)


def store_tokens(email: str, token: dict) -> None:
    from datetime import UTC, datetime

    from db import Db
    expires_at = token.get("expires_at")
    expiry = datetime.fromtimestamp(expires_at, UTC) if expires_at else None
    scopes = (token.get("scope") or " ".join(WORKSPACE_SCOPES)).split()
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO google_tokens
                    (person_email, access_token, refresh_token, token_expiry, scopes, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (person_email) DO UPDATE SET
                    access_token  = EXCLUDED.access_token,
                    refresh_token = COALESCE(EXCLUDED.refresh_token, google_tokens.refresh_token),
                    token_expiry  = EXCLUDED.token_expiry,
                    scopes        = EXCLUDED.scopes,
                    updated_at    = now()
            """, (email, token.get("access_token"), token.get("refresh_token"), expiry, scopes))


def get_status(email: str) -> dict:
    from datetime import UTC, datetime

    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT scopes, token_expiry FROM google_tokens WHERE person_email = %s", (email,))
            row = cur.fetchone()
    if not row:
        return {"connected": False}
    expiry = row["token_expiry"]
    return {
        "connected": True,
        "scopes": [s.split("/")[-1] for s in (row["scopes"] or [])],
        "token_expiry": expiry.isoformat() if expiry else None,
        "expired": bool(expiry and expiry <= datetime.now(UTC)),
    }


async def revoke_and_disconnect(email: str) -> None:
    """Best-effort revoke at Google, then delete the local token row."""
    import httpx
    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT access_token, refresh_token FROM google_tokens WHERE person_email = %s",
                        (email,))
            row = cur.fetchone()
    if row:
        tok = row.get("refresh_token") or row.get("access_token")
        if tok:
            try:
                async with httpx.AsyncClient() as c:
                    await c.post(REVOKE_URL, data={"token": tok}, timeout=10)
            except Exception:
                pass  # revoke is best-effort; we still drop the local grant
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM google_tokens WHERE person_email = %s", (email,))
