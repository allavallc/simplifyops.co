# Story 64 - Knowledge feature (curated docs + self-knowledge + governed retrieval)

## Status
**Plan — awaiting approval (no code yet).** 🧱 large / multi-phase. Implements
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

## Review
_(per phase, after approval + gate)_
