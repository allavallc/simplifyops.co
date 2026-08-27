"""Durable workflow worker — claims work_items and runs the governed
message path: reply_ready shortcut, else person-context -> Hermes -> outbound,
with retry/dead-letter semantics.

Extracted from the gateway.py god-module (story-26).
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import psycopg2.extras
from governance import get_person_context
from gwdb import get_db_conn
from hermes_client import call_hermes
from intake import build_prompt
from logging_setup import get_logger
from sessions import append_user_history
from telegram import _tg_send, send_outbound

log = get_logger("simplifyops-gateway")

WORKER_CONCURRENCY  = int(os.environ.get("GATEWAY_WORKER_CONCURRENCY",  "3"))
WORKER_POLL_SECONDS = int(os.environ.get("GATEWAY_WORKER_POLL_SECONDS", "2"))
WORKER_LOCK_SECONDS = int(os.environ.get("GATEWAY_WORKER_LOCK_SECONDS", "300"))
WORKER_RETRY_SECONDS = int(os.environ.get("GATEWAY_WORKER_RETRY_SECONDS", "30"))
WORKER_MAX_ATTEMPTS = 3
DELAY_THRESHOLD_MINUTES = 30


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
            elapsed_minutes = (datetime.now(UTC) - requested_at).total_seconds() / 60
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
