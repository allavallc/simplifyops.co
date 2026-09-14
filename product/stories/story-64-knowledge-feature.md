# Story 64 - Knowledge feature (curated docs + self-knowledge + governed retrieval)

## Status
**Phases A + B + C1 + C2 done + deployed — story complete.** 🧱 large / multi-phase. Implements
`plan-architecture/feature-details-if-needed/agents-knowledge-rebuild.md` (the owner's spec), adapted
to this repo. Supersedes parked [[story-46]] (this is 46 done *with* a real consumer).

## Goal
Give James a governed knowledge base: human-curated Markdown under `knowledge/`, seeded into
`whitelist_app`, editable by super-admins, and readable by the runtime through **governed,
authority-filtered** list/read/search tools — plus a deterministic, authority-filtered self-knowledge
doc generated from allowlisted sources. Baseline agent access is **read-only**.

## Maps onto what we already have
| Spec need | Our reuse |
|---|---|
| App DB, separate from memory | `whitelist_app` (not `hindsight`) ✓ |
| Schema + idempotent init | `migrations/` + `schema_init` (story 47) — new `0002_knowledge.sql` |
| Mutation audit | `audit.log_audit` |
| Admin auth + authority ladder (`contact<member<admin<super_admin`) | `deps.require_admin`, `people` authority; add one `authority_meets(req, min)` helper |
| Admin UI = server-rendered | Jinja (protected rule 2) — `/admin/knowledge` (super-admin only) |
| Governed tool identity | `tool_contexts` (mint `gateway/tool_context.py`, resolve `GET /api/tool-contexts/{token}`) ✓ |
| Generator (stdlib, deterministic) | new `scripts/build_agent_self_knowledge.py` |
| Runtime handoff | `gateway/hermes_client.py` `system_message` (injection point) |

## Proposed phases (each shippable; gated + merged on its own)
**Phase A — curated store + super-admin lifecycle (no runtime/MCP):**
`knowledge/` tree + front-matter contract (`minimum_authority`, `status`); `admin_api/knowledge_store.py`
(parse/validate/render/path/category helpers + store methods + `seed_from_repo_if_empty` + versions);
`0002_knowledge.sql` (`knowledge_documents`, `knowledge_document_versions`); Jinja `/admin/knowledge`
(list/filter/create/edit/archive/reactivate/download, generated docs read-only); tests.

**Phase B — self-knowledge generator:** `scripts/build_agent_self_knowledge.py generate|check` +
`knowledge/about-myself/sources.md`; deterministic, allowlisted sources, denylist for secret-bearing
paths, secret scan, authority-tagged output; tests (determinism, drift, missing heading, blocked paths).

**Phase C — runtime consumption (the consumer that makes it real):**
1. **Governed retrieval tools** `list/read/search_knowledge_docs` — our **first repo-owned MCP
   connector** (`connectors/`, FastMCP), resolving the tool-context token, authority-filtering server-side
   (this is also the seed of [[story-55]]).
2. **Runtime context**: inject the generated self-knowledge (+ a capability summary) into the handoff —
   **admin/super_admin get setup context, others get the public capability summary**; missing/unsafe
   generated file omitted (never fall back to raw sources).

## Baseline vs gaps (per spec §9 — keep visible; do NOT build as baseline)
- **No GitHub file sync / write-back** — admin saves write DB records only (`source_path` is a logical
  id, not proof of a file). GitHub adapters are out of scope.
- **No agent write/mutation tools** — retrieval is read-only list/read/search only.
- **No background learning/import worker** — no schedule/notify/retry (that's automations, held).
- **Concurrency**: uniqueness-protected identity; no optimistic-edit token (report the limit, don't
  claim safe parallel writes).
- **Generated refresh is split** — regenerated file isn't auto-reimported into an existing DB.

## Key decisions for approval
- **D1 — phasing:** build **A → B → C** as three separate gated stories/increments (my rec), or one
  mega-merge? (A+B are self-contained; C is the runtime/MCP integration.)
- **D2 — retrieval mechanism (Phase C1):** a repo-owned **FastMCP connector** (spec-faithful; first
  `connectors/`; needs registering in `config.yaml` `mcp_servers` + the deferred-tools bridge) — vs a
  simpler interim (inject a knowledge **index** into the runtime `system_message` so James can ask via a
  lighter path) with the full MCP connector later. (Rec: FastMCP connector, since the spec's governance
  model depends on it — but it's the biggest new piece, so worth confirming.)
- **D3 — self-knowledge injection (Phase C2):** inject via `hermes_client.system_message`
  (minimal, uses today's handoff) — confirm that's acceptable vs a larger message-context builder.
- **D4 — seed content:** I scaffold the folder map + READMEs + a few example docs at
  `minimum_authority: admin`, but **I won't invent SimplifyOps business content** — you provide the real
  curated knowledge, or we seed minimal placeholders. Confirm.

## Acceptance
Per spec §10 matrix, adapted: folder/metadata validation; create/edit/archive/reactivate/download
round-trips in real Postgres; authority matrix (UI super-admin-only; tool contact/member/admin/
super_admin visibility); retrieval (case-insensitive line search, no restricted leakage, missing==invisible);
seeding (empty-store only; edits survive reads); generator determinism + drift; runtime authority split;
audit (no body/token in general logs). Full gate per phase.

## Review — Phase A (curated store + super-admin lifecycle)
Built: `knowledge/` tree (rich per-folder READMEs explaining each category + how it differs from
neighbors; owner-approved seed); `knowledge_store.py` (single validation+storage seam — front-matter
contract, path-traversal/secret rejection, authority ladder, slug/category/render helpers, store
methods, `seed_from_repo_if_empty`, content versions); `migrations/0002_knowledge.sql`
(`knowledge_documents` + `_versions`, uuid/checks/unique); `routes/admin_knowledge.py` (super-admin
list/filter/create/edit/archive/reactivate/download, 303 redirects, generated read-only) + Jinja page;
removed the `pages.py` stub route (no duplicate `/admin/knowledge`).
**Verified live** (whitelist_app): migration applies idempotently; seed imports exactly the 1 example
(READMEs/INDEX/sources skipped); full lifecycle create→edit(2 versions)→authority-filter→archive→
download roundtrip; test rows cleaned up. brooks-review/audit: single seam, pure/DB split (lazy `db`
for CI), one-way deps, server-side authz; secrets/traversal rejected; audited. 🟡 DB store-methods not
unit-tested (need live PG) — 9 pure-helper tests + live lifecycle verification (repo pattern). No 🔴.
**Gate:** rebased on `origin/main`; full ruff clean; pytest 51 green (9 new); app imports (86 routes).
**Phase A done.**

## Review — Phase B (self-knowledge generator)
Built: `scripts/build_agent_self_knowledge.py` (`generate`/`check`, stdlib only, deterministic, no LLM);
`knowledge/about-myself/sources.md` (allowlist: one Output, sources with Reason + explicit Sections);
`knowledge/about-myself/capabilities.md` (reviewed non-secret source); generated
`knowledge/about-myself/generated/self-knowledge.md` (admin-level, tracked, do-not-hand-edit);
`ops/agent-self-knowledge.md`; CI `check` step (drift-guards the committed output).
Behavior: a named section extracts heading→next-equal/higher-heading (missing/empty **fails**, no
whole-file fallback); source paths validated (no absolute/traversal; env/config/auth/session/audit/infra
denylist); extracts + final output secret-scanned. Verified: generate→check OK, second generate byte-
identical. brooks-review/audit: pure/deterministic, no god-module/coupling; secrets excluded at every
step; generated file not auto-imported (separate from the DB store). 11 unit tests (parse, section
extract/stop/missing/empty, denylist, secret-scan, determinism, committed-not-stale). No 🔴/🟡.
**Gate:** rebased; full ruff clean; pytest 62 green (11 new). **Phase B done.**

## Review — Phase C1 (self-knowledge injection into the runtime handoff)
Built: `gateway/self_knowledge.py` — `self_knowledge_context(authority)` reads the generated file and
returns the **full body for admin/super_admin**, the **public Summary for others**, and **None**
(omit) if the file is missing/unreadable/secret-like (never falls back to raw sources). Wired into
`hermes_client.call_hermes` — appended to `system_message` after the tool-context token. Verified live
(flat import): member → summary only; admin → full 2389-char body. brooks-review/audit: change confined
to the runtime boundary (protected rule 10); authority filtered server-side; pure module, no
coupling/god-module. 7 unit tests. No 🔴/🟡. **Gate:** rebased on `origin/main`; full ruff clean;
pytest 69 green (7 new). **C1 done.** Deploy: restart `simplifyops-gateway.service`.

**Remaining — C2 (governed retrieval connector):** `list/read/search_knowledge_docs` as the first
repo-owned FastMCP connector in `connectors/`, resolving the tool-context token + authority-filtering
server-side, registered in `config.yaml` `mcp_servers`. Planned separately (MCP + live-runtime).

## Plan — Phase C2 (governed retrieval connector)

**Decision (owner-approved): data path = direct DB via the shared service.** The connector imports
`admin_api/knowledge_store.py` and resolves the token against Postgres itself (env-owned DB access) —
matches the spec §6 boundary (`connector → shared service → DB`), no runtime→admin_api HTTP coupling.
Everything runs as user `pi` on one host, so the connector holding DB access is not a new exposure.

**Tools (spec §6, all read-only):**
- `list_knowledge_docs(tool_context, category=None)` → `{status:"ok", documents:[summary]}`
- `read_knowledge_doc(tool_context, slug)` → `{status:"ok", document: summary + content_md}`
- `search_knowledge_docs(tool_context, query, category=None, max_results=20)` → `{status:"ok", query, matches}`

**Governance — server-side, non-negotiable:**
- `tool_context` (opaque token) is the ONLY authority source; model-supplied authority is ignored.
- Resolve token → hash → `tool_contexts` row, check `expires_at > now()`; expired/unknown → error.
- Filter `status='active'` AND `authority_meets(requester, minimum_authority)` **before** list/read/search.
- Invisible or missing slug → the **same** not-found error (no existence/authority leak).
- Search: case-insensitive substring over body lines of visible docs only; `max_results` clamped 1–50
  (default 20); each match = `{slug, title, category, line (1-based), snippet}`; snippet is a shortened
  line (no restricted content). No embeddings/vector/FTS.
- Token never appears in logs, returns, or error strings. Preserve `request_id` in tool logs only.

**Shared-service additions (`admin_api/knowledge_store.py`) — routes + tools share one impl (§4):**
- `resolve_tool_context(token) -> dict | None` — hash + expiry check against `tool_contexts` (extracted
  so the connector and the existing `/api/tool-contexts/{token}` route share exactly one implementation).
- `get_visible_by_slug(slug, requester_authority) -> dict | None` — active + authority-filtered; None if
  invisible/missing (caller maps both to the same not-found).
- `search_visible(query, requester_authority, category=None, max_results=20) -> list[dict]` — substring
  over `content_md` lines of active + authority-visible docs; returns the match shape above.
- Reuse existing `_summary`, `authority_meets`, `list_docs(requester_authority=...)`, `AUTHORITIES`.

**Connector (`connectors/knowledge/mcp_server.py`):** FastMCP server (`mcp.server.fastmcp`, SDK
`>=1.9.0,<2.0.0`); launch pattern `connectors.knowledge.mcp_server`. Thin: parse/validate args →
`resolve_tool_context` → call the shared service → shape `{status:"ok", ...}`. Package `connectors/`
+ `connectors/knowledge/` with `__init__.py`. No business logic beyond arg-shaping + error envelopes.

**Runtime registration (`config.yaml` `mcp_servers`):** add a `knowledge` stdio server via
`runtime_config.set_mcp_server(...)` — `command: python3`, `args: [-m, connectors.knowledge.mcp_server]`,
`env: {PYTHONPATH: <repo>:<repo>/admin_api, GATEWAY_DB_DSN: <socket dsn>}`, `enabled: true`. Discovered
by Hermes' native MCP client as `mcp_knowledge_*`. Restart `simplifyops-agent-runtime.service` to load.

**Known limits (report, don't hide):** token TTL stays 30 min (existing `tool_context.py`), not the
spec's 2 h default — a system-wide setting, out of scope to change here. No write/mutation tools. No
timeout/retry/worker of its own (inherits runtime/DB budgets). Initial-seed race is a known gap.

**Tests (real Postgres, per §10):** token resolve (valid/expired/unknown); authority matrix for
list/read/search (contact→super_admin visibility); archived excluded; invisible slug == missing (same
error, no leak); search case-insensitivity + `max_results` clamp + no restricted snippets; `status:"ok"`
envelopes; token never in output. Connector tools tested against the real MCP SDK error envelope.

**Gate:** code → logging → tests → commit WIP → rebase on `origin/main` → brooks-review + brooks-audit
(fix until clean) → focused ruff+pytest → full ruff+pytest → push → merge → archive story.

**Open sub-question (non-blocking, will default if you don't weigh in):** the `mcp_servers` entry is
written to the env-owned live `config.yaml`, not committed. I'll add it via `set_mcp_server` at deploy
and document it in the story; the connector code + a `config.base.prod.yaml` comment are what's committed.

## Review — Phase C2 (governed retrieval connector)
Built: `connectors/knowledge/mcp_server.py` — first repo-owned FastMCP server exposing
`list_knowledge_docs` / `read_knowledge_doc` / `search_knowledge_docs`. Authority resolved server-side
from the opaque `tool_context` token (model-claimed authority ignored); archived + over-authority docs
filtered before list/read/search; missing == invisible slug (same not-found, no leak); token never
logged/returned; `status:"ok"` envelopes; errors raised for the SDK to wrap. Reaches the shared service
+ Postgres directly (`connector → shared service → DB`). Shared code: `admin_api/tool_context_store.py`
(single token resolver; the `/api/tool-contexts/{token}` route now delegates to it) and
`knowledge_store.py` gains pure `search_matches`/`clamp_max_results`/`_snippet` + thin
`get_visible_by_slug`/`search_visible` DB reads + one `_visible_authorities` window used by all three
readers (removed the duplicated slice from `list_docs`). `mcp>=1.9.0,<2.0.0` pinned in requirements-dev.

**Review:** brooks-review + brooks-audit run on the rebased branch. One 🟡 (authority-window slice
duplicated across `list_docs` + `_visible_authorities`) — **fixed** by routing `list_docs` through the
helper. One 🟢 accepted-by-design: the DB-layer authority SQL isn't unit-tested (no live-Postgres
harness in the repo; matches Phase A convention) — covered by the live-deploy verification below. One
🟢 recorded: shared services under `admin_api/` have outgrown the name; revisit (promote to `core/`)
when a second connector lands. No 🔴. **Gate:** rebased on `origin/main`; full ruff clean; pytest 83
green (14 new: pure search + monkeypatched connector governance).

**Deploy (done 2026-09-15):** registered the `knowledge` MCP server in the live `config.yaml` via
`runtime_config.set_mcp_server` (command `/usr/bin/python3`, args `[-m, connectors.knowledge.mcp_server]`,
env `PYTHONPATH=/home/pi/projects/simplifyops` + `GATEWAY_DB_DSN`) and restarted
`simplifyops-agent-runtime.service`. The runtime spawns the connector under its MCP stdio watchdog
(stable, no restart-loop, no errors) and discovers all three tools.

**Live verification (compensating control for the untested DB layer):** a throwaway script seeded temp
docs (admin/active, member/active, member/archived) + member/admin tool-context tokens in real Postgres
and asserted, then deleted everything — 14/14 PASS: token resolve (member/admin/bogus); member list
excludes admin doc + hides archived; admin list includes admin doc; member CANNOT read admin doc (None);
admin can; archived read == missing (None); truly-missing == None; search never leaks admin doc to a
member and never returns archived. No in-context message was sent to James (off-limits). **C2 complete.**
