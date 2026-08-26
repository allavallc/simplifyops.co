# Story 31 - Complete the People page to spec (shared people_service + audit + safety + filters)

## Status
**In progress (local).** First page in the page-by-page blueprint pass
([`architecture/people-page.md`](/home/pi/Desktop/architecture/people-page.md)). Companies /
company-access are **explicitly out of scope** (owner: standalone effort later). Frontend is
server-rendered **Jinja** (not the spec's SPA) per the 2026-08-22 decision.

## Problem
The People admin has **two divergent implementations**, and the UI is wired to the weaker one:
- **Jinja pages** (`admin_api/main.py` `/admin/people*`) — what the operator sees. Basic CRUD with
  **no audit**, **no authority-elevation guard**, **no deactivation safety** (self / last-admin /
  protected profile / typed confirmation), only a `show_deleted` toggle, no `can_influence` column,
  telegram-only identity handling.
- **`admin_api/routes/admin_people.py`** (C1's JSON API, now consumer-less after the React SPA was
  retired in [[story-25]]) — has the governance logic: `_can_grant`, `_count_active_admins`, and
  full audit (`person_created/updated/deactivated/deactivate_rejected/activated`).

For a **governance surface**, the live (Jinja) path missing audit + safety is the real defect: any
logged-in admin can elevate someone to `super_admin`, deactivate the last admin, or delete a person
with **no audit trail**. The spec is explicit: *admin writes and runtime reads must use the same
shared service/store.*

## Approach (architecture per spec — rule 3)
1. **Extract a shared `admin_api/people_service.py`** — move the people logic (validation,
   `can_grant`, active-admin count, create/update/deactivate/restore, identity add/delete, index
   read model) into plain `(conn, actor, …)` functions, each writing the correct audit event.
2. **Wire both callers to it** — the Jinja routes in `main.py` and the JSON routes in
   `admin_people.py` call the same service (no duplicated logic). Runtime governance can adopt it
   later where it reads people.
3. **Bring the Jinja pages to spec** (existing tables only): status filter (active/inactive/all),
   `can_influence` column + broader identity presence, identity **add/delete** on the detail page,
   **typed-confirm** deactivation with self / last-admin / protected-profile guards, and audit on
   every mutation. Notes already persist — verify flow into runtime metadata.

## Scope
- **In:** people, person_identities; audit; the Jinja People pages + the shared service.
- **Out:** companies, `person_company_access`, `identity_claims` (standalone). `id` vs `email`
  route keying — note it, don't churn it this pass unless it blocks the service extraction.

## Acceptance (from people-page.md, minus companies)
- Every People mutation (create/update/deactivate/restore/identity add/delete) writes a non-secret
  before/after audit event via the shared service.
- Deactivation: typed confirmation; blocks self, last active admin, and protected bootstrap
  profiles (rejection audited).
- Authority elevation validated by `can_grant`; index has status filter + `can_influence` +
  identity presence; empty-filter state is accurate.
- Identity add (allowlisted type, shared normalization, dup-fail) and delete (non-primary only,
  cross-person blocked, primary-delete blocked), audited.
- Jinja routes and JSON API share one service; no duplicated people logic.
- Gate deferred with commit/push per owner; browser-tested each step.

## Review
_(fill before commit/push: brooks-review + brooks-audit, then focused + full ruff/pytest.)_
