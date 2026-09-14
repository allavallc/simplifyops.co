"""Tool-context token resolution — shared by the admin route and repo-owned MCP connectors.

The gateway mints short-lived tokens (`gateway/tool_context.py`) and stores only their SHA-256 hash in
`tool_contexts`. Both `GET /api/tool-contexts/{token}` and repo-owned MCP connectors resolve a raw token
through this single module — no independent hashing/expiry logic elsewhere. The raw token is a secret:
never log it or return it.
"""

import hashlib


def hash_token(token: str) -> str:
    """SHA-256 hex of the raw token — the only form ever stored or compared."""
    return hashlib.sha256(token.encode()).hexdigest()


def resolve(token: str) -> dict | None:
    """Resolve a raw token to its trusted context row, or None if unknown/expired.

    Read-only (no state change on read). Lazy-imports `db` so the pure `hash_token` stays DB-free."""
    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT request_id, person_id, authority, channel, from_id,
                       primary_email, timezone, can_influence, expires_at
                FROM tool_contexts
                WHERE token_hash = %s AND expires_at > now()
            """, (hash_token(token),))
            row = cur.fetchone()
    return dict(row) if row else None
