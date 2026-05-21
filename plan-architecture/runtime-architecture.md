# Runtime Architecture: Docker, Hermes, Honcho, Paperclip, and the messaging gateways

This is the operator-level reference for how the agent (referred to as **Atlas** below
as a placeholder name) actually runs. It covers what each component does, how a
request flows through them, and the pitfalls that have bitten us — so they don't
bite again.

If you're new: read top-to-bottom. If you're debugging: jump to **Pitfalls** first.

---

## 1. The pieces

| Component | Language | Role | Lives in |
|---|---|---|---|
| **Paperclip** (server + UI) | TypeScript / React | Issue tracking, dashboard, plugin host, all DB writes, channel auth, agent orchestration | `server/`, `ui/`, `packages/` |
| **Hermes** | Python | Sovereign-tier agent runtime: tool registry, skill broker, prompt builder, gateway | `hermes/` |
| **Honcho** | Python (third-party) | Per-human persistent memory keyed to `people.id` | `honcho/` (cloned from `plastic-labs/honcho`) |
| **Postgres (Paperclip)** | — | Paperclip's primary DB: 60+ tables (companies, people, issues, channel_auth, etc.) | `db` container, port `5433` |
| **Postgres (Honcho)** | pgvector | Honcho's separate DB, never mixed with Paperclip's | `honcho-db` container, internal only |
| **Redis (Honcho)** | — | Honcho's cache/queue layer | `honcho-redis` container, internal only |
| **Channel gateways** | inside Hermes | Telegram, Discord, Email — translate platform messages into Hermes calls | `hermes/gateway/` |

**The key principle:** Paperclip is the source of truth for everything except
per-human memory. Honcho is the source of truth for per-human memory only. They
never share a DB.

---

## 2. How a request flows

### Dashboard message (`User → Atlas via UI`)

```
Browser (UI)
  │
  ▼  HTTP POST /api/issues/:id/comments
Paperclip server
  │
  ├─► writes user comment to issue_comments
  │
  ├─► assigns the next run to Atlas via heartbeat scheduler
  │   (server/src/services/heartbeat.ts)
  │
  ▼
hermes-local adapter (TypeScript subprocess wrapper)
  │
  │   sets env vars including:
  │     ATLAS_PEER_USER_ID = the human's people.id
  │     HONCHO_BASE_URL    = http://honcho:8000
  │     ATLAS_API_URL      = http://server:3100
  │
  ▼  spawns python -m hermes.run_agent
Hermes (Python)
  │
  ├─► loads soul (hermes/souls/atlas.md)
  ├─► fetches Honcho peer card via HONCHO_BASE_URL + ATLAS_PEER_USER_ID
  ├─► selects skills via skill broker
  ├─► calls sovereign LLM (OpenRouter or Anthropic, per ATLAS_SOVEREIGN_PROVIDER)
  ├─► may call tools (honcho_search, decision_record, etc.)
  ├─► writes reply
  │
  ▼ stdout JSON parsed by adapter
Paperclip server
  │
  ├─► persists Atlas's reply to issue_comments
  ├─► logs cost_event for the run
  └─► emits live update via WebSocket
  │
  ▼
Browser (UI) receives the new comment
```

### Telegram message (`User → Atlas via Telegram bot`)

```
Telegram client
  │
  ▼ webhook / long-poll
hermes/gateway (Python, runs alongside Hermes container)
  │
  ├─► identifies sender via telegram_user_id
  │
  ├─► HTTP GET http://server:3100/api/channel-auth/check?platform=telegram&channelId=<id>
  │   (cached 30s, fails closed)
  │
  ├─── if not authorized ──► fixed polite rejection, no LLM call
  │
  ├─── if authorized:
  │      resolve people.id → set ATLAS_PEER_USER_ID
  │      forward the message to Hermes (same flow as dashboard from here)
  │
  ▼
Atlas's reply is sent back to the Telegram chat
  │
  └─► AND persisted to Paperclip's issue_comments
      so dashboard ↔ Telegram share the same conversation memory
```

**Why this works as cross-channel memory:** every reply is persisted in Paperclip's
`issue_comments` AND Honcho's per-human peer card. Whether the user asks via
dashboard or Telegram, Atlas sees the same thread + the same Honcho profile.

---

## 3. Container topology

`docker-compose.yml` defines **8 services** in two groups:

### Application group (Atlas's runtime)
- **`db`** — Postgres 17. Port `5433` exposed. Volume `<project>-pgdata`.
- **`server`** — Express + React. Host port configurable via `ATLAS_HOST_PORT`, default 3100. Depends on `db`.
- **`hermes`** — Python agent runtime + gateway. No port exposed (called by `server`).

### Honcho group (memory)
- **`honcho-db`** — pgvector/pg15. Internal only.
- **`honcho-redis`** — redis:8-alpine. Internal only.
- **`honcho`** — Honcho API server. Port `8001→8000` exposed (for debugging; Hermes uses internal `http://honcho:8000`).
- **`honcho-deriver`** — background worker. Currently disabled (`DERIVER_ENABLED=false` to stop credit drain). Healthcheck overridden to `NONE`.

### Service-to-service URLs (inside the compose network)
| From → To | URL |
|---|---|
| `hermes` → `server` | `http://server:3100` (set as `ATLAS_SERVER_URL` and `ATLAS_API_URL`) |
| `hermes` → `honcho` | `http://honcho:8000` (set as `HONCHO_BASE_URL`) |
| `server` → `hermes` | `http://hermes:8080` (set as `HERMES_URL`) |
| `server` → `db` | `postgres://atlas:atlas@db:5432/atlas_core` |
| `honcho` → `honcho-db` | `postgresql+psycopg://honcho:honcho@honcho-db:5432/honcho` |

---

## 4. Critical environment variables

### Paperclip server
| Var | Purpose | Notes |
|---|---|---|
| `DATABASE_URL` | Paperclip's Postgres | Set by compose to `db` service |
| `HERMES_URL` | Hermes endpoint for server-side calls | `http://hermes:8080` |
| `ATLAS_DEPLOYMENT_MODE` | `local_trusted` (no auth, dev) or `authenticated` (Better Auth + sessions) | Always `authenticated` on staging/prod |
| `ATLAS_PUBLIC_URL` | Externally-facing URL — used in emails, OAuth redirects, etc. | Updated by `deploy-staging.sh` to staging IP |
| `ATLAS_HOST_PORT` | Host port that maps to container's 3100 | Default 3100 (staging/prod). Local dev sets 3101 to avoid collision with `pnpm dev:server` |
| `BETTER_AUTH_SECRET` | Session signing | **Must differ between dev/staging/prod** |
| **`ATLAS_MIGRATION_AUTO_APPLY`** | Apply pending Drizzle migrations on server boot | **Must be `true` on staging/prod**. If missing, schema goes out of sync silently |

### Hermes
| Var | Purpose | Notes |
|---|---|---|
| `ATLAS_SOVEREIGN_PROVIDER` | `openrouter` (default) or `anthropic` | Wrong choice burns credits — see Pitfall #6 |
| `OPENROUTER_API_KEY` | Used when `ATLAS_SOVEREIGN_PROVIDER=openrouter` | |
| `ANTHROPIC_API_KEY` | Used when `ATLAS_SOVEREIGN_PROVIDER=anthropic`, AND used by Honcho deriver if enabled | |
| `GEMINI_API_KEY` | Used by Honcho for embeddings | Required even with deriver off — embeddings still fire on conclusions |
| `HONCHO_BASE_URL` | `http://honcho:8000` | Internal compose URL |
| `HONCHO_API_KEY` | `local-dev` for dev/staging | Honcho doesn't enforce; staying with placeholder is fine |
| `HERMES_HOME` | `/data` inside container | Where Hermes writes per-run state |
| **`ATLAS_PEER_USER_ID`** | The **human's** people.id (NOT the agent's) | **Set per-run by the adapter, NOT a static env var.** Setting it statically collapses all users into one Honcho profile |
| `TELEGRAM_BOT_TOKEN` | Telegram bot credential | **MUST differ between staging and prod** — see Pitfall #2 |

### Honcho (set by docker-compose.yml — generally don't touch)
| Var | Current value | Why |
|---|---|---|
| `EMBED_MESSAGES` | `false` | Off to save credits; conclusions still embed regardless |
| `DERIVER_ENABLED` | `false` | Off — was draining Anthropic credits |
| `SUMMARY_ENABLED` | `false` | Off — same reason |
| `DREAM_ENABLED` | `false` | Off — never validated |
| `LLM_EMBEDDING_PROVIDER` | `gemini` | Cheap enough to leave on |

---

## 5. Memory architecture (three layers)

| Layer | Scope | Home | How the agent reads/writes |
|---|---|---|---|
| **Personal** | Per human | Honcho peer card, keyed to `people.id` = `ATLAS_PEER_USER_ID` | `honcho_profile`, `honcho_context`, `honcho_search`, `honcho_conclude` tools |
| **Thread-local** | Within one issue | `issue_comments` table (Paperclip Postgres) | Auto-injected into prompt; no tool needed |
| **Institutional** | Company-level | `decisions` + `company_facts` tables (planned, not built yet) | `decision_record`, `decision_search`, `fact_record`, `fact_search` (planned) |

**Never** create a Honcho peer for a "company" — conflating personal and
institutional memory loses structure. Personal facts go to Honcho. Project facts go
to Paperclip's institutional tables (when built).

---

## 6. Pitfalls — read before debugging

### #1 — `honcho/` is a clone, not a submodule
The directory `./honcho/` is a full clone of `plastic-labs/honcho`. The comment in
`docker-compose.yml` says it's a submodule, but `.gitmodules` doesn't exist.
Consequences:
- Cloning the team repo does NOT pull Honcho. New devs must clone Honcho separately.
- The deploy script picks up `./honcho/` as untracked-not-gitignored and rsyncs it
  to the staging VM — which is why staging works at all.
- A future fix would be to either (a) make it a real submodule or (b) have the
  deploy script clone Honcho on the VM before `docker compose build`.

### #2 — Telegram bot tokens MUST differ between environments
If staging and prod share a token, both bots try to handle every Telegram update
and the user gets duplicate replies. Always create a separate staging bot via
BotFather (e.g., `@<project>_staging_bot`).

### #3 — `ATLAS_PEER_USER_ID` is the human, not the agent
This is the `people.id` of whoever is talking to the agent. The adapter sets it
per-run. Setting it as a static env var collapses every user into one Honcho
profile and the memory architecture silently breaks.

### #4 — Migrations don't auto-apply unless you say so
`ATLAS_MIGRATION_AUTO_APPLY=true` must be in staging/prod `.env` for new Drizzle
migrations to run on server boot. Without it, a deploy succeeds, the server
starts, but the schema is stale — and you find out hours later when something
queries a missing column.

### #5 — CRLF line endings break shell scripts on Linux
On Windows, git can convert LF → CRLF on checkout. Bash on the staging VM (Linux)
chokes on `\r` in shebangs and outputs cryptic errors like `bash\r: command not
found`. Either:
- Add `* text=auto eol=lf` to `.gitattributes` for shell scripts
- Or normalize on every deploy (`sed -i 's/\r$//' deploy/*.sh`)

### #6 — Sovereign provider fallback burns credits
If `ATLAS_SOVEREIGN_PROVIDER` is unset, code may default to Anthropic. Combined
with Honcho's `DERIVER_ENABLED=true` (which calls Anthropic Haiku on every turn),
this is how we burned through Anthropic credit. Default is OpenRouter; keep it
explicit.

### #7 — `gcloud` auth is split between PowerShell and WSL bash
On Windows, `gcloud auth login` from PowerShell stores credentials in
`%APPDATA%\gcloud`. WSL bash has its own `~/.config/gcloud`. Authenticating in
one doesn't carry over. Two options:
- Authenticate in WSL too: `bash -c "gcloud auth login --no-launch-browser"`
- Or set `CLOUDSDK_CONFIG=/mnt/c/Users/.../AppData/Roaming/gcloud` in WSL

### #8 — Service-account keys can be revoked server-side
The deployer SA key on disk doesn't change, but the cloud provider can revoke or
rotate the underlying credential server-side. You'll get `Invalid JWT Signature`.
The deploy scripts have a user-auth fallback — if the SA key fails, your gcloud
user account is used instead.

### #9 — Channel authorization is database-backed
Old: `TELEGRAM_ALLOWED_USERS` env var listed permitted handles. New: rows in
`people_channel_authorizations`. Consequences:
- After a fresh staging deploy with snapshot data, no one is authorized. Seed via
  SQL until the admin UI ships.
- The migration that auto-seeds users from the env var is a no-op if the env var
  isn't present (which is the case on staging).

### #10 — Soul not loaded on the gateway path (open)
Soul edits in `hermes/souls/atlas.md` only affect the agent's voice on the
**dashboard** path. The Hermes gateway (Telegram, Discord, email) does NOT load
the soul yet. Until that ships, voice changes only take effect via dashboard.
Telegram will sound noticeably different.

### #11 — Honcho deriver shows "unhealthy" badge if you re-enable it carelessly
The `honcho-deriver` container is currently a process-only worker (no HTTP). It's
healthy when the process is alive. Don't add an HTTP healthcheck. Currently the
healthcheck is overridden to `NONE`.

### #12 — Server host port: 3100 vs 3101
`docker-compose.yml` maps `${ATLAS_HOST_PORT:-3100}:3100`. Default is 3100 for
staging/prod. Local devs override to 3101 in their `.env` because they
also run `pnpm dev:server` on the host's 3100 port. The deploy script and the
firewall both assume the staging public URL is `:3100`. Don't change the staging
port without updating both.

---

## 7. Setup checklists

### Fresh local dev setup
1. Clone the project repo.
2. Clone Honcho INTO the repo: `git clone https://github.com/plastic-labs/honcho.git`
3. Copy `.env.example` → `.env`, fill in:
   - `OPENROUTER_API_KEY` (or `ANTHROPIC_API_KEY` if `ATLAS_SOVEREIGN_PROVIDER=anthropic`)
   - `GEMINI_API_KEY` (for Honcho embeddings)
   - `TELEGRAM_BOT_TOKEN` (your personal dev bot — never staging or prod)
   - `BETTER_AUTH_SECRET` (random string)
   - `ATLAS_HOST_PORT=3101` (so docker doesn't collide with `pnpm dev:server`)
4. `pnpm install`
5. `docker compose up -d` (starts db, honcho-db, honcho-redis, honcho)
6. `pnpm dev:server` — Express on :3100
7. `pnpm dev:ui` — Vite on :5173

### Fresh staging deploy
1. SSH check `.env` keys (use a wrapper that reports presence/absence, not values).
2. Verify present: `TELEGRAM_BOT_TOKEN` (staging-only bot), `OPENROUTER_API_KEY`,
   `GEMINI_API_KEY`, `DATABASE_URL`, `ATLAS_PUBLIC_URL`,
   `ATLAS_MIGRATION_AUTO_APPLY=true`, `ATLAS_SOVEREIGN_PROVIDER=openrouter`.
3. `bash ./deploy/deploy-staging.sh main`
4. Wait ~5-7 min for build + health check.
5. Seed channel authorizations via SQL (admin UI not built yet):
   ```sql
   SELECT id, name, telegram_user_id FROM people;
   INSERT INTO people_channel_authorizations
     (people_id, channel, channel_id, active)
   VALUES
     ('<user-1-people-id>', 'telegram', '<numeric-tg-id>', true),
     ('<user-2-people-id>', 'telegram', '<numeric-tg-id>', true);
   ```
6. Smoke test: dashboard login, assign issue to the agent, message Telegram bot.

### Fresh prod deploy
Same as staging but:
- Use the prod VM and DNS.
- DB is managed (Cloud SQL or equivalent), not in-VM Postgres.
- Use a real `BETTER_AUTH_SECRET`.
- Use the prod Telegram bot token.

---

## 8. Things that don't exist yet (so you don't think they're broken)

- **Institutional memory tools** (`decision_record`, `fact_search`). The agent
  can't write or recall company-level decisions yet.
- **Admin UI for channel auth** — granting/revoking is SQL-only today.
- **Soul on the gateway path** — Telegram/Discord/email replies aren't
  voice-aligned yet.
- **Email and Discord channels** — Telegram is the only working channel today.

---

*Last updated: 2026-04-27. Contributions: edit the file. If something here is
wrong, fix it; if you found a new pitfall, add it to §6.*
