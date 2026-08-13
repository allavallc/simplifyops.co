# Story 4 - Hermes Runtime Bridge

## Status
Completed 2026-08-09

## Problem
Every message spawned a new `hermes -z` subprocess: cold start, 51 plugin loads, session restore from disk, LLM API call, exit. This was slow (13-150s), expensive, and meant James had no persistent session state between messages.

## Goal
Replace subprocess-per-message with a long-running Hermes process. The worker calls the Hermes API server via HTTP. One persistent session per user, reused across all messages.

## What Was Built
- `simplifyops-agent-runtime.service` — runs `hermes gateway run` with API server on `127.0.0.1:8642`
- `API_SERVER_KEY` in isolated env file (no Telegram token, so Hermes doesn't poll Telegram)
- `call_hermes()` replaced with HTTP `POST /api/sessions/{id}/chat`
- `hermes_session_mappings` table — one physical session per user
- Stale session detection (404/410) → clear mapping → retry with new session
- `system_message` with channel, authority, person context, request ID on every call

## Key Files
- `gateway/gateway.py` — call_hermes(), _ensure_agent_session()
- `/etc/systemd/system/simplifyops-agent-runtime.service`
- `/home/pi/.config/simplifyops-runtime.env`

## Bug Fixed
`background_review.py` lines 495+545: `review_agent.close()` → `review_agent.release_clients()` — prevented background review thread from destroying parent agent's browser session.
