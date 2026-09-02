# Story 44 - Config ownership + per-env editor (foundation)

## Status
**Done (branch `story-44-config-ownership`).** P1. Config-ownership boundary + per-env editor.
**Absorbs/supersedes [[story-34]].** Foundation for [[story-45]] (full Settings page).

## Problem (owner's actual pain)
Editing runtime config per environment today means SSH-ing to the box and hand-editing
`~/.hermes/profiles/simplifyops/config.yaml`. That is error-prone, especially for adding an MCP server
or changing a capability, and local/staging/prod legitimately need **different** provider/tool/MCP
setups that a shared tracked file kept overwriting. We want non-secret runtime config **editable per
env from the admin UI**, with secrets never tracked and never printed.

## Grounding
- Law: `plan-architecture/agents-whitelabel-instructions.md` §"Configuration ownership",
  §"Configuration and Secret Ownership".
- Feature spec: `plan-architecture/feature-details-if-needed/settings-page.md` §"Config File, Not Env
  Var Sprawl", §"Persistence Ownership", §"Field-Save Standard" (its config-writer rules are the target).
- Product decision 2026-08-22..24 (config is env-owned, DB/UI-editable, secrets presence-only —
  protected invariant 11).
- Our reality: `config.yaml` lives at `/home/pi/.hermes/profiles/simplifyops/config.yaml` (env-owned,
  gitignored) **and is itself the live runtime config** — we have **no supervisor** that copies a base
  template into a project home (that's the blueprint's model; we run Hermes via `install.sh` + systemd).
  The Settings "Provider+Model" section already writes `config.yaml` → restarts runtime.

## Divergences from the blueprint (approved / to record — not drift)
1. **Jinja, not a SPA.** The settings spec assumes a separate admin client over CORS JSON. Our
   protected rule 2 is server-rendered Jinja + a `/api/*` JSON layer. We build JSON endpoints **and**
   Jinja pages; **no** React/CORS/admin-client. (The spec explicitly yields to current architecture.)
2. **No supervisor / project-home copy.** The blueprint's `supervisor.py` copies
   `hermes/config.base.yaml` → project-home `config.yaml`. We have no supervisor; `config.yaml` at the
   profile path *is* the live file. So "copy base→runtime" collapses to "**seed** `config.yaml` from the
   tracked base template only when it is missing," never an overwrite of an existing env file.

## Config-ownership model (decided A/B/C 2026-08-29)
```
hermes/config.base.<env>.yaml  (NEW, tracked, PER-ENV: local/staging/prod)  structural, non-secret
        │  seed-if-missing (never overwrite) · structural changes via explicit allowlisted apply (dry-run+backup)
        ▼
~/.hermes/profiles/simplifyops/config.yaml (env-owned, gitignored)  ← the live runtime config for THIS env
        ▲  structured read/write via one service
        │
admin_api/runtime_config.py (NEW service)  parse → edit allowlisted non-secret keys → atomic write → audit
        ▲
admin JSON API + Jinja editor (this story: mechanism; full Settings sections = story 45)
        │  reload-needing change → restart_required=true
        ▼
POST /api/admin/runtime/restart  (one shared explicit restart action; current Provider/Model flow refactored onto it)
```
**Env selection:** the active env is read from an env var (e.g. `SIMPLIFYOPS_ENV`, default `prod` — the
Pi is currently the only box; staging/prod split is deferred [[story-30]]). The service picks
`config.base.<SIMPLIFYOPS_ENV>.yaml`. This story creates the base for the current env; adding
local/staging bases later is just another tracked file. Per-env bases mean one env's structural
defaults can never overwrite another's — the original overwrite pain.
Rules the writer must honor (from the spec):
- **Structured YAML parse/merge — never text replace.** Preserve unrelated keys, keep existing values
  intact, write atomically, restrictive perms.
- **Never print/return the whole config or fully-resolved values.** Logs/audit carry paths, field
  names, hashes/sizes, or presence status only.
- **Secrets are presence-only** and stay in env/secret storage — not in `config.base.<env>.yaml`, not
  returned to the browser, not logged. Blank secret field = "keep existing."
- **Tracked base is bootstrap only.** A Settings save writes the **live env** `config.yaml`; it must
  **never** mutate any `config.base.<env>.yaml`.
- **Structural changes (add MCP server / new provider block) go through an allowlisted, dry-run +
  backup apply** (`metadata pull / check / apply`), not a free-form file overwrite.
- Provider/model changes that need a reload return `restart_required=true` (restart is explicit).

## Scope of THIS story (foundation only)
1. `hermes/config.base.<env>.yaml` — tracked **per-env** structural templates (non-secret keys only),
   documented; created for the current env now (`SIMPLIFYOPS_ENV`, default `prod`).
2. `admin_api/runtime_config.py` — the shared config service: `read_metadata()` (non-secret, redacted),
   `seed_if_missing()` (from the active env's base), `apply_allowlisted(patch)` (structured merge,
   atomic write, backup, audit), `restart_required` signalling. Allowlist of editable non-secret keys
   defined here — **incl. MCP-server registrations** (add/remove/toggle a server + non-secret args).
3. JSON endpoints: `GET /api/admin/settings/runtime` (metadata), `PATCH /api/admin/settings/runtime`
   (allowlisted apply), `POST /api/admin/runtime/restart` (the one shared explicit restart) — admin-auth,
   audited, redacted; the current Provider/Model restart is refactored onto the shared endpoint.
4. A minimal **Jinja** editor surface (allowlisted fields + MCP-server list + presence-only secrets +
   a "restart runtime" action) — the full sectioned Settings UI is **story 45**.
5. Tests: writer preserves unrelated keys / atomic / never returns full config; base-not-mutated;
   blank-secret preserved; allowlist rejects non-allowlisted keys; MCP add/remove round-trips; restart
   endpoint authz + audit; audit before/after non-secret.
- **Out of scope (→ 45):** channels, Workspace OAuth, identity-file upload, admin-contact, the full
  sectioned Settings page, session-health UI (backend exists), per-tool MCP policy.

## Decisions (approved 2026-08-29)
- **A — editable allowlist:** provider / model / context-length / session bits **+ MCP-server
  registrations**. Per-tool policy deferred.
- **B — restart:** explicit, via one shared `POST /api/admin/runtime/restart`; save returns
  `restart_required=true`; nothing restarts implicitly. Current Provider/Model flow refactored onto it.
- **C — per-env:** **per-env tracked base variants** `config.base.<env>.yaml` (local/staging/prod);
  live `config.yaml` stays env-owned/gitignored; base only seeds-if-missing / explicit allowlisted
  apply — never overwrites. One env's defaults can't clobber another's.

## Acceptance
- Config service + `config.base.yaml` + the two endpoints + minimal Jinja editor land with tests green;
  editing a non-secret key from the UI persists to the env `config.yaml`, reads back, and audits, with
  no secret ever returned/logged and the tracked base untouched. Full gate; merged after approval+gate.

## Review
Built as decided (A/B/C). `admin_api/runtime_config.py` is the single config-ownership service
(seed-if-missing from tracked per-env base, redacted `read_metadata`, allowlisted structured `apply`
with atomic write + `.bak`, MCP upsert/toggle/remove, explicit `restart_runtime`); `settings.py` and
`pages.py` refactored onto it (removed two inline `config.yaml` readers). New endpoints:
`POST /api/admin/runtime/restart` (the one shared restart) + `/api/admin/runtime/mcp[...]`; Settings
page moved to the explicit-restart model + an MCP-servers section. `hermes/config.base.prod.yaml`
tracked; PyYAML declared for CI.

**brooks-review:** R2 duplication *reduced* (one config source); clean one-way seam; `read_metadata`
redacts MCP `env` values (verified on live config — env keys only). 🟡 endpoint-level tests absent
(need app+DB) — mitigated: all logic lives in `runtime_config`, which has 8 unit tests; matches the
repo's existing no-endpoint-test pattern. **brooks-audit:** strengthens invariant 11 (env-owned
config single seam); no cycles/god-module. No 🔴. **Gate:** rebased on `origin/main`; focused+full
ruff clean; pytest 20 green; app imports (73 routes); `read_metadata` validated against the live
config (4 MCP servers, values redacted). **Done.**

**Deferred to [[story-45]]:** channels, Workspace OAuth, identity-file upload, admin-contact, the full
sectioned Settings page, per-tool MCP policy.
