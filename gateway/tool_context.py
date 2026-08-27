"""Short-lived tool-context tokens for MCP tools.

Extracted from the gateway.py god-module (story-26). MCP tools resolve the raw
token via GET /api/tool-contexts/{token}; only the hash is stored.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from gwdb import get_db_conn
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")

TOOL_CONTEXT_TTL_MINUTES = 30


def create_tool_context(request_id: str, person_ctx: dict, authority: str,
                        channel: str, from_id: str, can_influence: bool) -> str:
    """
    Create a short-lived tool context token. Returns the raw token (never stored).
    MCP tools resolve this via GET /api/tool-contexts/{token}.
    """
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(minutes=TOOL_CONTEXT_TTL_MINUTES)

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tool_contexts
                    (token_hash, request_id, person_id, authority, channel, from_id,
                     primary_email, timezone, can_influence, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                token_hash, request_id,
                person_ctx.get("person_id"),
                authority, channel, from_id,
                person_ctx.get("primary_email"),
                person_ctx.get("timezone", "UTC"),
                can_influence, expires_at,
            ))
        conn.commit()
    except Exception as e:
        log.warning("Failed to create tool context: %s", e)
        conn.rollback()
    finally:
        conn.close()

    return raw_token
