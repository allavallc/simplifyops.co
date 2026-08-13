# Story 3 - DB-Backed Governance

## Status
Completed 2026-08-08

## Problem
Governance was a flat text file (`whitelist.md`) — one Telegram ID per line. It couldn't express authority levels, block senders, or control memory influence. Any new channel would need its own file.

## Goal
Move governance to the `people` table with `authority`, `can_converse`, `can_influence`, and `status` columns. Unknown senders go to an admin inbox rather than being silently dropped.

## What Was Built
- Added `authority`, `can_converse`, `can_influence` columns to `people`
- `person_identities` table for typed identity mappings (telegram, email, phone)
- `governance_check()` in gateway queries DB instead of reading a file
- Whitelist file deleted
- Inbox approval now writes to `people` + `person_identities` with `authority=contact`
- Audit logging on governance decisions

## Key Files
- `gateway/gateway.py` — governance_check()
- `people-whitelist/src/routes/inboxRoutes.js` — approval flow (now disabled)
- `admin_api/routes/inbox.py` — approval in FastAPI
