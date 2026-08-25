"""Inbound intake: request IDs, durable enqueue, prompt building.

Extracted from the gateway.py god-module (story-26).
"""

import uuid

import psycopg2.errors
from gwdb import get_db_conn
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")


def new_request_id() -> str:
    return uuid.uuid4().hex


def build_prompt(text: str, delay_note: str = None) -> str:
    if delay_note:
        return f"{delay_note}\n\n{text}"
    return text


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
