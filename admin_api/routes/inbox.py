"""
Inbox — unknown sender contact requests.
Approve → creates/updates people + person_identities + triggers gateway reply.
"""

import json
import os
import uuid

import httpx
import psycopg2.extras
from audit import log_audit
from db import Db
from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/inbox")

ADMIN_API_URL = os.environ.get("ADMIN_API_URL", "http://127.0.0.1:3000")


@router.post("")
async def queue_contact_request(body: dict):
    """Called by the gateway adapter when an unknown sender messages."""
    request_id = str(body.get("request_id") or uuid.uuid4().hex)
    channel      = body.get("channel")
    from_id      = str(body.get("from_id", ""))
    from_name    = body.get("from_name")
    chat_id      = str(body.get("chat_id", ""))
    message_text = body.get("message_text", "")
    raw          = body.get("raw")

    if not (channel and from_id and chat_id and message_text):
        raise HTTPException(400, "missing_fields")

    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM contact_requests WHERE request_id = %s LIMIT 1",
                (request_id,)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE contact_requests
                    SET channel=%s, from_id=%s, from_name=%s, chat_id=%s,
                        message_text=%s, raw=%s, updated_at=now()
                    WHERE id=%s
                """, (channel, from_id, from_name, chat_id, message_text,
                      json.dumps(raw) if raw else None, existing[0]))
                return {"queued": True, "id": existing[0], "request_id": request_id, "deduplicated": True}

            cur.execute("""
                INSERT INTO contact_requests
                    (request_id, channel, from_id, from_name, chat_id, message_text, raw)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (request_id, channel, from_id, from_name, chat_id, message_text,
                  json.dumps(raw) if raw else None))
            row_id = cur.fetchone()[0]

    return {"queued": True, "id": row_id, "request_id": request_id}


@router.get("")
async def list_requests(status: str = "pending", admin=Depends(require_admin)):
    where = "" if status == "all" else "WHERE status = %s"
    params = [] if status == "all" else [status]
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT id, request_id, channel, from_id, from_name, chat_id,
                       left(message_text, 300) AS message_preview,
                       length(message_text) AS message_length,
                       status, created_at, reviewed_at, reviewed_by
                FROM contact_requests
                {where}
                ORDER BY created_at DESC
            """, params)
            return list(cur.fetchall())


@router.get("/count")
async def pending_count(admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::int FROM contact_requests WHERE status = 'pending'")
            return {"pending": cur.fetchone()[0]}


@router.post("/{req_id}/approve")
async def approve(req_id: int, admin=Depends(require_admin)):
    reviewer = admin["email"]
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                UPDATE contact_requests
                SET status='approved', reviewed_at=now(), reviewed_by=%s, updated_at=now()
                WHERE id=%s AND status IN ('pending','ignored')
                RETURNING *
            """, (reviewer, req_id))
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "not_found")

        # Upsert person with contact authority
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO people
                    (person_name, person_email, authority, can_converse, can_influence,
                     status, telegram_id, created_by)
                VALUES (%s, %s, 'contact', true, false, 'allowed', %s, %s)
                ON CONFLICT (person_email) DO UPDATE SET
                    status = 'allowed',
                    authority = COALESCE(people.authority, 'contact'),
                    can_converse = true,
                    telegram_id = COALESCE(EXCLUDED.telegram_id, people.telegram_id),
                    updated_at = now()
                RETURNING id
            """, (row["from_name"], f"{row['from_id']}@{row['channel']}",
                  row["from_id"] if row["channel"] == "telegram" else None, reviewer))
            person_id = cur.fetchone()["id"]

        # Upsert identity
        if row["channel"] == "telegram":
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO person_identities
                        (person_id, identity_type, identity_value, normalized_value, is_primary)
                    VALUES (%s, 'telegram', %s, %s, true)
                    ON CONFLICT (identity_type, normalized_value) DO UPDATE
                        SET person_id = EXCLUDED.person_id
                """, (person_id, row["from_id"], row["from_id"]))

    log_audit(reviewer, "inbox_approve",
              new_value={"request_id": row["request_id"], "channel": row["channel"],
                         "from_id": row["from_id"]})

    # Enqueue the original message through POST /messages now that sender is approved
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{ADMIN_API_URL}/messages", json={
                "channel": row["channel"],
                "from_id": row["from_id"],
                "from_name": row["from_name"],
                "chat_id": row["chat_id"],
                "message_text": row["message_text"],
                "provider_event_id": f"inbox-approved:{row['request_id']}",
            })
    except Exception:
        pass  # non-fatal — admin can resend or person can message again

    return {"ok": True, "request": dict(row)}


@router.post("/{req_id}/reject")
async def reject(req_id: int, admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE contact_requests
                SET status='rejected', reviewed_at=now(), reviewed_by=%s, updated_at=now()
                WHERE id=%s RETURNING id
            """, (admin["email"], req_id))
            if not cur.fetchone():
                raise HTTPException(404, "not_found")
    log_audit(admin["email"], "inbox_reject", new_value={"id": req_id})
    return {"ok": True}


@router.post("/{req_id}/ignore")
async def ignore(req_id: int, admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE contact_requests
                SET status='ignored', reviewed_at=now(), reviewed_by=%s, updated_at=now()
                WHERE id=%s RETURNING id
            """, (admin["email"], req_id))
            if not cur.fetchone():
                raise HTTPException(404, "not_found")
    log_audit(admin["email"], "inbox_ignore", new_value={"id": req_id})
    return {"ok": True}
