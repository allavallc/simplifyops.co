# Story 21 - People page (governance directory) per architecture spec

## Status
In progress (2026-08-13). Architecture resolved (API-first, Vite+React+TS SPA).
**First vertical slice built & live:**
- Vite+React+TS client scaffolded at `admin-client/`, built to `dist/`, served
  same-origin by the control plane at **`/app/`** (StaticFiles mount, SPA fallback).
- `GET /api/admin/people?status=active|inactive|all` — aggregated PersonSummary
  index (`routes/admin_people.py`): one joined query aggregating identity types,
  `can_influence`, `is_active` (`deleted_at IS NULL`), status filter with safe
  fallback. No N+1.
- SPA People index page renders it (ID, name, authority, identity-presence columns
  for email/telegram/discord/phone/whatsapp/calendar/chat, converse, influence,
  active) with a status filter, session-cookie auth, empty/error states.
- Verified: API 401 (auth-gated) when unauthenticated; `/app/` 200; aggregation
  query returns correct data.

**Second slice built & live (2026-08-13): Detail + create/edit + deactivate.**
- Name split: `people.first_name` + `last_name` (backfilled from `person_name`,
  which is kept in sync on writes for legacy readers).
- `routes/admin_people.py`: `GET /form-options`, `GET /{id}` (PersonDetail +
  identities + derived confirm phrase), `POST` create (authority validation +
  actor-grant check + primary email identity + audit `person_created`), `PATCH
  /{id}` edit (audit before/after), `POST /{id}/deactivate` (typed confirmation =
  person email, guards: protected super-admin [env `PROTECTED_SUPER_ADMIN_EMAILS`],
  no self-deactivate, no last-active-admin, audit `person_deactivated`/
  `person_deactivate_rejected`), `POST /{id}/activate`.
- SPA (`admin-client`): react-router (HashRouter), index rows link to detail,
  Person detail (fields + identities + danger-zone deactivate/activate with typed
  confirm), create/edit form (form-options dropdowns, first/last, authority,
  timezone, converse/influence, notes). All endpoints verified 401-gated; SPA
  builds + served at `/app`.

**Spec deviations (flagged, not silent):**
- Primary email REQUIRED on create (schema `person_email NOT NULL UNIQUE` + FKs);
  spec says optional. Needs a nullable-email migration to fully match — deferred.
- Email not editable on edit (kept as identity, per spec's hidden-primary-email).

Remaining phases: identity management (add/delete typed identities — incl. the
soft-vs-hard identity-row delete nuance in Decision 3), companies subsystem,
acceptance tests. **Could not click-test live** (needs a browser + admin session —
Anthony can at `/app`); verified at API/build/serving layers.

Deferred note: `admin-client/dist` is gitignored (build artifact) — a build step is
needed on deploy, or add a CI build. The `/app` mount is guarded by `dist` existing.

## Source
Authoritative spec: `~/Desktop/architecture/people-page.md` (consolidated final-state
build story; complements `brain-whitelabel-arch-build-doc.md`). This story adopts it
as the People page target and records the gap + a phased plan.

## Goal (from spec)
People as an **API-first governance directory** — control-plane data that message
governance reads before runtime handoff. Supports: index, new, edit, deactivate,
identity add/delete, company-access edits. Never a CRM/YAML/frontend-only store.

## Gap analysis (current vs spec)
| Area | Current | Spec target | Gap |
|---|---|---|---|
| Architecture | server-rendered FastAPI + Jinja | API-first typed JSON + separate admin client | **fork — decision needed** |
| Name | single `person_name` | `first_name` + `last_name` (both required) | split + migrate |
| Active state | `deleted_at` (story-20 soft delete) | `is_active=false` "deactivate" + inactive/all filters | reconcile semantics |
| Index columns | ID, name, telegram, authority, can_converse, status | + `can_influence`, org/company, identity presence (email/tg/discord/phone/whatsapp/calendar), active state | expand |
| Filters | show-deleted toggle | status (active/inactive/all) + organization | add filters |
| Identities | telegram field on form; `person_identities` table exists | add/delete typed identities from detail page (7 types, normalized, audited) | build identity mgmt |
| Companies | none | `companies`, `person_company_access`, relationships, scopes | **new subsystem** |
| Deactivation | JS confirm + soft delete; last-admin guard (API) | typed confirmation, self-guard, protected super-admin, `person_deactivated` audit | harden |
| Audit | partial | every mutation audited, before/after non-secret summaries | expand |
| Tests | none | acceptance tests are "non-negotiable" | add |

## DECISION 1 — architecture: API-FIRST (RESOLVED, Anthony 2026-08-13)
**API-first + a separate admin client. NO server-rendered pages.** Emphatic.
- `<CONTROL_API>` = typed JSON endpoints (`GET/POST/PATCH/DELETE/PUT /api/admin/people…`).
- `<ADMIN_CLIENT>` = a separate client app that renders from those JSON APIs.
- The existing server-rendered Jinja admin (stories 13/20) is **not** the target
  and will be superseded by the API + client for the People surface (and, by
  extension, the rest of the admin over time).
- Shared People service/store logic is used by BOTH the API endpoints and runtime
  message governance (single source of truth).

### New question this raises (see OPEN DECISION 0)
Which frontend stack / does an admin client already exist for agent-brain?

## OPEN DECISION 2 — scope/phasing
The spec is a 14-step build. Companies/company-access is a whole subsystem. Propose
phasing (assuming Decision 1 = A):
- **Phase 1 (governance hardening, no new subsystem):** align deactivation to spec
  (is_active/typed-confirm/self+last-admin+protected guards, `person_deactivated`
  audit), add `can_influence` to index, add status filter (active/inactive/all),
  extract a shared People service module.
- **Phase 2 (identity management):** add/delete typed identities from the detail
  page (email/telegram/discord/phone/whatsapp/google_chat; calendar special-cased),
  normalization shared with governance, audit.
- **Phase 3 (name split):** `first_name`/`last_name` migration + forms.
- **Phase 4 (companies subsystem):** `companies`, `person_company_access`,
  relationships, scopes, index org column + filter, replacement service.
- **Phase 5:** acceptance tests across all of the above.

Which phases, in what order, and how much this session?

## DECISION 3 — soft-delete everywhere (RESOLVED, Anthony 2026-08-13)
Reuse `deleted_at` as the deactivation model: `deleted_at IS NOT NULL` = deactivated;
People UI action becomes **Deactivate / Activate**; index status filter active/
inactive/all maps to `deleted_at IS NULL` / `IS NOT NULL` / no filter. **No new
`is_active` column.**

**System-wide principle:** the same `deleted_at` soft-delete strategy applies to
**all entity deletions** — no hard `DELETE FROM` on any governance/data entity
(people, companies, and every future entity). Deletions are always recoverable.

### Nuance to confirm when we build identity management (Phase: identities)
The spec's identity delete *removes the `person_identities` row* ("delete only the
identity row"). That conflicts with "all deletions are soft." Options for identity
rows: (a) also soft-delete (add `person_identities.deleted_at`) to honor the
system-wide rule; (b) follow the spec and hard-delete the identity row (it's a
sub-mapping, not an entity). **Flag for Anthony at that phase** — not needed for the
current index slice.

## Guardrails already honored (from spec, via story-20)
- No hard delete of person records ✅ (soft delete live).
- Deactivated people can't converse ✅ (`_governance` excludes them).
- Last active admin can't be removed ✅ (`_count_admins` active-only).
Still missing: self-deactivation guard, typed confirmation, protected super-admin,
`person_deactivated` audit event.

## Key mistakes to avoid (from spec)
No YAML whitelists; no people tables in memory DB; no hard delete; no N+1 identity/
company queries on the index; no primary-identity delete; no cross-person identity
delete; don't treat Workspace notification senders as people; don't duplicate
identity normalization in the frontend; don't skip rejected-attempt audits.

## Acceptance
Per spec's "Acceptance Tests" section — index/create/edit/deactivate/identity/
runtime-governance tests. Scoped to whichever phases are approved.
