# Story 61 - Settings: Admin Contact section (real)

## Status
**Done (branch `story-61-settings-admin-contact`).** First shippable increment of [[story-45]]
(Settings page to spec) — replace a UI-only shell with a working, audited field-save section.

## Goal
Turn the disabled "Admin contact" placeholder into a real control: pick a **primary** (required) and
optional **secondary** operational contact from the active admin/super-admin people, persisted and
audited, following the field-save lifecycle.

## Scope
- `people_service.active_admin_emails(conn)` — active (`deleted_at IS NULL`, allowed) admin/super-admin
  people (email + authority); the single source both the page dropdown and the save-validation use.
- `settings.py`: `GET /api/admin/settings/admin-contact` (primary/secondary + options),
  `PATCH` (validate both are active admins; secondary optional and ≠ primary; persist to
  `admin_settings` keys `admin_contact_primary`/`admin_contact_secondary`; audit before/after).
- `pages.py`: real `admin_contact` context (primary/secondary from `admin_settings`, options from
  `people_service`) — removes the "placeholder until admin_contact_settings table is built" stub.
- Settings template: primary/secondary `<select>`s populated from active admins + wired Save.
- **No new table** — reuse `admin_settings` (minimal code).

## Notes
- Storage: `admin_settings` string values; empty secondary stored as `""`, surfaced as `None`.
- **Tests:** no new unit test — the logic is thin DB-backed CRUD + a membership check, and the
  admin_settings/people reads need a live DB (matches the repo's existing untested-endpoint pattern;
  `runtime_config`/`soul_file` hold the testable logic). Verified via app import + the field-save flow.

## Acceptance
- Section shows active admins; saving a valid primary (+optional secondary) persists, reads back, and
  audits; invalid/duplicate selections are rejected. Full gate; merged.

## Review
_(filled during the gate)_
