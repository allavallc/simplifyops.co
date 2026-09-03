"""Hermes runtime adapter — the ONLY place the gateway talks to the Hermes API.

Protected architectural boundary (ops/current-architecture.md rule 10): a Hermes
or package upgrade touches this module, not the workers/adapters/handlers. Keep
all HTTP-to-:8642 concerns (session create/rotate, liveness streaming) here.
Extracted from the gateway.py god-module (story-26).
"""

import json
import os
import time

import requests
from logging_setup import get_logger
from sessions import (
    _logical_session_id,
    clear_hermes_session,
    get_hermes_session,
    get_session_message_cap,
    save_hermes_session,
)
from tool_context import create_tool_context

log = get_logger("simplifyops-gateway")

AGENT_API_URL             = os.environ.get("AGENT_API_URL", "http://127.0.0.1:8642")
AGENT_API_KEY             = os.environ.get("AGENT_API_KEY", "")
AGENT_API_CONNECT_TIMEOUT = int(os.environ.get("AGENT_API_CONNECT_TIMEOUT", "15"))
# Liveness-based streaming (story-17): max silence between stream chunks before we
# treat the runtime as dead. The runtime emits a keepalive every 30s, so 90s = 3
# missed keepalives. Implemented as the requests read (time-to-next-chunk) timeout —
# there is deliberately NO total wall-clock cap; a long turn runs while events flow.
AGENT_API_IDLE_TIMEOUT    = int(os.environ.get("AGENT_API_IDLE_TIMEOUT", "90"))


def _agent_api_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if AGENT_API_KEY:
        h["Authorization"] = f"Bearer {AGENT_API_KEY}"
    return h


def _ensure_agent_session(user_id: str, channel: str) -> str | None:
    """Return existing session ID or create a new one via the API server."""
    existing = get_hermes_session(user_id)
    if existing:
        return existing

    try:
        r = requests.post(
            f"{AGENT_API_URL}/api/sessions",
            headers=_agent_api_headers(),
            json={"profile": "simplifyops"},
            timeout=15,
        )
        if not r.ok:
            log.error("Agent API session create failed: %d %s", r.status_code, r.text[:200])
            return None
        session_id = r.json()["session"]["id"]
        save_hermes_session(user_id, channel, session_id)
        log.info("Created agent session %s for user %s", session_id, user_id)
        return session_id
    except Exception as e:
        log.error("Failed to create agent session: %s", e, exc_info=True)
        return None


def _get_session_message_count(session_id: str) -> int | None:
    """Query Hermes API for current session message count."""
    try:
        r = requests.get(
            f"{AGENT_API_URL}/api/sessions/{session_id}",
            headers=_agent_api_headers(),
            timeout=10,
        )
        if r.ok:
            return r.json().get("session", {}).get("message_count")
    except Exception as e:
        log.warning("Failed to get session message count for %s: %s", session_id, e)
    return None


def call_hermes(prompt: str, user_id: str = None, channel: str = None,
                authority: str = "member", can_influence: bool = True,
                request_id: str = None, person_ctx: dict = None) -> tuple:
    """
    Send a message to the long-running Hermes API server.
    Returns (reply, session_id) or (None, None) on failure.
    Rotates physical session when message count hits the cap.
    On stale session error, clears the mapping and retries once with a new session.
    """
    session_id = _ensure_agent_session(user_id, channel) if user_id else None
    if not session_id:
        log.error("Could not obtain agent session for user %s", user_id)
        return None, None

    # Check message count and rotate physical session if at cap
    cap = get_session_message_cap()
    msg_count = _get_session_message_count(session_id)
    if msg_count is not None and msg_count >= cap:
        logical = _logical_session_id(channel or "unknown", user_id or "unknown")
        log.info(
            "Session cap reached: logical=%s physical=%s count=%d cap=%d request_id=%s — rotating",
            logical, session_id, msg_count, cap, request_id,
        )
        # Create new physical session
        try:
            r = requests.post(
                f"{AGENT_API_URL}/api/sessions",
                headers=_agent_api_headers(),
                json={"profile": "simplifyops"},
                timeout=15,
            )
            if r.ok:
                new_session_id = r.json()["session"]["id"]
                save_hermes_session(user_id, channel, new_session_id,
                                    rotation_reason="message_count_cap",
                                    message_count_at_rotation=msg_count)
                log.info(
                    "Session rotated: logical=%s old=%s new=%s count_at_rotation=%d",
                    logical, session_id, new_session_id, msg_count,
                )
                session_id = new_session_id
            else:
                log.error("Session rotation failed: %d %s — using existing session",
                          r.status_code, r.text[:100])
        except Exception as e:
            log.error("Session rotation error: %s — using existing session", e)

    ctx = person_ctx or {}
    system_message = (
        f"Channel: {channel or 'unknown'}. "
        f"Sender ID: {user_id or 'unknown'}. "
        f"Authority: {authority}. "
        f"Memory influence: {'enabled' if can_influence else 'disabled'}."
    )
    if ctx.get("person_id"):
        system_message += f" Person ID: {ctx['person_id']}."
    if ctx.get("primary_email"):
        system_message += f" Email: {ctx['primary_email']}."
    if ctx.get("timezone"):
        system_message += f" Timezone: {ctx['timezone']}."
    if request_id:
        system_message += f" Request ID: {request_id}."
    tool_ctx_token = create_tool_context(
        request_id=request_id or "",
        person_ctx=ctx,
        authority=authority,
        channel=channel or "unknown",
        from_id=user_id or "unknown",
        can_influence=can_influence,
    )
    system_message += f" Tool context token: {tool_ctx_token}."

    log.info("Agent handoff (session=%s): %.80s", session_id, prompt)
    t0 = time.time()

    def _chat_stream(sid):
        # Liveness streaming (story-17): read timeout = idle timeout between chunks;
        # no total wall-clock cap, so a long-but-live turn is never killed.
        resp = requests.post(
            f"{AGENT_API_URL}/api/sessions/{sid}/chat/stream",
            headers=_agent_api_headers(),
            json={"message": prompt, "system_message": system_message},
            stream=True,
            timeout=(AGENT_API_CONNECT_TIMEOUT, AGENT_API_IDLE_TIMEOUT),
        )
        # SSE (`text/event-stream`) carries no charset, so `requests` defaults r.encoding to
        # ISO-8859-1 (RFC 2616) — then iter_lines(decode_unicode=True) would mis-decode the UTF-8
        # reply as Latin-1, mojibake-ing curly quotes/apostrophes/em-dashes (story-62). Force UTF-8.
        resp.encoding = "utf-8"
        return resp

    try:
        r = _chat_stream(session_id)

        # Stale session — the stream endpoint returns 404/410 before streaming.
        if r.status_code in (404, 410):
            log.warning("Agent session %s not found — clearing and retrying", session_id)
            r.close()
            clear_hermes_session(user_id)
            session_id = _ensure_agent_session(user_id, channel)
            if not session_id:
                return None, None
            r = _chat_stream(session_id)

        if not r.ok:
            log.error("Agent API chat/stream failed: %d %s", r.status_code, r.text[:200])
            r.close()
            return None, None

        # Consume the SSE stream. Every event (and each 30s keepalive comment) resets
        # the read/idle timeout, so a long turn stays alive as long as it makes noise.
        # The final reply comes from `assistant.completed`; an `error` event is failure;
        # 90s of total silence raises ReadTimeout below → treated as a dead runtime.
        reply = None
        returned_session = session_id
        stream_error = None
        event_name = None
        try:
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    event_name = None          # blank line = end of one SSE event
                    continue
                line = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
                line = line.strip()
                if not line or line.startswith(":"):
                    continue                   # keepalive comment — liveness only
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    if event_name == "assistant.completed":
                        reply = (payload.get("content") or "").strip()
                        returned_session = payload.get("session_id", returned_session)
                    elif event_name == "run.completed":
                        returned_session = payload.get("session_id", returned_session)
                    elif event_name == "error":
                        stream_error = payload.get("message", "unknown")
                    elif event_name == "done":
                        break
        except requests.exceptions.RequestException as e:
            log.error("Agent stream idle >%ds or aborted: %s", AGENT_API_IDLE_TIMEOUT, e)
            return None, None
        finally:
            r.close()

        elapsed = int((time.time() - t0) * 1000)

        if stream_error is not None:
            log.error("Agent stream error after %dms: %s", elapsed, stream_error)
            return None, None

        if returned_session != session_id:
            save_hermes_session(user_id, channel or "unknown", returned_session)
            session_id = returned_session

        log.info("Agent responded (stream) in %dms (%d chars)", elapsed, len(reply or ""))
        return (reply or None), session_id

    except requests.exceptions.RequestException as e:
        log.error("Agent API stream connect failed: %s", e, exc_info=True)
        return None, None
    except Exception as e:
        log.error("Agent API call failed: %s", e, exc_info=True)
        return None, None
