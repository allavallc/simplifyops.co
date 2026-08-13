# Story 8 - MCP Connector Framework

## Status
Not started — requires Story 7 (tool contexts) complete

## Problem
James has no governed tools. He can browse, but cannot read/write Google Calendar, Gmail, Drive, or Sheets in a way that is authorized through the app governance model. Direct Hermes skills bypass request_id, person_id, authority, and audit.

## Goal
Repo-owned MCP servers that use tool context tokens to authorize tool calls. Each tool resolves the token to get person_id, authority, and request context before doing anything. Business logic stays in shared services — not in tool definitions.

## Required Shape (per arch doc)
```
connectors/<domain>/
  client.py       — provider API details
  service.py      — business logic, auth lookup, validation, errors
  mcp_server.py   — FastMCP tool definitions
  __init__.py
```

## Connectors To Build (in order)
1. Google Calendar — list/get/create/update/delete events, respond to invite
2. Gmail — send, search, read, forward, label, archive
3. Google Drive — create/list/get/update/share/delete files
4. Google Sheets — get/update/append/clear values
5. Brain/context repo — read-only allowlisted context files

## Prerequisites
- Story 7 (tool context tokens) — done
- Google OAuth connection managed by admin API (not yet built)
- MCP servers run as stdio subprocesses registered in Hermes config

## Key Constraint
Tools must not return secrets, raw config, OAuth tokens, or expanded env values. Tool descriptions must be clear enough for Hermes to choose tools without app-side prompt routing.
