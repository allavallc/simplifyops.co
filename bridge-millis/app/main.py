import hashlib
import hmac
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

load_dotenv()

app = FastAPI(title="SimplifyOps Unified Ingress")

HERMES_API_URL = os.getenv("HERMES_API_URL", "http://localhost:3000/chat")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")
MILLIS_WEBHOOK_SECRET = os.getenv("MILLIS_WEBHOOK_SECRET", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
HERMES_TIMEOUT_SECONDS = float(os.getenv("HERMES_TIMEOUT_SECONDS", "2.3"))


def _verify_hmac_sha256(raw_body: bytes, signature: str | None, secret: str, missing_code: str, invalid_code: str) -> None:
    if not secret:
        return
    if not signature:
        raise HTTPException(status_code=401, detail=missing_code)
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature.strip().removeprefix("sha256=")
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail=invalid_code)


def _normalize_payload(source: str, payload: dict[str, Any]) -> tuple[str, str]:
    source = source.lower()

    if source == "millis":
        transcript = payload.get("transcript") or payload.get("text") or payload.get("message") or ""
        session_key = payload.get("call_id") or payload.get("conversation_id") or "unknown_call"
        if not isinstance(transcript, str) or not transcript.strip():
            raise HTTPException(status_code=400, detail="missing_transcript")
        return transcript.strip(), f"millis_{session_key}"

    if source == "telegram":
        # Telegram webhook Update format
        msg = payload.get("message") or payload.get("edited_message") or {}
        text = msg.get("text") or ""
        chat = msg.get("chat", {})
        chat_id = chat.get("id", "unknown_chat")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=400, detail="missing_text")
        return text.strip(), f"telegram_{chat_id}"

    raise HTTPException(status_code=400, detail="unsupported_source")


async def _query_hermes(message: str, session_id: str, source: str) -> str:
    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    body = {
        "message": message,
        "session_id": session_id,
        "source": source,
    }

    timeout = httpx.Timeout(HERMES_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(HERMES_API_URL, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()

    reply = data.get("response") or data.get("message") or ""
    if not isinstance(reply, str) or not reply.strip():
        return "I heard you. Please repeat that once."
    return reply.strip()


async def _send_telegram_message(chat_id: int | str, text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="missing_telegram_bot_token")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    timeout = httpx.Timeout(HERMES_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/messages")
async def messages(
    request: Request,
    x_source: str | None = Header(default=None),
    x_millis_signature: str | None = Header(default=None),
    x_telegram_signature: str | None = Header(default=None),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    raw = await request.body()
    payload = await request.json()

    source = (
        x_source
        or request.query_params.get("source")
        or payload.get("source")
        or "millis"
    ).lower()

    if source == "millis":
        _verify_hmac_sha256(raw, x_millis_signature, MILLIS_WEBHOOK_SECRET, "missing_millis_signature", "invalid_millis_signature")
    elif source == "telegram":
        if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="invalid_telegram_secret")

    message, session_id = _normalize_payload(source, payload)

    try:
        reply = await _query_hermes(message, session_id, source)
        if source == "telegram":
            msg = payload.get("message") or payload.get("edited_message") or {}
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            if chat_id is None:
                raise HTTPException(status_code=400, detail="missing_chat_id")
            await _send_telegram_message(chat_id, reply)
            return {"response": "ok"}
        return {"response": reply}
    except httpx.TimeoutException:
        return {"response": "I’m still processing that. Please try again in a second."}
    except httpx.HTTPError:
        return {"response": "I’m having trouble reaching my backend right now. Please try again."}


@app.post("/respond")
async def respond_compat(request: Request, x_millis_signature: str | None = Header(default=None)) -> dict[str, str]:
    raw = await request.body()
    _verify_hmac_sha256(raw, x_millis_signature, MILLIS_WEBHOOK_SECRET, "missing_millis_signature", "invalid_millis_signature")
    payload = await request.json()
    payload["source"] = "millis"

    message, session_id = _normalize_payload("millis", payload)
    try:
        reply = await _query_hermes(message, session_id, "millis")
        return {"response": reply}
    except httpx.TimeoutException:
        return {"response": "I’m still processing that. Please try again in a second."}
    except httpx.HTTPError:
        return {"response": "I’m having trouble reaching my backend right now. Please try again."}
