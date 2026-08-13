# Story 7 - Tool Context Tokens

## Status
In progress — token creation and resolution endpoint built; MCP connectors not yet built

## Problem
MCP tools need to resolve request context (person_id, authority, channel, timezone) without the gateway exposing raw session data or the tools having direct DB access. There is no secure handoff mechanism between the governed runtime bridge and tool calls.

## Goal
Short-lived opaque tokens passed in the system_message. MCP tools call `GET /api/tool-contexts/{token}` to get full execution context. Token expires after 30 minutes.

## What Was Built
- `tool_contexts` table (in both gateway and admin_api schemas)
- `create_tool_context()` in gateway — creates token, stores hash, returns raw token
- `GET /api/tool-contexts/{token}` in admin API — resolves hash, returns context if not expired
- Token included in `system_message` on every Hermes call
- `get_person_context()` in gateway — looks up person_id, email, timezone from people table

## What Is Pending
- MCP connector framework (Story 8) needs this as a prerequisite
- Token cleanup job (expired rows accumulate — add periodic DELETE WHERE expires_at < now())
- Per-channel override cap in Settings UI

## Key Files
- `gateway/gateway.py` — create_tool_context(), get_person_context()
- `admin_api/routes/tool_contexts.py` — resolution endpoint
- `admin_api/schema.sql`, `gateway/sql/schema.sql` — tool_contexts table
