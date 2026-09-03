# Story 62 - Fix James's reply mojibake (UTF-8 decoded as Latin-1)

## Status
**Done.** Bugfix — user-facing.

## Symptom
Every James reply with "smart" punctuation came out garbled to real users (e.g. John): curly quotes
`“ ”`, apostrophes `’`, and em-dashes `—` rendered as mojibake like `Ã¢â‚¬Å“…Ã¢â‚¬ï¿½`. The corrupted
text is what's stored in `work_items.reply_text` and what's sent to Telegram.

## Root cause
The runtime streams replies as **`text/event-stream` with no charset**. `requests` then defaults
`Response.encoding` to **ISO-8859-1** (RFC 2616 for `text/*`), so
`hermes_client.call_hermes` → `iter_lines(decode_unicode=True)` mis-decoded the UTF-8 reply as
Latin-1. Byte proof: `“` (U+201C, UTF-8 `E2 80 9C`) was stored as `C3 A2 C2 80 C2 9C` — exactly
those bytes decoded as Latin-1 then re-encoded UTF-8 on storage. Not a prompt/soul issue.

## Fix
`gateway/hermes_client.py` — set `resp.encoding = "utf-8"` on the streamed response before reading it
(in `_chat_stream`, covering the initial call + the stale-session retry). One line; the runtime→gateway
boundary (protected rule 10) is the right place.

## Tests
`tests/test_sse_encoding.py` (3): pins that `text/event-stream` defaults to ISO-8859-1, that the
default mojibakes smart punctuation, and that the `utf-8` override restores it. `requests` added to
`requirements-dev.txt` (app dep now exercised by tests).

## Scope / limits
- Fixes all **new** replies. Already-garbled rows in `work_items.reply_text` are left as historical
  data (not rewritten).
- Deploy: restart `simplifyops-gateway.service` (runs the worker that calls `hermes_client`).

## Acceptance
- Full ruff + pytest green (incl. the new regression tests); gateway restarted; next real reply with
  smart punctuation renders correctly. Merged.

## Review
One-line fix at the `hermes_client` runtime boundary (rule 10) with a rationale comment; 3 regression
tests pin the mechanism (text/event-stream→ISO-8859-1 default, default mojibakes, utf-8 restores).
brooks-review/audit: minimal, correct, no god-module/coupling/dup. No 🔴/🟡. **Gate:** rebased on
`origin/main`; full ruff clean; pytest 29 green (3 new). Deployed by restarting
`simplifyops-gateway.service`. **Done.**
