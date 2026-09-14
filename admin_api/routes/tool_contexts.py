"""
Tool context token resolution endpoint.
MCP servers call GET /api/tool-contexts/{token} to resolve execution context.
Tokens are short-lived and single-use-safe (no state change on read).
"""

from fastapi import APIRouter, HTTPException
from tool_context_store import resolve

router = APIRouter(prefix="/api/tool-contexts")


@router.get("/{token}")
async def resolve_tool_context(token: str):
    ctx = resolve(token)
    if not ctx:
        raise HTTPException(404, "tool_context_not_found_or_expired")

    return {
        "request_id":    ctx["request_id"],
        "person_id":     ctx["person_id"],
        "authority":     ctx["authority"],
        "channel":       ctx["channel"],
        "from_id":       ctx["from_id"],
        "primary_email": ctx["primary_email"],
        "timezone":      ctx["timezone"],
        "can_influence": ctx["can_influence"],
        "expires_at":    ctx["expires_at"].isoformat() if ctx["expires_at"] else None,
    }
