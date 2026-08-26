# Architecture Decisions Log

Dated log of durable product/architecture decisions + rationale. Newest first. Durable decisions go
here (not buried in stories/handoffs/chat). Each entry: date, decision, why, and where it lives.

---

## 2026-08-26 — Adopt the whitelabel blueprint selectively/incrementally
**Decision:** Follow the genericized blueprint (`~/Desktop/architecture/agents-whitelabel.md`) via a
prioritized, selective backlog (`product/stories-list.md`), keeping what already works — not a full
rebuild. Whitelabel `<agent name>`→James, `agent_*`→`simplifyops_*`.
**Why:** Most of the control-plane/governance/durable-work core already aligns; a near-rebuild isn't
warranted. **Defaults:** keep current `gateway`+`hermes_client` (no runtime-bridge yet); skip Docker
(native/systemd); MCP work needs Anthony.

## 2026-08-25 — Gateway decomposed behind a `hermes_client` adapter (protected rule 10)
**Decision:** `gateway.py` (1181-line god-module) split into 9 single-responsibility modules; all
Hermes API access goes through one `hermes_client` module. **Why:** isolate the external-runtime
boundary so upgrades touch one seam, not spaghetti. Validated by the 0.20.5 upgrade. [[story-26]]

## 2026-08-25 — Hermes upgraded 0.19.0 → 0.20.5 via `install.sh` (pip deprecated)
**Decision:** Migrate off the deprecated pip install to the supported `install.sh`; pin known-good,
inspect, install, test, then re-pin. Config auto-migrated v33→v39; the old `codex_runtime` patch is
obsolete. **Why:** pip is frozen upstream; safe pin-first workflow. [[story-33]]

## 2026-08-22..24 — Runtime config is environment-owned; DB-source-of-truth + per-env editor
**Decision:** Live provider/model/tool/MCP config is per-environment, gitignored, and never
tracked/overwritten by a shared source (each env differs). Editable per-env from the admin UI (secrets
presence-only); `config.yaml` is a generated artifact, never the hand-edited source of truth.
**Why:** a shared/tracked config kept overwriting per-env provider/tool setups. Protected invariant 11.
[[story-34]]

## 2026-08-22 — Admin UI is server-rendered Jinja; retire the React SPA (reverses prior 2a)
**Decision:** Admin UI = server-rendered Jinja in `admin_api/templates/`; no React/SPA/build step.
Retire `admin-client/`. **Why:** owner preference (low-maintenance, no build treadmill, one contract),
and the Jinja pages already existed. Protected invariant 2. [[story-25]]

## 2026-08-22 — People governance has one source of truth: `people_service`
**Decision:** Admin Jinja routes, the JSON API, and runtime governance all read/write people via
`admin_api/people_service.py` — audit + safety guards in one place. **Why:** two divergent people
code paths (the UI used the weaker one, no audit). Protected invariant 9. [[story-31]]

## 2026-08-22 — Protected architecture invariants (approval required to change)
**Decision:** The "Architectural rules" in `current-architecture.md` are PROTECTED invariants; changing
one needs explicit owner approval recorded here. brooks findings touching them are 🔴 by default.
**Why:** keep the clean boundaries the audit found from silently decaying.
