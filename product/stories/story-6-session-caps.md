# Story 6 - Session Caps and Context Growth Control

## Status
Completed 2026-08-10

## Problem
James's Hermes session accumulated 735+ messages and 1.75M cumulative tokens. Each new message carried the full history into the prompt, making replies slow and expensive (Story 53 in source system documented 312k provider input tokens for a 39-character message).

## Goal
Rotate the physical Hermes session before each handoff when the message count hits a configured cap. Preserve logical conversation continuity — the logical session ID stays stable, only the physical session ID changes.

## What Was Built
- `hermes_session_mappings` schema extended: `logical_session_id`, `physical_rotations`, `rotation_reason`, `message_count_at_rotation`
- `admin_settings` table with `session_message_cap` default (100 messages)
- `get_session_message_cap()` reads from DB, falls back to env var
- `_get_session_message_count()` calls `GET /api/sessions/{id}` before each handoff
- Rotation at cap: create new physical session, update mapping, log with logical/old/new/count/cap/request_id
- `BROWSER_INACTIVITY_TIMEOUT=3600` set in agent runtime env (was 120s default — caused browser session loss between turns)

## Cap defaults (per Story 79 in source system)
- Global default: 100 messages
- Phone: 50 (not yet implemented — no phone channel)
- Email: 200 (not yet implemented — no email channel)
- Per-channel override: planned for Settings admin page

## Key Files
- `gateway/gateway.py` — call_hermes(), get_session_message_cap(), rotation logic
- `gateway/sql/schema.sql` — hermes_session_mappings, admin_settings
- `/home/pi/.config/simplifyops-runtime.env` — BROWSER_INACTIVITY_TIMEOUT
