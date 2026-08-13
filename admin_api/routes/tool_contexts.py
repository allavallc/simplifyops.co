"""
Tool context token resolution endpoint.
MCP servers call GET /api/tool-contexts/{token} to resolve execution context.
Tokens are short-lived and single-use-safe (no state change on read).
"""

import hashlib

import psycopg2.extras
from fastapi import APIRouter, HTTPException

from db import Db

router = APIRouter(prefix="/api/tool-contexts")


@router.get("/{token}")
async def resolve_tool_context(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT request_id, person_id, authority, channel, from_id,
                       primary_email, timezone, can_influence, expires_at
                FROM tool_contexts
                WHERE token_hash = %s AND expires_at > now()
            """, (token_hash,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(404, "tool_context_not_found_or_expired")

    return {
        "request_id":    row["request_id"],
        "person_id":     row["person_id"],
        "authority":     row["authority"],
        "channel":       row["channel"],
        "from_id":       row["from_id"],
        "primary_email": row["primary_email"],
        "timezone":      row["timezone"],
        "can_influence": row["can_influence"],
        "expires_at":    row["expires_at"].isoformat() if row["expires_at"] else None,
    }
