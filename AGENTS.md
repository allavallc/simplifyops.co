## Working Rules (read first)

1. **James is off-limits.** Never call `POST /messages`, message the Telegram bot, or simulate a user message via any API or script. All interaction with James goes through Anthony. Injected messages burn session limits, corrupt task context, and confuse Anthony mid-task. Not permitted for testing without explicit instruction.
2. **Stories first.** All implementation work needs a numbered story in `product/stories/story-N-<title>.md` before coding. Write the story, present the plan, wait for approval. Numbers are permanent — never reuse.
3. **No architecture choices without asking.** Implementation approach, service boundaries, data model, technology selection — if there's more than one reasonable way, stop and ask. "Simplest path" is not a reason.
4. **No short-term fixes.** No workarounds "just to get something working." Do it right or say what the right approach requires and hold.
5. **MCP requires guidance.** Do not build/configure/authorize/modify MCP servers without explicit direction from Anthony (who consults the other LLM). High mistake potential. The third-party `@dguido/google-workspace-mcp` self-manages OAuth and bypasses app governance — that conflicts with the repo-owned MCP model.
6. **Read the graph first.** `graphify update .` then read `graphify-out/GRAPH_REPORT.md` (or use `graphify query/path/explain`) before coding or answering codebase questions.
7. **Explain before acting.** Say what you'll do before doing it.
8. **Coordination doc.** Multiple agents (e.g. C1, C2) share this box. Read `agent-coordination.md` (repo root, untracked) at session start and **before touching shared infra** (systemd services, `config.yaml`, the Telegram bot/token, the DB), and check it regularly. **Log what you do there.** When Anthony says "the coordination doc" he means `agent-coordination.md`. Append entries at the bottom, wrapped in `----`, first line `<name> | <ISO timestamp> | <story-N or ->`:
   ```
   ----
   C2 | 2026-08-13T00:50:40-04:00 | story-18
   <message>
   ----
   ```

---

## Current System State (2026-08-11)

James (Hermes agent) is **functional** — `gpt-5.5` via `openai-codex`, profile `simplifyops`.

### Services (systemd, all active)
| Service | Purpose | Port |
|---|---|---|
| `simplifyops-admin.service` | FastAPI control plane: `POST /messages`, admin UI, governance, audit, settings | 3000 |
| `simplifyops-gateway.service` | Telegram adapter + DurableWorkflowWorker | 3001 internal |
| `simplifyops-agent-runtime.service` | Hermes gateway run + API server | 8642 |
| `hindsight.service` | Memory | 8888 |
| `people-whitelist.service` | Node.js — **DISABLED**, replaced by `admin_api/` | — |

### Message flow
Telegram → `gateway/gateway.py` adapter → `POST /messages` (FastAPI) → governance (`person_identities`→`people`) → `work_items(ready)` → DurableWorkflowWorker (concurrency=1) → session-cap check/rotate → `POST /api/sessions/{id}/chat` (Hermes API, system_message + tool_context token) → `reply_ready` → Telegram send → `completed`. Failures retry ≤3 → `failed_needs_review` + Telegram alert.

### Key locations
- FastAPI control plane: `admin_api/`
- Durable worker + Telegram adapter: `gateway/gateway.py`
- Hermes config (env-owned, gitignored): `/home/pi/.hermes/profiles/simplifyops/config.yaml`
- Secrets: `/home/pi/.config/relay.env`, `/home/pi/.config/simplifyops-runtime.env`
- Canonical architecture: `plan/current-architecture.md`
- DB: `whitelist_app` (unix socket `/var/run/postgresql`)

### Settings page (`/admin/settings`)
Working backends: Health, Provider+Model (writes config.yaml → restarts runtime → clears sessions), Session Health (cap). Other sections UI-only.

### Google Workspace MCP status
config.yaml wires 4 `@dguido/google-workspace-mcp` servers. Package self-manages OAuth in `~/.hermes/profiles/simplifyops/home/.config/google-workspace-mcp/`. `credentials.json` exists, `tokens.json` **missing** → never authorized → Google tools not yet functional. Do not act on this without guidance (see rule 5).

---

## Stack Setup Guide

For a full explanation of how the James stack works (Hermes, Hindsight, the Telegram gateway, profiles, secrets, and service startup order), read:

**`plan/james-stack-setup.md`**

Start there before making any changes to this system.

---

## Hermes Gateway — Known Issues & Fixes

### codex_runtime.py — SDK TypeError on get_final_response() (2026-05-26)

**Symptom:** `hermes-gateway.service` crashes in a restart loop. Journal shows:
```
error_type=TypeError ... summary='NoneType' object is not iterable
provider=openai-codex  model=gpt-5.3-codex
```

**Cause:** The OpenAI SDK's `stream.get_final_response()` returns `output=None` instead of `output=[]` when the Codex backend streams items via events. The existing backfill patch only guarded against an empty list, so `None` fell through and caused the TypeError downstream.

**Fix:** Edit `/home/pi/.hermes/hermes-agent/agent/codex_runtime.py`:

1. In `run_codex_stream()` — wrap `get_final_response()` in a `try/except TypeError` so a `None` final_response is caught, then widen the backfill condition from `isinstance(_out, list) and not _out` to `not _out` (covers both `None` and `[]`). If `final_response` is `None`, synthesize a `SimpleNamespace` from `collected_output_items` or `_codex_streamed_text_parts`.

2. Same widened condition (`not _out`) in `run_codex_create_stream_fallback()`.

**Warning:** `hermes update` overwrites `codex_runtime.py` and regenerates the service file. After any Hermes update you must:
- Re-apply the patch above
- Re-add `EnvironmentFile=/home/pi/.config/relay.env` to `/etc/systemd/system/hermes-gateway.service` (hermes strips it on reinstall)
- Run `sudo systemctl daemon-reload && sudo systemctl restart hermes-gateway.service`

---

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

---

## Product stories

All work needs a story in `product/stories/` before implementation starts.

Each story file and title must include a number, like `story 1 - <title>`.
