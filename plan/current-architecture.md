# Current Architecture (SimplifyOps)

Last updated: 2026-08-10

## Purpose
Canonical architecture snapshot for sharing with humans or other LLMs.

## Mandatory update rule
Before any architecture/system decision or architecture doc edit in this repo:

1. Run from repo root:
```bash
graphify update .
```
2. Read `graphify-out/GRAPH_REPORT.md`
3. Update this file if anything architecture-relevant changed.

## Message flow (current)

```
Telegram user message
  -> gateway.py Telegram adapter (long-poll)
  -> POST http://127.0.0.1:3000/messages  (FastAPI admin API)
  -> governance check: person_identities -> people (can_converse, authority)
  -> unknown sender: contact_requests + no work item
  -> approved: requests row + channel_events idempotency + work_items row (status=ready)
  -> DurableWorkflowWorker (in gateway.py, concurrency=1)
  -> reads governance context from work_items.payload (no second DB lookup)
  -> POST http://127.0.0.1:8642/api/sessions/{id}/chat  (Hermes API server)
  -> system_message: channel, sender authority, request ID
  -> reply saved (status=reply_ready)
  -> Telegram outbound send
  -> status=completed
```

## Services

| Service | Purpose | Port |
|---|---|---|
| `simplifyops-admin.service` | FastAPI control plane: POST /messages, admin UI, governance, audit | 3000 |
| `simplifyops-gateway.service` | Telegram adapter + DurableWorkflowWorker | — |
| `simplifyops-agent-runtime.service` | Hermes gateway run + API server | 8642 |
| `hindsight.service` | Hermes memory (self-hosted Hindsight) | 8888 |
| `claude-telegram-relay.service` | Claude Code via separate Telegram bot | — |

`people-whitelist.service` (Node.js) is **disabled** — replaced by FastAPI admin API.

## Key file locations

| Path | Purpose |
|---|---|
| `/home/pi/simplifyops/admin_api/` | FastAPI control plane |
| `/home/pi/simplifyops/gateway/gateway.py` | Telegram adapter + durable worker |
| `/home/pi/.hermes/profiles/simplifyops/` | Hermes profile root |
| `/home/pi/.hermes/profiles/simplifyops/SOUL.md` | Agent soul (edit source: `souls/james-bott.md`) |
| `/home/pi/.hermes/profiles/simplifyops/config.yaml` | Hermes model/memory/MCP config |
| `/home/pi/.config/relay.env` | Shared secrets (bot tokens, API keys, Google OAuth) |
| `/home/pi/.config/simplifyops-runtime.env` | Isolated env for agent runtime (no Telegram token) |

## Database

Single PostgreSQL instance, database `whitelist_app`, Unix socket `/var/run/postgresql`.

Key tables:
- `people` — governance: authority, can_converse, can_influence, status
- `person_identities` — typed identity mappings (telegram, email, phone)
- `requests` — one row per inbound message, source of request_id
- `channel_events` — provider-event idempotency
- `work_items` — durable workflow state (ready/processing/reply_ready/completed/failed_*)
- `hermes_session_mappings` — one persistent Hermes API session per user
- `session_history` — audit log of exchanges
- `contact_requests` — unknown sender queue for admin inbox
- `audit_log` — governance and admin action events

## Agent runtime

- Hermes v0.19.0, profile `simplifyops`, model `gpt-5.4-mini` via `openai-codex`
- Long-running process started by `simplifyops-agent-runtime.service`
- API server on `127.0.0.1:8642`, authenticated with `AGENT_API_KEY`
- One persistent session per user (`hermes_session_mappings` table)
- Session survives runtime restarts (loaded from Hermes SQLite `state.db`)
- Background review browser session bug fixed: `review_agent.close()` → `release_clients()`

## Memory

- Provider: Hindsight (self-hosted, local_external mode)
- API: `http://localhost:8888`
- DB: PostgreSQL `hindsight` + pgvector
- Embeddings: Google Gemini `gemini-embedding-001`
- Reranker: `rrf` (never `none` — crashes)

## Governance

1. `POST /messages` looks up sender via `person_identities` (identity_type, normalized_value)
2. Resolves to `people` row — checks `status=allowed`, `can_converse=true`
3. Unknown senders → `contact_requests` → admin inbox
4. Approved: work_items enqueued with authority + can_influence in payload
5. Worker reads payload — no second governance DB call

## Operational checks

```bash
# Services
systemctl is-active simplifyops-admin simplifyops-gateway simplifyops-agent-runtime hindsight

# Admin API health
curl -s http://127.0.0.1:3000/health

# Hermes API server health
curl -s http://127.0.0.1:8642/api/sessions \
  -H "Authorization: Bearer $AGENT_API_KEY" | head -1

# Hindsight health
curl -s http://127.0.0.1:8888/health

# Work item backlog
psql "postgresql:///whitelist_app?host=/var/run/postgresql" \
  -c "SELECT status, COUNT(*) FROM work_items GROUP BY status ORDER BY status;"

# Stuck processing items (after crash)
psql "postgresql:///whitelist_app?host=/var/run/postgresql" \
  -c "UPDATE work_items SET status='ready', locked_until=NULL WHERE status='processing' AND locked_until < now();"
```

## Admin UI

Available at `http://100.82.172.8:3000` (Tailscale) or `http://localhost:3000`.
Google OAuth login — redirect URI must be registered in Google Cloud Console.
Pages: Dashboard, People, Inbox, Activity Log.

## Source-of-truth order
1. Live runtime checks
2. `graphify-out/GRAPH_REPORT.md`
3. This file
4. Memory at `/home/pi/.claude/projects/-home-pi/memory/project_hermes.md`
