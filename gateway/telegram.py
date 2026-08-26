"""Telegram channel adapter: long-poll, send, attachments/transcription, intake handoff.

Extracted from the gateway.py god-module (story-26). `send_outbound` is the
channel-agnostic outbound entry point (currently Telegram-only).
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

import psycopg2.extras
import requests
from gwdb import get_db_conn
from intake import new_request_id
from logging_setup import get_logger
from transcription import TranscriptionError, looks_transcribable_file, transcribe_local_audio

log = get_logger("simplifyops-gateway")

BOT_TOKEN                  = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API               = f"https://api.telegram.org/bot{BOT_TOKEN}"
ADMIN_API_URL              = os.environ.get("ADMIN_API_URL", "http://127.0.0.1:3000")
# Intake durability: how long to back off before re-polling the SAME Telegram
# update when handoff to the admin API is retryable (admin down / 5xx / timeout).
# The offset is never advanced past an unconfirmed update, so nothing is dropped.
INTAKE_BACKOFF_MIN_SECONDS = int(os.environ.get("INTAKE_BACKOFF_MIN_SECONDS", "1"))
INTAKE_BACKOFF_MAX_SECONDS = int(os.environ.get("INTAKE_BACKOFF_MAX_SECONDS", "30"))


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


def send_outbound(channel: str, chat_id: str, text: str) -> bool:
    if channel == "telegram":
        return _tg_send(chat_id, text)
    log.error("No outbound sender for channel=%s", channel)
    return False


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
