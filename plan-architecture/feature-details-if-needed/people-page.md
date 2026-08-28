# People Page Build And Architecture Story

This is the consolidated final-state build story for the `agent-brain` People
page in the admin API. It complements
`ops/brain-whitelabel-arch-build-doc.md` and should be read after that document.

Use this as a current build target, not as history. Story numbers are included
only as provenance so an implementation LLM knows which source-system threads
informed the final state.

## Table Of Contents

1. [Source Story Provenance](#source-story-provenance)
2. [Goal](#goal)
3. [Final Architecture Position](#final-architecture-position)
4. [Data Ownership](#data-ownership)
5. [People Index](#people-index)
6. [New Person Flow](#new-person-flow)
7. [Edit Person Flow](#edit-person-flow)
8. [Deactivate Person Flow](#deactivate-person-flow)
9. [Identity Lifecycle](#identity-lifecycle)
10. [Company Access Lifecycle](#company-access-lifecycle)
11. [Runtime And Hermes Boundary](#runtime-and-hermes-boundary)
12. [Authorization And Audit](#authorization-and-audit)
13. [API Contract](#api-contract)
14. [Frontend Contract](#frontend-contract)
15. [Performance Rules](#performance-rules)
16. [Key Mistakes To Avoid](#key-mistakes-to-avoid)
17. [Acceptance Tests](#acceptance-tests)
18. [Official Docs To Recheck](#official-docs-to-recheck)
19. [Build Order](#build-order)

## Source Story Provenance

The most relevant story is **Story 109**, because it captures the latest
completed performance work for the People index and related admin
responsiveness.

| Story | Final-State Use |
| --- | --- |
| Story 109 | Completed source for the current People index performance contract: joined index query, bulk company-access lookup, lazy-once schema initialization, request-duration logging, and no broad threadpool move without measurement. |
| Story 91 | Visual direction for the People index as a dense governance directory. Treat as UI intent, not backend authority. |
| Story 100 | Planned visual direction for Add Person and Person detail forms. Treat as future UI intent only; current code/tests define behavior. |
| Story 10 | Provenance for status and organization filters on the People index. Current implementation/tests outrank the story status text. |
| Story 43 | Field-save standard: every visible editable field must save, persist, read back, display, and audit correctly. |
| `codex-identity-delete` | Provenance for non-primary identity deletion from the person detail page. |
| `codex-identity-upsert` | Provenance for self-service identity update behavior outside the admin page. Keep admin and self-service paths distinct. |
| `codex-person-notes` / `codex-admin-gaps` | Provenance for person notes and company context flowing into governed runtime metadata. |
| Story 131 | Future X identity foundation. Useful only when adding new identity types; not part of the current People page build unless explicitly scoped. |

Current source-system code and current architecture docs outrank all story text.
If an older story conflicts with this build story, treat the older story as
historical background.

## Goal

Build the People admin surface as an API-first governance directory:

- `<CONTROL_API>` owns people, identities, companies, company access,
  validation, persistence, authorization, audit, and JSON contracts.
- `<ADMIN_CLIENT>` renders a browser UI from typed JSON APIs.
- The rebuild must not require server-rendered admin HTML.
- People data is runtime governance data, not address-book decoration.
- The page must support index, new, edit, person deactivation, identity add,
  identity delete, and company access edits.

The People page answers operational questions:

- Who is known to the system?
- How can the system recognize them across channels?
- What admin authority do they have?
- May they converse with `<AGENT_NAME>`?
- May their input influence memory?
- What company or organization context and access topics apply?
- Are they active or deactivated?

## Final Architecture Position

People is a control-plane feature with runtime consequences.

The People page is human-admin operated, but the same database-backed records
are read by message governance before runtime handoff. Do not build People as a
separate CRM table, YAML allowlist, static config file, or frontend-only state.

The source system currently uses FastAPI routes and server-rendered forms. A
rebuild should translate the behavior into API-first endpoints and a separate
admin client. Preserve the source system's service boundary:

```text
admin client
  -> <CONTROL_API> people endpoints
  -> shared People service/store
  -> <BRAIN_DATABASE>
  -> audit
```

Runtime message handling uses the same People service/store:

```text
channel adapter / webhook
  -> POST /messages
  -> people and identity governance
  -> safety
  -> runtime bridge only when allowed
```

The admin UI must not have separate business logic for permission checks,
identity normalization, company access, or audit. Put that logic in shared
service/store code used by both admin endpoints and runtime governance.

## Data Ownership

People governance lives in `<BRAIN_DATABASE>`.

| Data | Owner | Notes |
| --- | --- | --- |
| `people` | `<CONTROL_API>` People service | Stores name, primary email, authority, `can_converse`, `can_influence`, active state, timezone, and notes. |
| `person_identities` | `<CONTROL_API>` People service | Maps a person to channel identities. Values must be normalized for matching. |
| `identity_claims` | `<CONTROL_API>` People service | Supports governed self-service identity verification. Do not bypass it from the admin UI. |
| `companies` | `<CONTROL_API>` People/Companies service | Stores root and child company records plus archived state. |
| `person_company_access` | `<CONTROL_API>` People/Companies service | Links people to companies, relationship, and root-company access scopes. |
| `contact_requests` | `<CONTROL_API>` People/Inbox service | Holds unknown inbound senders for review, approval, link, ignore, block, or failure. |
| audit events | `<CONTROL_API>` audit service | Records every accepted/rejected People mutation with non-secret summaries. |

Do not store these records in the memory database. Memory internals may retain
conversation facts, but they do not authorize people, admin login, company
access, or runtime handoff.

Do not bring back YAML whitelists. The source system explicitly superseded YAML
whitelists with DB-backed people, identities, and contact requests.

## People Index

The People index is a compact governance directory, not a card grid.

Required columns or equivalent displayed fields:

- short person ID;
- full name linked to person detail;
- authority/user type;
- organization/company context;
- identity presence for email, Telegram, Discord, phone, WhatsApp, and calendar;
- `can_converse`;
- `can_influence`;
- active/deactivated status.

Required filters:

- status: `active`, `inactive`, `all`;
- organization/company: `all` or one active company ID.

Filter rules:

- invalid status falls back to `active`;
- invalid company filters fall back to all organizations;
- status and organization filters compose;
- archived company access may be displayed on rows, but archived companies
  should not appear as selectable filter options unless a later product decision
  says otherwise;
- empty filtered results should say that no people match the current filters,
  not imply that People data is missing.

Final performance rule from Story 109:

- use a joined/aggregated index read model such as `list_people_index(...)`;
- aggregate identity types and company access in the same index query;
- do not fetch identities or company access in a per-person loop;
- use a bulk lookup such as `list_company_access_by_person(...)` for pages that
  need company access grouped by many people.

## New Person Flow

Creating a person writes a durable governance record and optionally creates the
primary email identity.

Minimum create fields:

- first name, required;
- last name, required;
- primary email, optional but normalized when present;
- authority: `member`, `contact`, `admin`, or `super_admin`;
- `can_converse`;
- `can_influence`;
- timezone, defaulting to the configured operational default;
- notes, optional;
- optional company;
- optional company relationship;
- optional root-company access scopes.

Create behavior:

- trim human-entered name fields;
- normalize primary email before storage and lookup;
- validate authority through the same service used by edits;
- validate whether the actor can create the requested authority and influence
  level;
- create a primary `email` identity when primary email is present;
- replace company access from the submitted company-access section after the
  person record exists;
- write a `person_created` audit event with non-secret before/after summary,
  including company access summary.

The create path must not require channel identities up front. Admins create the
person first, then add channel identities from the detail page.

## Edit Person Flow

Editing a person updates the same governance record that runtime checks use.

Editable fields:

- first name;
- last name;
- authority;
- `can_converse`;
- `can_influence`;
- timezone;
- notes;
- company;
- company relationship;
- root-company access scopes.

Current source behavior keeps primary email as a hidden detail-field value on
the edit page rather than a normal editable field. If a rebuild exposes primary
email editing, it must preserve the primary email identity contract:

- primary email must normalize the same way as email identities;
- changing primary email must update or create the primary `email` identity;
- duplicate email identity conflicts must fail cleanly;
- primary identity deletion must still be blocked.

Edit behavior:

- load the existing person and company access before mutation;
- reject unknown person IDs with 404;
- validate actor authority before writing authority or influence changes;
- keep active state unchanged through the normal edit form;
- update company access through the shared replacement service;
- write `person_updated` audit with before and after summaries for both person
  fields and company access.

Notes are not cosmetic. They are admin-written context that may be included as
non-secret runtime metadata after governance approves a message. Test notes as
a saved/read-back field.

## Deactivate Person Flow

Person "delete" is deactivation. Do not hard-delete person records.

Required behavior:

- deactivation sets `is_active=false`;
- deactivated people remain visible under the inactive/all filters;
- deactivated people cannot authorize admin login;
- deactivated people cannot be matched as active conversational senders for
  runtime handoff;
- deactivation requires typed confirmation;
- the expected phrase is derived from the current person record;
- successful deactivation redirects back to the People index or returns the
  API equivalent state transition response.

Required safety guards:

- an admin cannot deactivate their own person record;
- the last active admin/super-admin cannot be deactivated;
- bootstrap/protected super-admin profiles are hidden from the danger zone and
  rejected server-side if posted directly;
- rejected protected-profile attempts must be audited;
- all failures must return clear non-secret errors.

Audit:

- successful deactivation writes `person_deactivated`;
- protected-profile rejection writes `person_deactivate_rejected`;
- audit summaries must include non-secret person fields and must not include
  cookies, auth headers, raw request bodies, or secrets.

## Identity Lifecycle

Identities are how runtime governance recognizes a person across channels.

Supported current identity types:

- `email`;
- `telegram`;
- `discord`;
- `phone`;
- `whatsapp`;
- `google_calendar`;
- `google_chat`.

The conversational identity subset currently excludes `google_calendar`.
Calendar notification senders are provider notifications, not ordinary people;
they require special handling through reply-to/linking rules and the Inbox when
not safely linked.

Identity add behavior:

- admin adds non-primary identities from the person detail page;
- identity type must be allowlisted;
- value must be nonblank;
- normalization must be type-specific and shared with governance lookup;
- duplicate normalized identity conflicts must fail cleanly;
- actor authorization must use the same person-write rules as person edits;
- accepted adds write `person_identity_added` audit with non-secret identity
  type/value summary.

Identity delete behavior:

- use a server/API mutation; in the source HTML form this is a POST because HTML
  forms only support GET/POST;
- verify the identity exists;
- verify it belongs to the route person;
- reject cross-person identity deletion;
- reject primary identity deletion with a clear error;
- delete only the identity row, not the person;
- write `person_identity_deleted` audit with the identity ID or another
  non-secret identifier.

Do not build an admin "rename identity" shortcut unless explicitly scoped.
Identity value changes should go through a clear update/upsert operation with
the same validation, uniqueness, and audit rules.

## Company Access Lifecycle

Company access is part of person governance and runtime context.

Relationships:

- `team_member`;
- `advisor`;
- `investor`;
- `vendor`;
- `local_org_admin`;
- `super_admin_owner`.

Access scopes:

- `board_materials`;
- `financial_detail`;
- `financial_summary`;
- `investor_updates`.

Final rules:

- a person may have zero or more company access rows in the data model;
- the current source UI edits one primary company-access row on the person form;
- the replacement service deletes existing access rows for that person and
  inserts the submitted rows in one controlled operation;
- child-company access does not save root-company topic scopes;
- `super_admin_owner` on the root company receives all root-company scopes;
- root-company super-admin-owner scopes are displayed as checked/disabled in
  the UI because they are derived from the relationship;
- company access changes must audit before/after summaries.

Do not confuse `local_org_admin` with admin-login authority. It is a company
relationship, not permission to operate the admin API.

## Runtime And Hermes Boundary

The People page does not call Hermes directly.

People data affects runtime only through governed message handling:

```text
POST /messages
  -> match active person by channel identity
  -> check `can_converse`
  -> check `can_influence`
  -> attach non-secret person/company/runtime context
  -> safety
  -> private runtime bridge
```

Runtime context may include:

- person ID;
- authority;
- primary email when present;
- linked calendar identity when relevant;
- timezone;
- company name when available;
- company access topics;
- notes when present and non-empty;
- `can_influence`.

Do not expose raw people records, full identity tables, contact request history,
admin audit logs, or secrets to Hermes. Send only the minimal non-secret context
the runtime needs after governance has approved the message.

Unknown senders must not bypass People governance. They should become pending
contact requests or equivalent review work until an admin approves, links,
ignores, blocks, or otherwise resolves them.

## Authorization And Audit

People is an admin-only control surface.

Minimum authorization:

- index/detail/new reads require an authenticated admin or super admin;
- create/update/deactivate/add-identity/delete-identity require an
  authenticated admin or super admin;
- actor write authority must be checked by the People service before mutating
  elevated authority or memory-influence rights;
- bootstrap super-admin emails are used only for initial bootstrap/protection,
  not as a replacement for DB-backed people governance.

Every mutation must audit:

- actor email;
- action;
- target object;
- environment;
- request metadata when available;
- accepted/rejected/failed result;
- non-secret before summary;
- non-secret after summary.

Audit must never include:

- session cookies;
- OAuth tokens;
- API keys;
- raw `.env`;
- channel secrets;
- fully expanded config;
- raw prompts or full user messages unless explicitly approved for a separate
  audit surface.

## API Contract

Use typed JSON contracts. Do not make the browser infer persisted state from
rendered text.

Minimum read endpoints:

- `GET /api/admin/people?status=active|inactive|all&company=<uuid|all>`
- `GET /api/admin/people/{person_id}`
- `GET /api/admin/people/{person_id}/identities`
- `GET /api/admin/people/{person_id}/company-access`
- `GET /api/admin/people/form-options`

Minimum mutation endpoints:

- `POST /api/admin/people`
- `PATCH /api/admin/people/{person_id}`
- `POST /api/admin/people/{person_id}/deactivate`
- `POST /api/admin/people/{person_id}/identities`
- `DELETE /api/admin/people/{person_id}/identities/{identity_id}`
- `PUT /api/admin/people/{person_id}/company-access`

Recommended response models:

- `PersonSummary` for index rows, including identity-type presence and company
  labels;
- `PersonDetail` for the edit page;
- `PersonIdentity`;
- `PersonCompanyAccess`;
- `PersonFormOptions`, including authority values, identity types, companies,
  relationships, scopes, and timezone options;
- `AuditResult` or standard mutation envelope for accepted/rejected mutations.

Mutation responses should return the updated resource or a redirect-equivalent
location. Errors should use stable machine-readable codes plus clear
operator-readable messages.

If `<ADMIN_CLIENT>` is served on a different origin, configure exact CORS
origins and credential behavior. Do not use wildcard CORS for authenticated
admin requests.

## Frontend Contract

The rebuild target is not server-rendered admin HTML.

Preserve these UX behaviors in the separate admin client:

- People index remains a dense table or equivalent high-density record view;
- status and organization filters are visible in the page header or equivalent
  persistent filter surface;
- identity presence is text-equivalent and never conveyed by color alone;
- governance fields are visually distinct from basic profile metadata;
- Add Person and Person detail group fields by operator task;
- deactivation is in a danger/status area and requires typed confirmation;
- identity delete uses a clear destructive action and confirmation;
- all form fields preserve typed values on validation errors where practical;
- mobile/narrow layouts remain usable without overlapping controls.

Do not introduce page-specific duplicate styling or a frontend framework
dependency unless a later product decision explicitly chooses that stack. If the
new `agent-brain` already has a frontend framework, use its established design
system rather than copying source-system templates.

## Performance Rules

Story 109 is the latest completed performance reference.

Required rules:

- schema setup must not run on every People page request after successful
  initialization;
- People index must use one joined/aggregated query or equivalent read model;
- company access for many people must use a bulk query, not one query per
  person;
- active identity lookup should use joined identity queries, not repeated
  per-identity reads;
- request-duration logs should be non-secret and bounded;
- slow-request warnings should log route/status/duration style metadata only;
- do not move broad admin routes into threadpools without measured evidence and
  explicit scope.

Use indexes or materialized read models where the database needs them, but keep
the first rebuild simple unless measured performance requires more.

## Key Mistakes To Avoid

- Do not bring back YAML people whitelists.
- Do not put people governance tables in the memory database.
- Do not hard-delete person records from the admin page.
- Do not let deactivated people authorize admin login or runtime conversation.
- Do not let the last active admin be deactivated.
- Do not allow self-deactivation through a direct API post.
- Do not delete primary identities.
- Do not let one person's route delete another person's identity.
- Do not treat Google Workspace notification senders as normal person
  identities.
- Do not treat `local_org_admin` as admin-login authority.
- Do not save root-company topic scopes for child-company relationships.
- Do not duplicate identity normalization in the frontend.
- Do not make the People index run identity/company N+1 queries.
- Do not skip rejected-attempt audit logs.
- Do not expose raw people records, audit logs, notes dumps, tokens, cookies, or
  config in runtime context.
- Do not copy source-system server-rendered HTML as the rebuild architecture.

## Acceptance Tests

Automated tests are non-negotiable because People drives governance.

Index tests:

- renders authority, organization, identity presence, `can_converse`,
  `can_influence`, and active state;
- supports status filter;
- supports organization filter;
- composes status and organization filters;
- invalid filters fall back safely;
- archived company access is displayed distinctly but not offered as an active
  filter option;
- empty filtered state is accurate;
- index read model does not perform per-person identity/company queries.

Create tests:

- creates every persisted person field;
- trims/normalizes primary email;
- creates primary email identity when primary email exists;
- saves optional notes and timezone;
- saves company relationship and scopes;
- audits `person_created`;
- rejects invalid authority, invalid company, invalid relationship, invalid
  scope, and unauthorized elevation.

Edit tests:

- renders saved values before edit;
- saves and reads back every editable field;
- keeps normal edit separate from deactivation;
- updates company access through the replacement service;
- blocks child-company root-topic scopes;
- gives root `super_admin_owner` all scopes;
- audits before/after `person_updated`.

Deactivate tests:

- requires typed confirmation;
- rejects wrong confirmation;
- hides and blocks protected bootstrap super-admin profiles;
- rejects self-deactivation;
- rejects deactivation of the last active admin;
- sets `is_active=false`;
- removes the person from the active filter and shows them under inactive/all;
- blocks admin login and runtime conversation for deactivated people;
- audits accepted and protected rejected paths.

Identity tests:

- add identity accepts every current allowed type;
- add identity rejects unsupported type and blank value;
- duplicate normalized identity fails cleanly;
- detail page/read endpoint hides primary email from removable identities;
- delete identity succeeds for a non-primary identity owned by the person;
- delete identity rejects another person's identity;
- delete identity rejects primary identity;
- add and delete audit events are written without secrets.

Runtime governance tests:

- active known person with `can_converse=true` can reach runtime after safety;
- active known person with `can_converse=false` is blocked before runtime;
- `can_influence` is carried into runtime metadata/status;
- notes and company context are included only after governance approves;
- unknown conversational sender creates or updates pending contact review work;
- Google Workspace notification sender handling uses reply-to/linking rules.

## Official Docs To Recheck

Recheck current official docs before implementation:

- FastAPI bigger applications and `APIRouter` structure:
  <https://fastapi.tiangolo.com/tutorial/bigger-applications/>
- FastAPI form handling if preserving any HTML form compatibility during
  migration: <https://fastapi.tiangolo.com/tutorial/request-forms/>
- MDN `<form>` behavior for POST compatibility and form controls:
  <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/form>
- PostgreSQL index docs when adding or revising People lookup/index queries:
  <https://www.postgresql.org/docs/current/indexes.html>

Prefer official framework/database documentation and the source-system code over
blog posts.

## Build Order

1. Define People domain schemas and service/store interface.
2. Implement database tables, constraints, indexes, and schema/migration path.
3. Implement shared validation: authority, identity type, identity
   normalization, company relationship, access scopes.
4. Implement admin auth/session dependency and actor write authorization.
5. Implement create/read/update/deactivate People service methods.
6. Implement identity add/delete service methods.
7. Implement company access replacement and bulk read helpers.
8. Implement People index read model with aggregated identities and company
   access.
9. Implement API read endpoints.
10. Implement API mutation endpoints with audit.
11. Implement `<ADMIN_CLIENT>` index, new, detail/edit, deactivation, identity,
    and company-access UI.
12. Wire runtime governance to the same People service/store.
13. Add acceptance tests from this document.
14. Verify local behavior, including admin UI workflows and runtime governance
    decisions.

Do not split implementation into a People UI story and a separate governance
story unless the shared service contract is already written. The page is only
correct when admin writes and runtime reads use the same source of truth.
