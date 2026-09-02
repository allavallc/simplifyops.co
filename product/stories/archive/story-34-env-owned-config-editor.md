# Story 34 - Per-environment config editor (non-secret YAML + injected secrets → materialize → restart)

## Status
**Proposed.** Config-management mechanism that reshapes [[story-32]]'s Provider/Model/Approvals
section (replaces direct `config.yaml` writes). Design settled with owner 2026-08-24.

## Problem
Hermes runtime config (`~/.hermes/profiles/simplifyops/config.yaml`: providers, model, approvals,
memory, **MCP servers**) is **per-environment and must differ** across local/staging/prod. Two hard
lessons:
- A **shared/tracked** config overwrites each env's provider/tool/MCP differences → drift/breakage.
  So config must stay **env-owned, gitignored, never propagated**. (This repo is **public** — config
  with infra details/secrets can never be tracked anyway.)
- MCP servers/capabilities change **fast**, and hand-editing a file over **SSH on each env** is
  error-prone.
Need: edit each env's config **from the admin UI (no SSH)**, keep secrets out of the editable
surface, keep envs independent.

## Design (owner decisions, 2026-08-24)
**Two layers that never mix at rest:**
1. **Editable non-secret config** (per-env, env-owned) — everything except secrets; secrets appear
   only as **named references** (e.g. `${SIMPLIFYOPS_OPENAI_KEY}`). Safe to show/edit/upload.
2. **Env-owned secret store** (`.env` / gitignored secrets file, perms 0600) — name → value.

**Materialize:** non-secret config + resolve references from the secret store → **final
`config.yaml`** (atomic write, restrictive perms) → **restart runtime** → **rollback** to last-good
on failed restart. Final file is generated, gitignored, never displayed.

**UI (Settings page, one environment):**
- **Config editor:** the non-secret config as an **editable YAML block** *and* **upload-to-replace**;
  validated (YAML parse + structure) on save; env banner showing which env.
- **Secrets panel:** list referenced secret **names** with **set / missing** status; **masked
  set/update** field (blank = keep existing); values never rendered back.
- **Save & apply:** validate → materialize → restart, behind **typed confirmation**; inline errors;
  rollback notice on failure.
- **Independent per-env only** — no propagation, no copy/diff (zero overwrite risk).

## Build order
1. **Verify Hermes interpolation first.** Does Hermes natively expand `${VAR}` in `config.yaml`
   (reads from its env)? If **yes**, lean on it (references stay as `${VAR}`, minimal merge). If
   **no**, our materialize substitutes before writing. Prefer MCP **`env:` passthrough** so secrets
   never land in the file.
2. Config service: read/validate/backup/write final config atomically; resolve secret refs; fail
   loud on missing secret; restart + rollback.
3. Secret store writer (env-owned, 0600, presence-only reads).
4. Admin UI: YAML editor + upload; secrets panel; save & apply with typed confirm.
5. Redacted audit on every mutation (config saved, secret set/rotated, materialize, restart, rollback).

## Guardrails
- 🔴 **MCP editing needs Anthony.** This surface edits MCP config; per CLAUDE.md, do not build/enable
  the MCP-editing path without Anthony's explicit guidance. Build the generic mechanism up to that
  line and confirm before enabling MCP edits.
- ⚠️ **Restart hits the live agent** (rule 8) — coordinate; test the write/validate path without
  restart where possible.
- **Public repo:** never commit config, secrets, infra details, or the final `config.yaml`.
- Never log/return raw config, secret values, or expanded config; secrets presence-only.

## Acceptance
- Each env's config editable via the admin UI (edit YAML or upload) + secrets settable (masked,
  presence-only), **no SSH**; envs independent (no propagation/overwrite).
- Save → validate → inject → materialize → restart works, with **rollback on failed restart**.
- No secret ever displayed or logged; final `config.yaml` stays gitignored/env-owned.
- Redacted audit on every mutation. Hermes interpolation behavior verified + documented.

## Review
_(fill before commit/push: brooks-review + brooks-audit, then focused + full ruff/pytest.)_
