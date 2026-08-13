"""
POST /messages — canonical governed intake for all user-facing channels.

Responsibilities:
  1. Parse and normalize the inbound channel event
  2. Create or preserve requests.id
  3. Claim provider event idempotency in channel_events
  4. Governance check: look up sender via person_identities → people
  5. Unknown senders → contact_requests, no work item
  6. Declined senders (blocked / can_converse=false) → 200 with no work item
  7. Approved senders → enqueue work_items row
  8. Write audit event for governance decision
  9. Return 202 Accepted immediately (never wait for runtime)
"""

import uuid
import json
from datetime import datetime, timezone

import psycopg2.errors
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import Db
from audit import log_audit

router = APIRouter()


class MessagePayload(BaseModel):
    channel: str
    provider: str | None = None
    from_id: str
    from_name: str | None = None
    chat_id: str
    message_text: str
    provider_event_id: str | None = None
    raw: dict | None = None


def _new_request_id() -> str:
    return uuid.uuid4().hex


def _governance(conn, channel: str, from_id: str) -> dict | None:
    """
    Resolve sender via person_identities → people.
    Returns person row or None if unknown.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT p.id, p.person_email, p.authority, p.can_converse, p.can_influence, p.status
            FROM person_identities pi
            JOIN people p ON p.id = pi.person_id
            WHERE pi.identity_type = %s AND pi.normalized_value = %s
              AND p.deleted_at IS NULL
            LIMIT 1
        """, (channel, from_id))
        return cur.fetchone()


def _enqueue(conn, request_id: str, channel: str, provider: str | None,
             from_id: str, from_name: str | None, chat_id: str,
             message_text: str, provider_event_id: str | None,
             raw: dict | None, person_id: int,
             authority: str = "member", can_influence: bool = True) -> int | None:
    """
    Atomically insert requests + channel_events + work_items.
    Returns work_items.id or None if duplicate provider event.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO requests (id, channel, provider, from_id, from_name, chat_id, message_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (request_id, channel, provider, from_id, from_name, chat_id, message_text))

        if provider_event_id:
            try:
                cur.execute("""
                    INSERT INTO channel_events (channel, provider_event_id, request_id)
                    VALUES (%s, %s, %s)
                """, (channel, provider_event_id, request_id))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                return None  # duplicate — already enqueued

        cur.execute("""
            INSERT INTO work_items (request_id, status, payload)
            VALUES (%s, 'ready', %s)
            RETURNING id
        """, (request_id, json.dumps({
            "person_id": person_id,
            "channel": channel,
            "from_id": from_id,
            "chat_id": chat_id,
            "authority": authority,
            "can_influence": can_influence,
        })))
        return cur.fetchone()[0]


def _queue_contact_request(conn, request_id: str, channel: str, from_id: str,
                            from_name: str | None, chat_id: str,
                            message_text: str, raw: dict | None):
    with conn.cursor() as cur:
        existing = conn.cursor()
        existing.execute(
            "SELECT id FROM contact_requests WHERE request_id = %s LIMIT 1",
            (request_id,)
        )
        if existing.fetchone():
            return
        cur.execute("""
            INSERT INTO contact_requests
                (request_id, channel, from_id, from_name, chat_id, message_text, raw)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (request_id, channel, from_id, from_name, chat_id, message_text,
              json.dumps(raw) if raw else None))


@router.post("/messages", status_code=202)
async def intake(payload: MessagePayload, request: Request):
    request_id = _new_request_id()
    channel   = payload.channel
    from_id   = payload.from_id
    from_name = payload.from_name
    chat_id   = payload.chat_id

    with Db() as conn:
        person = _governance(conn, channel, from_id)

        if not person:
            _queue_contact_request(
                conn, request_id, channel, from_id, from_name,
                chat_id, payload.message_text, payload.raw,
            )
            log_audit("system", "governance_unknown_sender",
                      new_value={"channel": channel, "from_id": from_id,
                                 "request_id": request_id})
            return {"request_id": request_id, "status": "queued_for_review"}

        if person["status"] != "allowed":
            log_audit("system", "governance_blocked",
                      subject_email=person["person_email"],
                      new_value={"channel": channel, "from_id": from_id,
                                 "reason": f"status={person['status']}"})
            return {"request_id": request_id, "status": "declined"}

        if not person["can_converse"]:
            log_audit("system", "governance_declined",
                      subject_email=person["person_email"],
                      new_value={"channel": channel, "from_id": from_id,
                                 "reason": "can_converse=false"})
            return {"request_id": request_id, "status": "declined"}

        item_id = _enqueue(
            conn, request_id, channel, payload.provider,
            from_id, from_name, chat_id,
            payload.message_text, payload.provider_event_id,
            payload.raw, person["id"],
            authority=person["authority"],
            can_influence=person["can_influence"],
        )

        if item_id is None:
            return {"request_id": request_id, "status": "duplicate"}

        log_audit("system", "governance_approved",
                  subject_email=person["person_email"],
                  new_value={
                      "channel": channel, "from_id": from_id,
                      "request_id": request_id, "work_item_id": item_id,
                      "authority": person["authority"],
                  })

    return {"request_id": request_id, "status": "accepted", "work_item_id": item_id}
