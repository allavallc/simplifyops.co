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

## Architectural rules — PROTECTED invariants (approval required to change)

These are **protected architectural boundaries**, not suggestions. Each is a seam the codebase
depends on staying clean. **Violating, "refactoring around," or removing any of them requires
explicit owner approval recorded in a story** — an agent may not quietly break one to make a task
easier. The `brooks-audit` gate exists to catch drift against these boundaries; a finding that
touches one of these rules is a 🔴 by default. Day-to-day build/test/commit process for agents lives
in [`product/product-dev-guidelines.md`](../product/product-dev-guidelines.md).

1. **API-first backend, one contract per concern.** Business logic lives in the FastAPI layer and
   is exposed as JSON `/api/*`. Do not express the same decision in two output shapes or two
   services.
2. **Admin UI is server-rendered HTML (Jinja).** Admin pages are Jinja templates in
   `admin_api/templates/`, rendered by FastAPI. **No client-side JS frameworks (React/Vue/Svelte),
   no SPA, no bundler/build step (no npm/Vite).** Plain HTML/CSS/JS + Jinja only. (This is the
   current direction — it reverses the earlier React-SPA approach; see [[story-25]].)
3. **One responsibility per module — no god-modules.** A source file's job must be statable in one
   sentence. Adapters, workers, clients, and domain logic go in separate modules (e.g. the gateway
   is adapter / worker / hermes-client / governance / db, not one file — [[story-26]]). A file past
   ~400 lines is a smell to investigate, not a hard limit.
4. **One-way dependencies; the composition root only wires.** Handlers/routes depend on the shared
   foundation (`db`, `deps`, `audit`); `main.py` wires them together and nothing imports its
   composition root. No import cycles.
5. **Single source of truth for settings.** Runtime settings live in `admin_settings` and are read
   through one accessor per service — never re-read a key with a duplicated default literal in
   multiple places ([[story-27]]).
6. **Dependencies are repo-owned and declared.** Every import must resolve from the repo plus its
   declared manifests (`requirements*.txt` / `pyproject.toml`). No importing host-global modules
   (e.g. `/home/pi/*.py`). Logging is per-repo, not machine-wide ([[story-28]]).
7. **Test seams at every infrastructure boundary.** DB connections and HTTP/Telegram/Hermes clients
   are injected or wrapped so a test double can replace them without editing the module under test.
8. **Environments: local → staging → prod.** Work is developed locally (this machine), pushed to
   GitHub = **staging**, and promoted to **prod** as a separate, deliberate step. Never push work
   straight to prod. (Mechanism being established — [[story-30]]; until it lands, GitHub `main`
   pushes still reach the prod domain, so treat them with production care.)
9. **People governance has one source of truth: `people_service`.** The Jinja admin routes, the JSON
   `/api/admin/people*` endpoints, and runtime governance all read/write people, identities, and
   authority through `admin_api/people_service.py` — never inline SQL, duplicated `can_grant`/audit,
   or a second people code path. ([[story-31]])
10. **External runtimes are accessed only through an adapter.** Hermes is called only via a single
    `hermes_client` module (never inline HTTP to `:8642` in handlers/workers). That adapter is the
    *one* place a Hermes/package upgrade touches — this is what keeps upgrades safe instead of
    spaghetti. Same rule for any future external runtime/provider. ([[story-26]])
11. **Runtime config is environment-owned.** Live provider/model/tool/MCP config is per-environment,
    gitignored, and **never tracked in git or overwritten by a shared/pushed source** — each env's
    config must be able to differ. Config is edited per-env; secrets live in the secret store
    (presence-only in any UI); `config.yaml` is a generated artifact, never the hand-edited source
    of truth. ([[story-34]])

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

_(The legacy `people-whitelist.service` Node app has been **removed** — people governance is owned solely by the FastAPI admin API (`admin_api/`). Per the build blueprint, the legacy writer is retired, not kept as a parallel governance authority.)_

## Key file locations

| Path | Purpose |
|---|---|
| `/home/pi/simplifyops/admin_api/` | FastAPI control plane |
| `/home/pi/simplifyops/gateway/gateway.py` | Telegram adapter + durable worker |
| `/home/pi/.hermes/profiles/simplifyops/` | Hermes profile root |
| `/home/pi/.hermes/profiles/simplifyops/SOUL.md` | Agent soul (edit source: `souls/soul.md`) |
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

- Hermes **v0.20.5** (upgraded 2026-08-25 from v0.19.0 via the supported `install.sh`; pip installs
  are deprecated. Config auto-migrated `_config_version` 33 → 39. Rollback kit:
  `/home/pi/hermes-upgrade-backup-20260824-213008/`), profile `simplifyops`, `openai-codex`
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
