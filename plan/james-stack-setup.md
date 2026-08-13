# James Stack — Setup Guide for LLMs

This document describes the full operational stack that runs James Bott, the AI agent for SimplifyOps.co. Use this to replicate, debug, or rebuild the setup from scratch.

---

## What Is James?

James Bott is an AI agent persona running on a Raspberry Pi 5. He is the operational brain of SimplifyOps.co — a consulting practice. His identity, voice, and rules are defined in a "soul" file. He is reachable via Telegram DM.

The underlying agent runtime is **Hermes** (hermes-agent). James is not a custom application — he is a named *profile* inside Hermes, with a specific model, memory config, and soul attached.

---

## Component Overview

| Component | What it does | Where it lives |
|---|---|---|
| Hermes | Agent runtime (runs James) | `/home/pi/.local/bin/hermes` |
| `simplifyops` profile | James's config, memory, soul | `/home/pi/.hermes/profiles/simplifyops/` |
| Soul file | James's identity/persona | `/home/pi/simplifyops/souls/james-bott.md` |
| Hindsight | Long-term memory API | `http://localhost:8888` (systemd service) |
| PostgreSQL | Hindsight's database backend | local, DB = `hindsight`, user = `pi` |
| gateway.py | Telegram → Hermes bridge | `/home/pi/simplifyops/gateway/gateway.py` |
| james-gateway.service | Runs the gateway as a daemon | `/etc/systemd/system/james-gateway.service` |
| hindsight.service | Runs the Hindsight API | `/etc/systemd/system/hindsight.service` |
| relay.env | All secrets (tokens, API keys) | `/home/pi/.config/relay.env` (chmod 600) |

---

## Hermes and Profiles

Hermes is a general-purpose agent framework. It supports multiple profiles — each profile is an isolated identity with its own model, memory config, soul, and session history.

**Profile root:** `/home/pi/.hermes/profiles/simplifyops/`

Key files inside the profile:

```
config.yaml         — model, memory provider, approvals, compression, logging
SOUL.md             — symlink → /home/pi/simplifyops/souls/james-bott.md
hindsight/
  config.json       — tells Hermes how to reach the Hindsight API
sessions/           — conversation history
memories/           — Hermes's built-in short-term memory notes
```

**`config.yaml` — key settings:**
- `model.default: gpt-5.4-mini` / `provider: openai-codex` — the LLM James uses
- `memory.provider: hindsight` — routes all memory calls to the Hindsight API
- `approvals.mode: auto` — James does not ask for tool approval

**`hindsight/config.json`:**
```json
{
  "mode": "local_external",
  "bank_id": "simplifyops",
  "budget": "mid",
  "api_url": "http://localhost:8888"
}
```
This tells Hermes's Hindsight plugin to POST to the local Hindsight API server rather than a cloud service.

**Soul symlink:**
```
/home/pi/.hermes/profiles/simplifyops/SOUL.md
  → /home/pi/simplifyops/souls/james-bott.md
```
The soul lives in the `simplifyops` repo (version-controlled). The symlink keeps the profile in sync with the repo. **Never edit the copy inside `.hermes/` directly — always edit the source in `souls/james-bott.md`.**

**Running Hermes one-shot (how the gateway calls it):**
```bash
/home/pi/.local/bin/hermes -p simplifyops -z "your message here"
```
- `-p simplifyops` — use the simplifyops profile
- `-z "message"` — pass a one-shot prompt (non-interactive)

---

## Hindsight (Memory)

Hindsight is a separate API server that gives Hermes long-term, cross-session memory. It stores facts about people and conversations, supports semantic search via embeddings, and exposes an HTTP API.

**Service:** `hindsight.service`
**Binary:** `/home/pi/.local/bin/hindsight-api`
**Bind:** `127.0.0.1:8888` (loopback only — not exposed to the network)
**Database:** PostgreSQL 17 with pgvector extension, database `hindsight`, user `pi`

**Config:** `/home/pi/.config/hindsight.env`

```
HINDSIGHT_API_HOST=127.0.0.1
HINDSIGHT_API_PORT=8888
HINDSIGHT_API_DATABASE_URL=postgresql://pi:hindsight@localhost:5432/hindsight
HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
HINDSIGHT_API_EMBEDDINGS_API_KEY=<openrouter key>
HINDSIGHT_API_EMBEDDINGS_BASE_URL=https://openrouter.ai/api/v1
HINDSIGHT_API_EMBEDDINGS_MODEL=text-embedding-3-small
HINDSIGHT_API_RERANKER_PROVIDER=rrf
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_API_KEY=dummy
HINDSIGHT_API_LLM_BASE_URL=https://openrouter.ai/api/v1
HINDSIGHT_API_LLM_MODEL=openai/gpt-4o-mini
```

**Important notes on config:**
- `RERANKER_PROVIDER=rrf` — RRF (Reciprocal Rank Fusion) is a purely algorithmic reranker, no model or network call needed. This is the "no neural reranker" setting. Do NOT set it to `none` — that value was removed in newer versions of hindsight-api and causes a crash.
- `LLM_API_KEY=dummy` — Hermes uses its own codex model; Hindsight's LLM key is unused in this setup.
- Embeddings are called via OpenRouter (real API key required).

**Health check:**
```bash
curl -s http://127.0.0.1:8888/health
```

---

## The Telegram Gateway

The gateway is a Python script that connects Telegram to Hermes. It runs as a systemd service.

**File:** `/home/pi/simplifyops/gateway/gateway.py`
**Service:** `james-gateway.service`

**Flow:**
1. Polls Telegram for new messages (long-polling, 30s timeout)
2. Checks the sender's Telegram user ID against a whitelist
3. If approved: calls Hermes via subprocess and sends the reply back
4. If not approved: queues the message in the inbox for admin review and sends no reply to the sender

**Whitelist:** `/home/pi/simplifyops/gateway/whitelist/whitelist.md`
One Telegram user ID per line. Lines starting with `#` are ignored. The whitelist is reloaded on every poll loop — no restart needed to add/remove users.

**How the gateway calls Hermes:**
```python
cmd = ["/home/pi/.local/bin/hermes", "-p", "simplifyops", "-z", text]
```
Timeout: 300 seconds. ANSI escape codes are stripped from output before sending to Telegram.

**Service file** (`/etc/systemd/system/james-gateway.service`):
```ini
[Unit]
Description=James (Hermes) Telegram Gateway
After=network-online.target hindsight.service
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/simplifyops/gateway
EnvironmentFile=/home/pi/.config/relay.env
ExecStart=/usr/bin/python3 /home/pi/simplifyops/gateway/gateway.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

The `EnvironmentFile` injects secrets (Telegram bot token, API keys) into the process environment at launch. The gateway reads `TELEGRAM_BOT_TOKEN` from the environment.

---

## Secrets

All secrets live in `/home/pi/.config/relay.env` (chmod 600, never committed to git).

Relevant keys for this stack:
- `TELEGRAM_BOT_TOKEN` — the Telegram bot token for James's bot
- `OPENROUTER_API_KEY` — used by Hindsight for embeddings

The Hermes codex model authenticates via OAuth (`hermes auth openai-codex`), not via an API key in the env file.

---

## Startup Order

Services must start in this order:
1. `postgresql.service` (system — auto)
2. `hindsight.service` (depends on postgres)
3. `james-gateway.service` (depends on hindsight)

All three are enabled and start on boot. Check status:
```bash
systemctl status hindsight.service
systemctl status james-gateway.service
```

---

## Verifying the Stack Is Healthy

```bash
# 1. Hindsight API is up
curl -s http://127.0.0.1:8888/health

# 2. Hermes can call James one-shot
/home/pi/.local/bin/hermes -p simplifyops -z "say hello"

# 3. Gateway service is running
systemctl status james-gateway.service

# 4. Check gateway logs
journalctl -u james-gateway.service -n 30 --no-pager
```

---

## Key Paths Summary

```
/home/pi/.local/bin/hermes                          — Hermes binary
/home/pi/.hermes/profiles/simplifyops/              — James's profile root
/home/pi/.hermes/profiles/simplifyops/config.yaml   — model, memory, agent config
/home/pi/.hermes/profiles/simplifyops/SOUL.md       — symlink to soul file
/home/pi/.hermes/profiles/simplifyops/hindsight/config.json — Hindsight plugin config
/home/pi/simplifyops/souls/james-bott.md            — soul source of truth (edit here)
/home/pi/simplifyops/gateway/gateway.py             — Telegram gateway script
/home/pi/simplifyops/gateway/whitelist/whitelist.md — allowed Telegram user IDs
/home/pi/.config/relay.env                          — all secrets (600 perms)
/home/pi/.config/hindsight.env                      — Hindsight API config (600 perms)
/etc/systemd/system/james-gateway.service           — gateway service unit
/etc/systemd/system/hindsight.service               — Hindsight service unit
```
