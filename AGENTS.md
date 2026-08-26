## Working Rules (read first)

1. **James is off-limits.** Never call `POST /messages`, message the Telegram bot, or simulate a user message via any API or script. All interaction with James goes through Anthony. Injected messages burn session limits, corrupt task context, and confuse Anthony mid-task. Not permitted for testing without explicit instruction.
2. **Stories first.** All implementation work needs a numbered story in `product/stories/story-N-<title>.md` before coding. Write the story, present the plan, wait for approval. Numbers are permanent — never reuse. **Lifecycle:** story → plan → approval → **branch (rule 10)** → **code → write logging → write tests → commit (WIP)** → **rebase onto `origin/main`** → **`brooks-review` + `brooks-audit` → fix, re-run until clean** → **focused `ruff` + `pytest`** → **full `ruff` + `pytest`** → **amend → push → merge to `main` → archive story → delete work branch** (rule 10). You commit first so you can rebase; the **gate runs once, on the rebased (integrated) result** — so "green" means green on top of the latest `main`, never stale (see rule 9). A story is not *done* until the gate is clean on the rebased branch, both `ruff`/`pytest` passes are green, and it's been merged + archived.
2a. **Admin UI is server-rendered HTML (Jinja) — no React, no SPA, no build step.** Admin pages are Jinja templates in `admin_api/templates/`, rendered by FastAPI at `/admin`, reading data from the `/api/*` JSON layer. **Never** add a client-side JS framework (React/Vue/Svelte), an SPA, or an npm/Vite build step for admin UI. New admin surfaces = a JSON API endpoint (if needed) + a Jinja page. The React SPA (`admin-client/`) is **legacy being retired** (`product/stories/story-25-retire-react-consolidate-jinja.md`) — do not extend it. (Owner decision, 2026-08-22 — **reverses** the prior 2026-08-13/14 React-SPA/"never Jinja" direction.)
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
   every story runs **`brooks-review` (diff) *and* `brooks-audit` (architecture) on the *rebased*
   work branch** — i.e. after you commit your work (WIP) and `git rebase origin/main`, and before
   push/merge — so the gate validates the **integrated** result, never stale code. Run the brooks
   reviews first (they're **static** — they read code + test files, they don't run tests) and
   **iterate: fix findings and re-run until clean**, *then* run focused + full `ruff`/`pytest`. An
   unresolved 🔴 **Critical** from either brooks mode blocks push/merge — fix it or record an
   explicit justification in the story's Review section; 🟡/🟢 are fixed or justified there too.
   **Testing-phase progress readout.** Once you enter the testing phase, print this standard
   status line and reprint it every time you advance a stage, marking the current position with
   `(**HERE**)` — so Anthony can see exactly where the run is at a glance:
   > `brooks audit > fixing findings > focused ruff > focused pytest > full ruff > full pytest > done`
   e.g. `brooks audit > fixing findings > focused ruff > focused pytest (**HERE**) > full ruff > full pytest > done`.
   `brooks-debt`/`brooks-test`/`brooks-health` remain opt-in. Six modes: `brooks-review` (PR/diff review),
   `brooks-audit` (architecture), `brooks-debt` (tech debt), `brooks-test` (test quality),
   `brooks-health` (composite score), `brooks-sweep` (full sweep + fixes). Invoke by asking
   naturally ("review this diff", "audit the architecture", "where's our worst tech debt?") or,
   where your agent supports slash/`$` commands, `/brooks-review` etc. Optional project config:
   `.brooks-lint.yaml` at repo root (see `.agents/skills/_shared/common.md`). Do **not** treat
   these findings as auto-authoritative — they advise; you still follow stories-first and ask
   before acting.
10. **Work branches — all story/feature work (never on `main`).** `main` is **production**
    (GitHub Pages auto-deploys on push; there is **no staging**), so never commit feature/story
    work directly to it. Every story/feature is built on a **work branch off `main`**, named to
    match its story: **`story-N-<slug>`** (same slug as the story file). To finish a story:
    1. **commit** your work on the branch (WIP — you'll amend after the gate);
    2. **rebase onto latest `main` — never skip this:** `git fetch origin` then
       `git rebase origin/main`, so your branch sits on top of whatever landed meanwhile and the
       merge **can't reverse** someone else's work; resolve any conflicts;
    3. **run the gate on the rebased result** (rules 2 & 9): `brooks-review` + `brooks-audit` until
       clean, then focused + full `ruff`/`pytest`; fix findings and **amend**. Running the gate
       *here — after the rebase* — is the point: it validates the integrated code, so "green"
       can't be stale. An unresolved 🔴 Critical blocks the rest.
    4. **push** the branch, then **merge it to `main`** (an agent does the merge — no external PR
       review required; use `git merge --no-ff` so the story branch stays traceable) and push `main`;
    5. **archive the story:** `git mv product/stories/story-N-<slug>.md product/stories/archive/`
       and commit — so `product/stories/` lists only active work;
    6. **clean up the work branch:** delete it locally (`git branch -d story-N-<slug>`) and on the
       remote (`git push origin :story-N-<slug>`).
    Non-feature housekeeping (docs, this archive move, `agent-coordination.md` entries) may go
    straight to `main`. Coordinate on shared infra per rule 8 before branching work that touches it.
11. **Dev process + architectural rules — read before implementing.** The full LLM dev process for
    this repo — **build → test → log → fix → commit → push to staging** — lives in
    **`product/product-dev-guidelines.md`**. The binding **architectural rules** (API-first;
    server-rendered Jinja, not React; no god-modules; one-way dependencies; single source of truth
    for settings; repo-owned/declared dependencies; test seams; local → staging → prod) live in
    **`ops/current-architecture.md` → "Architectural rules"**. Both are enforced alongside the
    lifecycle in rules 2/9/10 — a change that breaks an architectural rule needs an explicit
    decision recorded in a story (rule 3).

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

_(The legacy `people-whitelist.service` Node app was removed — governance is owned by `admin_api/`.)_

### Message flow
Telegram → `gateway/gateway.py` adapter → `POST /messages` (FastAPI) → governance (`person_identities`→`people`) → `work_items(ready)` → DurableWorkflowWorker (concurrency=1) → session-cap check/rotate → `POST /api/sessions/{id}/chat` (Hermes API, system_message + tool_context token) → `reply_ready` → Telegram send → `completed`. Failures retry ≤3 → `failed_needs_review` + Telegram alert.

### Key locations
- FastAPI control plane: `admin_api/`
- Durable worker + Telegram adapter: `gateway/gateway.py`
- Hermes config (env-owned, gitignored): `/home/pi/.hermes/profiles/simplifyops/config.yaml`
- Secrets: `/home/pi/.config/relay.env`, `/home/pi/.config/simplifyops-runtime.env`
- Canonical architecture: `ops/current-architecture.md`
- DB: `whitelist_app` (unix socket `/var/run/postgresql`)

### Settings page (`/admin/settings`)
Working backends: Health, Provider+Model (writes config.yaml → restarts runtime → clears sessions), Session Health (cap). Other sections UI-only.

### Google Workspace MCP status
config.yaml wires 4 `@dguido/google-workspace-mcp` servers. Package self-manages OAuth in `~/.hermes/profiles/simplifyops/home/.config/google-workspace-mcp/`. `credentials.json` exists, `tokens.json` **missing** → never authorized → Google tools not yet functional. Do not act on this without guidance (see rule 5).

---

## Stack Setup Guide

For a full explanation of how the James stack works (Hermes, Hindsight, the Telegram gateway, profiles, secrets, and service startup order), read:

**`ops/james-stack-setup.md`**

Start there before making any changes to this system.

---

## Hermes Gateway — Known Issues & Fixes

### codex_runtime.py — SDK TypeError on get_final_response() (2026-05-26)

> **RESOLVED upstream as of Hermes v0.20.5 (2026-08-25).** After the 0.19→0.20.5 upgrade the runtime
> boots clean **without** the patch below — the bug is fixed upstream. The fresh 0.20.5
> `codex_runtime.py` is unpatched and `simplifyops-agent-runtime` runs with NRestarts=0. Keep the
> note below as history; only re-derive a fix if the crash-loop returns on a future version.

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

Each story must include a **## Review** section, filled in before commit/push, recording **both**
the `brooks-review` (diff) and `brooks-audit` (architecture) runs: each one's Health Score and
each 🔴 Critical finding with how it was resolved (fixed) or justified (why it's acceptable), plus
confirmation that focused **and** full `ruff` + `pytest` came back green. Per rule 2's lifecycle
the brooks gate runs **once code/logging/tests are written — before ruff/pytest and before
commit/push — and is re-run until clean**; an unresolved Critical from either blocks the push.
