"""People governance lookups, unknown-sender queueing, and runtime person context.

Extracted from the gateway.py god-module (story-26).
"""

import os

import psycopg2.extras
import requests
from gwdb import get_db_conn
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")

INBOX_URL = os.environ.get("INBOX_URL", "http://127.0.0.1:3000/api/inbox")


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
