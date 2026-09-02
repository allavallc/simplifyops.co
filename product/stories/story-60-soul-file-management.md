# Story 60 - Soul file: generic name + Settings download/upload

## Status
**Done (branch `story-60-soul-file-management`).** Small, focused soul-file work carved out of the
larger [[story-46]] (which still covers the soul/skills/knowledge restructure + self-knowledge gen).

## Goal
1. Stop naming the soul source after the agent — the runtime only ever loads the fixed name `SOUL.md`
   (a symlink), so `souls/james-bott.md` was an odd, misleading name.
2. Let a super-admin **download, edit, and re-upload** the soul from the Settings page; uploading
   replaces the soul and **restarts the runtime** so it loads (owner request).

## Scope
- Rename `souls/james-bott.md` → **`souls/soul.md`**; repoint the live profile symlink
  `~/.hermes/profiles/simplifyops/SOUL.md` → `souls/soul.md` (content unchanged). Update all filename
  references (CLAUDE.md, AGENTS/decisions, `ops/james-stack-setup.md`, `current-architecture.md`,
  backlog).
- `souls/README.md` — note that `soul.md` **is** the agent's personality; customize it to change the
  personality; the "customize me" note lives here, **not** inside `soul.md` (its contents are the
  prompt).
- `admin_api/soul_file.py` — read / validate / atomic-write service (size limit, non-empty,
  secret-like rejection; content never logged).
- Endpoints (super-admin): `GET /api/admin/settings/identity-file/download` (returns `soul.md`),
  `POST /api/admin/settings/identity-file/upload` (JSON `{content}`; validate → write → audit
  non-secret meta → **restart runtime**).
- Settings → File locations: wire the previously-disabled "Upload identity file" placeholder into a
  real Download + Choose-file + "Upload & restart" flow (reads the file client-side, posts JSON).
- Tests: `tests/test_soul_file.py` (validate empty/oversize/secret-like/valid; atomic write; invalid
  does not write).

## Decisions
- **super-admin** for both download and upload (identity-file rules in the settings spec).
- **restart on upload** (owner) — a divergence from the general save-then-explicit-restart model,
  because a soul upload is a deliberate, complete replacement meant to take effect immediately.
- JSON upload (client reads the file) — avoids adding a `python-multipart` dependency.
- Kept `souls/soul.md` (not the blueprint's `soul/agent-soul.md` dir layout) — owner chose the simple
  rename now; the fuller `soul/` + `skills/` + `knowledge/` restructure remains [[story-46]].

## Acceptance
- Runtime still loads `SOUL.md` (symlink valid); soul download returns the file; a valid upload
  replaces it, audits non-secret metadata, and restarts the runtime; invalid uploads are rejected with
  no write. Full gate; merged.

## Review
_(filled during the gate)_
