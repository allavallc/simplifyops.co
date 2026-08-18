## Working Rules (read first)

1. **James is off-limits.** Never call `POST /messages`, message the Telegram bot, or simulate a user message via any API or script. All interaction with James goes through Anthony. Injected messages burn session limits, corrupt task context, and confuse Anthony mid-task. Not permitted for testing without explicit instruction.
2. **Stories first.** All implementation work needs a numbered story in `product/stories/story-N-<title>.md` before coding. Write the story, present the plan, wait for approval. Numbers are permanent — never reuse. **Lifecycle:** story → plan → approval → implement → **write tests → tests pass** → **`brooks-review` the diff → resolve findings** → **then** commit & push. The brooks-review gate runs *after tests pass and before committing/pushing* (see rule 9); a story is not *done* until it has passed that gate.
2a. **DO NOT BUILD SERVER-SIDE HTML.** The admin is **API-first**: a Vite+React+TS client-side SPA (`admin-client/`, served static at `/app`) consuming typed JSON `/api/admin/*` endpoints. **Never** add server-rendered pages/Jinja templates for admin UI. New admin surfaces = a JSON API endpoint + a React view in the SPA. The old `/admin` Jinja pages are legacy being retired — do not extend them. (Anthony, emphatic, 2026-08-13/14.)
2b. **The design guide in `design/` is the master for ALL UI. No deviation, ever.** Every UI change — layout, color, type, spacing, component, copy tone — must conform to `design/` (start at `design/style-guide.md`). You may not improvise, "improve," or reinterpret the design; matching the guide is not optional and there are **no exceptions**. **If anything is unspecified, ambiguous, or appears to conflict — ASK Anthony. Never assume, never fill the gap yourself.** When the guide and the code disagree, the guide wins and you flag it. (Anthony, 2026-08-15.)
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
9. **Code review: brooks-lint (all agents).** This repo ships the **brooks-lint** Agent Skills
   at `.agents/skills/` (vendor-neutral; MIT). They are **provider-agnostic** — any agent that
   loads Agent Skills (Codex/James, Claude Code, Cursor, Gemini, etc.) discovers them from that
   folder via each skill's `description`. **Mandatory review gate (part of rule 2's lifecycle):**
   every story runs **`brooks-review` on its diff *after* its tests pass and *before* you commit
   or push.** An unresolved 🔴 **Critical** finding **blocks the commit/push** — fix it or record
   an explicit justification in the story's Review section; 🟡/🟢 are fixed or justified there too.
   The review is static (reads code + test files; it does not run tests), which is why tests are
   written and green first — so the gate reviews stable code as the last step before pushing.
   Also available (not per-diff) for architecture/tech-debt/test audits. Six modes: `brooks-review` (PR/diff review),
   `brooks-audit` (architecture), `brooks-debt` (tech debt), `brooks-test` (test quality),
   `brooks-health` (composite score), `brooks-sweep` (full sweep + fixes). Invoke by asking
   naturally ("review this diff", "audit the architecture", "where's our worst tech debt?") or,
   where your agent supports slash/`$` commands, `/brooks-review` etc. Optional project config:
   `.brooks-lint.yaml` at repo root (see `.agents/skills/_shared/common.md`). Do **not** treat
   these findings as auto-authoritative — they advise; you still follow stories-first and ask
   before acting.

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

Each story must include a **## Review** section, filled in before commit/push, recording the
`brooks-review` run on the story's diff: the Health Score and each 🔴 Critical finding with how
it was resolved (fixed) or justified (why it's acceptable). Per rule 2's lifecycle the gate runs
**after tests pass and before committing/pushing**; an unresolved Critical blocks the push.
