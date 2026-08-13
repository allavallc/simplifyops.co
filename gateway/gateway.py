#!/usr/bin/env python3
"""
SimplifyOps message gateway — channel-agnostic router for James (Hermes).

Architecture:
  [channel adapter] -> enqueue_message() -> work_items row
  [DurableWorkflowWorker] -> governance -> Hermes -> reply_ready -> outbound send

Durable workflow: every inbound message gets a requests row and work_items row
before Hermes is called. Channel adapters never block waiting for a reply.
If Hermes times out, the item moves to failed_retryable and is retried up to
WORKER_MAX_ATTEMPTS times before moving to failed_needs_review.

Adding a new channel:
  1. Write an adapter that normalises incoming messages into
     (channel, from_id, from_name, chat_id, text, raw, provider_event_id)
  2. Call enqueue_message() with those values
  3. Implement _send_outbound() support for the new channel
  4. Start the adapter in main()

Current adapters: Telegram
"""

import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import psycopg2
import psycopg2.errors
import psycopg2.extras
import requests

from transcription import TranscriptionError, looks_transcribable_file, transcribe_local_audio

sys.path.insert(0, "/home/pi")
from pi_logging import get_logger

log = get_logger("simplifyops-gateway")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

AGENT_API_URL          = os.environ.get("AGENT_API_URL", "http://127.0.0.1:8642")
AGENT_API_KEY          = os.environ.get("AGENT_API_KEY", "")
AGENT_API_TIMEOUT      = int(os.environ.get("AGENT_API_TIMEOUT", "300"))  # legacy (sync path); replaced by liveness streaming below
AGENT_API_CONNECT_TIMEOUT = int(os.environ.get("AGENT_API_CONNECT_TIMEOUT", "15"))
# Liveness-based streaming (story-17): max silence between stream chunks before we
# treat the runtime as dead. The runtime emits a keepalive every 30s, so 90s = 3
# missed keepalives. Implemented as the requests read (time-to-next-chunk) timeout —
# there is deliberately NO total wall-clock cap; a long turn runs while events flow.
AGENT_API_IDLE_TIMEOUT = int(os.environ.get("AGENT_API_IDLE_TIMEOUT", "90"))
ADMIN_API_URL          = os.environ.get("ADMIN_API_URL", "http://127.0.0.1:3000")
INBOX_URL              = os.environ.get("INBOX_URL", f"{ADMIN_API_URL}/api/inbox")
INTERNAL_PORT          = int(os.environ.get("GATEWAY_INTERNAL_PORT", "3001"))
TELEGRAM_API           = f"https://api.telegram.org/bot{BOT_TOKEN}"
DELAY_THRESHOLD_MINUTES = 30
# Intake durability: how long to back off before re-polling the SAME Telegram
# update when handoff to the admin API is retryable (admin down / 5xx / timeout).
# The offset is never advanced past an unconfirmed update, so nothing is dropped.
INTAKE_BACKOFF_MIN_SECONDS = int(os.environ.get("INTAKE_BACKOFF_MIN_SECONDS", "1"))
INTAKE_BACKOFF_MAX_SECONDS = int(os.environ.get("INTAKE_BACKOFF_MAX_SECONDS", "30"))
SESSION_MESSAGE_CAP_FALLBACK = int(os.environ.get("SESSION_MESSAGE_CAP", "100"))

DB_DSN = os.environ.get("GATEWAY_DB_DSN", "postgresql:///whitelist_app?host=/var/run/postgresql")

WORKER_CONCURRENCY  = int(os.environ.get("GATEWAY_WORKER_CONCURRENCY",  "3"))
WORKER_BATCH_SIZE   = int(os.environ.get("GATEWAY_WORKER_BATCH_SIZE",   "10"))
WORKER_POLL_SECONDS = int(os.environ.get("GATEWAY_WORKER_POLL_SECONDS", "2"))
WORKER_LOCK_SECONDS = int(os.environ.get("GATEWAY_WORKER_LOCK_SECONDS", "300"))
WORKER_RETRY_SECONDS = int(os.environ.get("GATEWAY_WORKER_RETRY_SECONDS", "30"))
WORKER_MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db_conn():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    return conn


def apply_schema():
    schema_path = Path(__file__).parent / "sql" / "schema.sql"
    sql = schema_path.read_text()
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        log.info("Schema applied")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Session history (audit log — written after each exchange)
# ---------------------------------------------------------------------------

def append_user_history(user_id: str, user_msg: str, assistant_msg: str) -> None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO session_history (user_id, user_msg, assistant_msg)
                VALUES (%s, %s, %s)
            """, (user_id, user_msg, assistant_msg))
        conn.commit()
    except Exception as e:
        log.warning("Failed to save session history: %s", e)
        conn.rollback()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Hermes session mappings — one persistent Hermes session per user
# ---------------------------------------------------------------------------

def _logical_session_id(channel: str, user_id: str) -> str:
    return f"{channel}:{user_id}"


def get_hermes_session(user_id: str) -> str | None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT hermes_session_id FROM hermes_session_mappings WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def save_hermes_session(user_id: str, channel: str, hermes_session_id: str,
                        rotation_reason: str = None,
                        message_count_at_rotation: int = None) -> None:
    logical = _logical_session_id(channel, user_id)
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hermes_session_mappings
                    (user_id, channel, logical_session_id, hermes_session_id,
                     rotation_reason, message_count_at_rotation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET hermes_session_id         = EXCLUDED.hermes_session_id,
                        channel                   = EXCLUDED.channel,
                        logical_session_id        = EXCLUDED.logical_session_id,
                        physical_rotations        = hermes_session_mappings.physical_rotations + 1,
                        rotation_reason           = EXCLUDED.rotation_reason,
                        message_count_at_rotation = EXCLUDED.message_count_at_rotation,
                        updated_at                = now()
            """, (user_id, channel, logical, hermes_session_id,
                  rotation_reason, message_count_at_rotation))
        conn.commit()
    except Exception as e:
        log.warning("Failed to save hermes session mapping: %s", e)
        conn.rollback()
    finally:
        conn.close()


def clear_hermes_session(user_id: str) -> None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hermes_session_mappings WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        log.warning("Failed to clear hermes session mapping: %s", e)
        conn.rollback()
    finally:
        conn.close()


def get_session_message_cap() -> int:
    """Read global cap from admin_settings, fall back to env var default."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM admin_settings WHERE key = 'session_message_cap'")
            row = cur.fetchone()
            return int(row[0]) if row else SESSION_MESSAGE_CAP_FALLBACK
    except Exception:
        return SESSION_MESSAGE_CAP_FALLBACK
    finally:
        conn.close()


def build_prompt(text: str, delay_note: str = None) -> str:
    if delay_note:
        return f"{delay_note}\n\n{text}"
    return text


# ---------------------------------------------------------------------------
# Durable enqueue
# ---------------------------------------------------------------------------

def new_request_id() -> str:
    return uuid.uuid4().hex


def enqueue_message(request_id: str, channel: str, from_id: str, from_name: str,
                    chat_id: str, text: str, raw: dict,
                    provider_event_id: str = None) -> bool:
    """
    Create requests + channel_events + work_items rows atomically.
    Returns True if enqueued, False if provider_event_id was already seen (duplicate).
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO requests (id, channel, from_id, from_name, chat_id, message_text)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (request_id, channel, from_id, from_name, chat_id, text))

            if provider_event_id:
                try:
                    cur.execute("""
                        INSERT INTO channel_events (channel, provider_event_id, request_id)
                        VALUES (%s, %s, %s)
                    """, (channel, provider_event_id, request_id))
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    log.info("Duplicate provider event %s/%s — skipping", channel, provider_event_id)
                    return False

            cur.execute("""
                INSERT INTO work_items (request_id, status)
                VALUES (%s, 'ready')
            """, (request_id,))

        conn.commit()
        log.info("Enqueued request_id=%s channel=%s from=%s", request_id, channel, from_id)
        return True
    except Exception as e:
        conn.rollback()
        log.error("enqueue_message failed: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------

def governance_check(from_id: str, channel: str = "telegram") -> tuple:
    """
    Look up the sender in the people DB.
    Returns (approved, reason, context) where context carries authority
    and can_influence for use in runtime handoff.
    Unknown senders return (False, reason, {}).
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if channel == "telegram":
                cur.execute("""
                    SELECT authority, can_converse, can_influence, status
                    FROM people WHERE telegram_id = %s
                """, (from_id,))
            else:
                return False, f"unsupported channel {channel}", {}
            person = cur.fetchone()
    finally:
        conn.close()

    if not person:
        return False, f"unknown sender {from_id}", {}
    if person["status"] != "allowed":
        return False, f"person blocked (status={person['status']})", {}
    if not person["can_converse"]:
        return False, "can_converse=false", {}
    return True, "approved", {
        "authority": person["authority"],
        "can_influence": person["can_influence"],
    }


# ---------------------------------------------------------------------------
# Runtime bridge — HTTP calls to long-running Hermes API server
# ---------------------------------------------------------------------------

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
        return requests.post(
            f"{AGENT_API_URL}/api/sessions/{sid}/chat/stream",
            headers=_agent_api_headers(),
            json={"message": prompt, "system_message": system_message},
            stream=True,
            timeout=(AGENT_API_CONNECT_TIMEOUT, AGENT_API_IDLE_TIMEOUT),
        )

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


# ---------------------------------------------------------------------------
# Identity enrichment (fire-and-forget)
# ---------------------------------------------------------------------------

def enrich_identity(raw: dict) -> None:
    headers = {"content-type": "application/json"}
    if WHITELIST_WEBHOOK_SECRET:
        headers["x-telegram-bot-api-secret-token"] = WHITELIST_WEBHOOK_SECRET
    try:
        r = requests.post(WHITELIST_WEBHOOK_URL, json=raw, headers=headers, timeout=5)
        if not r.ok:
            log.warning("Identity enrichment returned %d", r.status_code)
    except Exception as e:
        log.warning("Identity enrichment failed: %s", e)


# ---------------------------------------------------------------------------
# Unknown sender — queue for admin approval
# ---------------------------------------------------------------------------

def queue_contact_request(request_id: str, channel: str, from_id: str, from_name: str,
                           chat_id: str, text: str, raw: dict) -> None:
    try:
        r = requests.post(INBOX_URL, json={
            "request_id": request_id,
            "channel": channel,
            "from_id": from_id,
            "from_name": from_name,
            "chat_id": chat_id,
            "message_text": text,
            "raw": raw,
        }, timeout=5)
        if r.ok:
            log.info("Queued contact request from %s/%s (request_id=%s)", channel, from_id, request_id)
        else:
            log.warning("Failed to queue contact request: %d", r.status_code)
    except Exception as e:
        log.warning("queue_contact_request failed: %s", e)


# ---------------------------------------------------------------------------
# Outbound send
# ---------------------------------------------------------------------------

TOOL_CONTEXT_TTL_MINUTES = 30


def create_tool_context(request_id: str, person_ctx: dict, authority: str,
                        channel: str, from_id: str, can_influence: bool) -> str:
    """
    Create a short-lived tool context token. Returns the raw token (never stored).
    MCP tools resolve this via GET /api/tool-contexts/{token}.
    """
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOOL_CONTEXT_TTL_MINUTES)

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


def get_person_context(from_id: str, channel: str) -> dict:
    """Look up non-secret person context for the system_message."""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.id,
                       p.person_email,
                       COALESCE(
                           p.timezone,
                           (SELECT value FROM admin_settings WHERE key = 'default_timezone'),
                           'UTC'
                       ) AS timezone
                FROM person_identities pi
                JOIN people p ON p.id = pi.person_id
                WHERE pi.identity_type = %s AND pi.normalized_value = %s
                LIMIT 1
            """, (channel, from_id))
            row = cur.fetchone()
            if row:
                return {
                    "person_id": str(row["id"]),
                    "primary_email": row["person_email"],
                    "timezone": row["timezone"] or "UTC",
                }
    except Exception as e:
        log.warning("get_person_context failed: %s", e)
    finally:
        conn.close()
    return {}


def send_outbound(channel: str, chat_id: str, text: str) -> bool:
    if channel == "telegram":
        return _tg_send(chat_id, text)
    log.error("No outbound sender for channel=%s", channel)
    return False


# ---------------------------------------------------------------------------
# Durable workflow worker
# ---------------------------------------------------------------------------

class DurableWorkflowWorker(threading.Thread):
    def __init__(self):
        super().__init__(name="durable-worker", daemon=True)

    def run(self):
        log.info("DurableWorkflowWorker started (concurrency=%d poll=%ds)",
                 WORKER_CONCURRENCY, WORKER_POLL_SECONDS)
        while True:
            try:
                self._poll_and_process()
            except Exception as e:
                log.error("Worker poll error: %s", e, exc_info=True)
            time.sleep(WORKER_POLL_SECONDS)

    def _poll_and_process(self):
        conn = get_db_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        w.id        AS item_id,
                        w.request_id,
                        w.attempt_count,
                        w.reply_text,
                        w.payload,
                        r.channel,
                        r.from_id,
                        r.from_name,
                        r.chat_id,
                        r.message_text,
                        r.created_at AS requested_at
                    FROM work_items w
                    JOIN requests r ON r.id = w.request_id
                    WHERE (
                        w.status IN ('ready', 'failed_retryable', 'reply_ready')
                        OR (w.status = 'processing' AND w.locked_until <= now())
                    )
                      AND (w.retry_after IS NULL OR w.retry_after <= now())
                      AND (w.locked_until IS NULL OR w.locked_until <= now())
                    FOR UPDATE OF w SKIP LOCKED
                    LIMIT %s
                """, (WORKER_CONCURRENCY,))
                items = cur.fetchall()

                if not items:
                    return

                item_ids = [i["item_id"] for i in items]
                cur.execute("""
                    UPDATE work_items
                    SET status = 'processing',
                        locked_until = now() + (%s * interval '1 second'),
                        updated_at = now()
                    WHERE id = ANY(%s)
                """, (WORKER_LOCK_SECONDS, item_ids))
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error("Worker claim failed: %s", e, exc_info=True)
            return
        finally:
            conn.close()

        with ThreadPoolExecutor(max_workers=WORKER_CONCURRENCY) as pool:
            futures = [pool.submit(self._process_item, item) for item in items]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    log.error("Worker item failed with unhandled exception: %s", e, exc_info=True)

    def _process_item(self, item):
        item_id    = item["item_id"]
        request_id = item["request_id"]
        channel    = item["channel"]
        from_id    = item["from_id"]
        chat_id    = item["chat_id"]
        text       = item["message_text"]
        attempt    = item["attempt_count"] + 1
        # Governance context was stored at intake by POST /messages
        raw_payload = item.get("payload") or {}
        payload = raw_payload if isinstance(raw_payload, dict) else json.loads(raw_payload)
        authority  = payload.get("authority", "member")
        can_influence = payload.get("can_influence", True)
        log.info("Processing item_id=%d request_id=%s attempt=%d authority=%s",
                 item_id, request_id, attempt, authority)

        # reply_ready: skip runtime, go straight to outbound send
        if item["reply_text"]:
            self._do_outbound(item_id, request_id, channel, from_id, chat_id, item["reply_text"], attempt)
            return

        # delay note for late-delivered items
        delay_note = None
        requested_at = item.get("requested_at")
        if requested_at:
            elapsed_minutes = (datetime.now(timezone.utc) - requested_at).total_seconds() / 60
            if elapsed_minutes > DELAY_THRESHOLD_MINUTES:
                delay_note = "Note: there was a delay before I could respond — please acknowledge that briefly before answering."

        person_ctx = get_person_context(from_id, channel)
        prompt = build_prompt(text, delay_note)
        log.info("item_id=%d runtime_handoff_start request_id=%s", item_id, request_id)
        t0 = time.time()
        reply, _ = call_hermes(prompt, user_id=from_id, channel=channel,
                                authority=authority, can_influence=can_influence,
                                request_id=request_id, person_ctx=person_ctx)
        elapsed_ms = int((time.time() - t0) * 1000)

        if reply is None:
            error = "Agent returned no response"
            log.error("item_id=%d runtime_handoff_failed after %dms attempt=%d", item_id, elapsed_ms, attempt)
            if attempt >= WORKER_MAX_ATTEMPTS:
                self._set_status(item_id, "failed_needs_review", attempt, error_summary=error,
                                 request_id=request_id, channel=channel, from_id=from_id)
            else:
                self._set_status(item_id, "failed_retryable", attempt, error_summary=error)
            return

        log.info("item_id=%d runtime_handoff_complete %dms %d chars", item_id, elapsed_ms, len(reply))

        # save reply before sending (reply_ready boundary)
        self._save_reply(item_id, reply)
        append_user_history(from_id, text, reply)
        self._do_outbound(item_id, request_id, channel, from_id, chat_id, reply, attempt)

    def _do_outbound(self, item_id, request_id, channel, from_id, chat_id, reply, attempt):
        log.info("item_id=%d outbound_send_start channel=%s", item_id, channel)
        ok = send_outbound(channel, chat_id, reply)
        if ok:
            self._set_status(item_id, "completed", attempt)
            log.info("item_id=%d request_id=%s outbound_send_complete completed", item_id, request_id)
        else:
            # reply is saved; retry outbound only, do not re-run Hermes
            if attempt >= WORKER_MAX_ATTEMPTS:
                self._set_status(item_id, "failed_needs_review", attempt,
                                 error_summary="outbound send failed after max attempts",
                                 request_id=request_id, channel=channel, from_id=from_id)
            else:
                self._set_status(item_id, "failed_retryable", attempt,
                                 error_summary="outbound send failed")

    def _save_reply(self, item_id: int, reply: str):
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE work_items
                    SET reply_text = %s, status = 'reply_ready', updated_at = now()
                    WHERE id = %s
                """, (reply, item_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error("_save_reply failed for item_id=%d: %s", item_id, e)
        finally:
            conn.close()

    def _notify_failed_needs_review(self, item_id: int, request_id: str,
                                     channel: str, from_id: str, error_summary: str):
        chat_id = os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "8633043564")
        text = (
            f"⚠️ Failed request needs review\n"
            f"item_id: {item_id}\n"
            f"request_id: {request_id}\n"
            f"channel: {channel} / sender: {from_id}\n"
            f"error: {error_summary or 'unknown'}"
        )
        try:
            _tg_send(chat_id, text)
        except Exception as e:
            log.error("Failed to send failed_needs_review notification: %s", e)

    def _set_status(self, item_id: int, status: str, attempt: int,
                    error_summary: str = None, request_id: str = None,
                    channel: str = None, from_id: str = None):
        if status == "failed_needs_review":
            log.error("item_id=%d moved to failed_needs_review: %s", item_id, error_summary)
            self._notify_failed_needs_review(item_id, request_id or "", channel or "", from_id or "", error_summary)
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                if status == "failed_retryable":
                    cur.execute("""
                        UPDATE work_items
                        SET status = %s,
                            attempt_count = %s,
                            error_summary = %s,
                            locked_until = NULL,
                            retry_after = now() + (%s * interval '1 second'),
                            updated_at = now()
                        WHERE id = %s
                    """, (status, attempt, error_summary, WORKER_RETRY_SECONDS, item_id))
                else:
                    cur.execute("""
                        UPDATE work_items
                        SET status = %s,
                            attempt_count = %s,
                            error_summary = %s,
                            locked_until = NULL,
                            retry_after = NULL,
                            updated_at = now()
                        WHERE id = %s
                    """, (status, attempt, error_summary, item_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error("_set_status failed for item_id=%d: %s", item_id, e)
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Internal HTTP server — receives approval callbacks from admin UI
# ---------------------------------------------------------------------------

class InternalHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path != "/internal/reply":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))

        channel    = body.get("channel", "telegram")
        from_id    = str(body.get("from_id", ""))
        from_name  = str(body.get("from_name", ""))
        chat_id    = str(body.get("chat_id", ""))
        text       = body.get("text", "")
        request_id = str(body.get("request_id") or new_request_id())

        enqueue_message(request_id, channel, from_id, from_name, chat_id, text, {})

        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def start_internal_server():
    server = HTTPServer(("127.0.0.1", INTERNAL_PORT), InternalHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="internal-server")
    t.start()
    log.info("Internal reply server listening on 127.0.0.1:%d", INTERNAL_PORT)


# ---------------------------------------------------------------------------
# Telegram adapter
# ---------------------------------------------------------------------------

def _tg_get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=35)
    r.raise_for_status()
    return r.json().get("result", [])


def _tg_send(chat_id, text) -> bool:
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
    if r.ok:
        log.info("Telegram reply sent to chat_id=%s (%d chars)", chat_id, len(text))
        return True
    log.error("Telegram sendMessage failed: %d %s", r.status_code, r.text[:200])
    return False


def _tg_typing(chat_id):
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction",
                      json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except Exception as e:
        log.warning("Telegram typing indicator failed: %s", e)


def extract_reply_context(msg: dict):
    reply_to = msg.get("reply_to_message")
    if not reply_to:
        return None
    parts = ["Telegram reply context:"]
    orig_from = reply_to.get("from", {})
    orig_name = orig_from.get("first_name", "Unknown")
    parts.append(f"Replying to message {reply_to.get('message_id')} from {orig_name}:")
    orig_text = reply_to.get("text") or reply_to.get("caption") or "(no text)"
    parts.append(f'"{orig_text}"')
    quote = msg.get("quote")
    if quote and quote.get("text"):
        parts.append(f"Quoted: \"{quote['text']}\"")
    parts.append("")
    parts.append("Anthony's message:")
    return "\n".join(parts)


def _tg_get_file_path(file_id: str) -> str:
    r = requests.post(f"{TELEGRAM_API}/getFile", json={"file_id": file_id}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getFile failed: {data}")
    file_path = data.get("result", {}).get("file_path")
    if not file_path:
        raise RuntimeError("Telegram getFile response did not include file_path")
    return file_path


def _tg_download_file(file_path: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with destination.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    fh.write(chunk)


def _telegram_audio_attachment(msg: dict):
    voice = msg.get("voice")
    if voice and voice.get("file_id"):
        return {
            "kind": "voice",
            "file_id": voice["file_id"],
            "file_name": f"voice-{msg.get('message_id', 'message')}.ogg",
            "mime_type": "audio/ogg",
        }
    audio = msg.get("audio")
    if audio and audio.get("file_id"):
        return {
            "kind": "audio",
            "file_id": audio["file_id"],
            "file_name": audio.get("file_name") or f"audio-{msg.get('message_id', 'message')}",
            "mime_type": audio.get("mime_type", "audio/unknown"),
        }
    document = msg.get("document")
    if document and document.get("file_id") and looks_transcribable_file(
            document.get("file_name"), document.get("mime_type")):
        return {
            "kind": "document",
            "file_id": document["file_id"],
            "file_name": document.get("file_name") or f"document-{msg.get('message_id', 'message')}",
            "mime_type": document.get("mime_type", "application/octet-stream"),
        }
    return None


def _telegram_text_or_transcript(update: dict, request_id: str):
    msg = update.get("message") or {}
    text = msg.get("text", "").strip()
    if text:
        return text, update

    attachment = _telegram_audio_attachment(msg)
    if not attachment:
        return None, update

    temp_dir = Path(tempfile.mkdtemp(prefix=f"james-audio-{request_id[:8]}-"))
    try:
        file_path = _tg_get_file_path(attachment["file_id"])
        suffix = Path(file_path).suffix or Path(attachment["file_name"]).suffix or ".ogg"
        local_audio = temp_dir / f"telegram-{attachment['kind']}{suffix}"
        _tg_download_file(file_path, local_audio)
        transcript = transcribe_local_audio(local_audio)
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(str(e)) from e
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    transcript = transcript.strip()
    if not transcript:
        raise TranscriptionError("transcription returned empty text")

    augmented_update = dict(update)
    augmented_message = dict(msg)
    augmented_message["text"] = transcript
    augmented_message["transcription"] = {
        "kind": attachment["kind"],
        "file_name": attachment["file_name"],
        "mime_type": attachment["mime_type"],
        "source_file_path": file_path,
    }
    augmented_update["message"] = augmented_message
    return transcript, augmented_update


def _dead_letter(channel: str, provider_event_id: str, reason: str, raw_update: dict):
    """Persist an inbound update that intake terminally rejected, so it is never
    silently dropped. Best-effort: a dead-letter failure must not wedge polling."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO channel_dead_letter (channel, provider_event_id, reason, raw_update)
                VALUES (%s, %s, %s, %s)
            """, (channel, provider_event_id, reason, psycopg2.extras.Json(raw_update)))
        conn.commit()
        log.error("Dead-lettered %s/%s: %s", channel, provider_event_id, reason)
    except Exception as e:
        conn.rollback()
        log.error("Dead-letter write failed for %s/%s (%s): %s",
                  channel, provider_event_id, reason, e)
    finally:
        conn.close()


def _handle_update(update: dict) -> str:
    """Hand one Telegram update off to the admin intake API.

    Returns:
      "terminal"  — definitively handled (2xx), nothing to enqueue, or dead-lettered
                    (422). The caller may advance the offset past this update.
      "retryable" — intake could not confirm (admin down / timeout / 5xx). The
                    caller must NOT advance the offset; re-poll the same update.
    """
    msg = update.get("message")
    if not msg:
        return "terminal"  # non-message update (nothing to enqueue)

    request_id = new_request_id()
    try:
        text, _raw = _telegram_text_or_transcript(update, request_id)
    except TranscriptionError as e:
        log.warning("Transcription failed for request_id=%s: %s", request_id, e)
        return "terminal"

    if not text:
        return "terminal"

    chat_id   = str(msg["chat"]["id"])
    from_id   = str(msg["from"]["id"])
    from_name = (
        " ".join(filter(None, [
            msg["from"].get("first_name"),
            msg["from"].get("last_name"),
        ])) or msg["from"].get("username") or from_id
    )

    reply_context = extract_reply_context(msg)
    if reply_context:
        text = f"{reply_context}\n{text}"

    provider_event_id = f"{msg['message_id']}:{chat_id}"
    try:
        r = requests.post(
            f"{ADMIN_API_URL}/messages",
            json={
                "channel": "telegram",
                "from_id": from_id,
                "from_name": from_name,
                "chat_id": chat_id,
                "message_text": text,
                "provider_event_id": provider_event_id,
            },
            timeout=10,
        )
    except requests.RequestException as e:
        # Connection refused / timeout — admin API not answering. Retry the update.
        log.warning("Intake handoff retryable (network) for %s: %s", provider_event_id, e)
        return "retryable"

    if r.ok:
        status = r.json().get("status")
        if status == "accepted":
            _tg_typing(chat_id)
        elif status == "duplicate":
            pass  # already enqueued (idempotent replay is expected on retry)
        elif status in ("queued_for_review", "declined"):
            log.info("Intake %s for %s: %s", status, from_id, r.json())
        else:
            log.warning("Unexpected intake status %s for %s", status, from_id)
        return "terminal"

    # 422 = unprocessable (malformed/poison) — will never succeed. Dead-letter it
    # rather than wedge the channel; advance past it.
    if r.status_code == 422:
        _dead_letter("telegram", provider_event_id,
                     f"intake 422: {r.text[:300]}", update)
        return "terminal"

    # 5xx / other — transient server-side failure. Retry the same update.
    log.warning("Intake handoff retryable (HTTP %d) for %s: %s",
                r.status_code, provider_event_id, r.text[:200])
    return "retryable"


def telegram_adapter():
    log.info("Telegram adapter started")
    offset = None
    backoff = INTAKE_BACKOFF_MIN_SECONDS

    while True:
        try:
            updates = _tg_get_updates(offset)
        except requests.RequestException as e:
            log.warning("Telegram network error: %s — retrying in 5s", e)
            time.sleep(5)
            continue
        except Exception as e:
            log.error("Telegram getUpdates error: %s", e, exc_info=True)
            time.sleep(5)
            continue

        for update in updates:
            try:
                outcome = _handle_update(update)
            except Exception as e:
                # Unexpected bug handling this update: treat as poison, dead-letter
                # and move on so one bad message can't freeze the channel forever.
                log.error("Unhandled error processing update_id=%s: %s",
                          update.get("update_id"), e, exc_info=True)
                _dead_letter("telegram", str(update.get("update_id", "")),
                             f"unhandled: {e}", update)
                outcome = "terminal"

            if outcome == "retryable":
                # Do NOT advance the offset — Telegram will re-deliver this same
                # update. Back off (bounded), then re-poll. Intake is idempotent
                # (UNIQUE channel_events(channel, provider_event_id)), so replay
                # cannot double-enqueue.
                log.warning("Intake retryable for update_id=%s — backing off %ds",
                            update.get("update_id"), backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, INTAKE_BACKOFF_MAX_SECONDS)
                break  # re-poll with the SAME (un-advanced) offset

            # Terminal outcome — safe to advance past this update.
            offset = update["update_id"] + 1
            backoff = INTAKE_BACKOFF_MIN_SECONDS


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    log.info("James gateway started")
    apply_schema()
    DurableWorkflowWorker().start()
    start_internal_server()
    telegram_adapter()


if __name__ == "__main__":
    main()
