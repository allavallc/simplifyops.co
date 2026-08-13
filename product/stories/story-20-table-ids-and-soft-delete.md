# Story 20 - Admin data tables: show IDs everywhere + soft-delete (no hard delete)

## Status
✅ Built 2026-08-13. Decisions resolved below. Live.

### What was built
- **Soft delete (people):** `people.deleted_at` column; both hard-deletes → `UPDATE
  deleted_at=now()`; list hides deleted by default with **Show deleted** toggle +
  **Restore**; view/edit show Restore for deleted rows; button still says "Delete".
- **Governance hardening:** `_governance` excludes deleted people (a deleted person
  can no longer converse → treated as unknown); `_count_admins` counts active only;
  people API list defaults to active-only (`?show_deleted`).
- **IDs on tables + view/edit:** people (id col + view card + edit readonly field),
  Activity & Inbox (`request_id` col; Activity detail already showed it), and all
  UI-only tables (companies, knowledge, memories, automations, job_credentials,
  tools) got an ID column (populated when their backends land).
- Tools/MCP: "ID" = server key (`s.id or s.name`) — MCP servers are config, not a
  DB entity; flagged for confirmation.
- All render-checked; admin restarted healthy.

### Decisions (resolved — Anthony, 2026-08-13)
1. **ID per entity:** People = integer `people.id`; Activity & Inbox = text
   `request_id`; other entities = their integer row id.
2. **Soft-delete = `deleted_at timestamptz NULL`** (NULL active, timestamp = deleted).
3. **Deleted rows: hide + restore** — default list shows only active; a "Show
   deleted" toggle reveals deleted rows with a **Restore** action.
4. **Button stays "Delete"** (soft under the hood).
5. **Sub-entity removals** (e.g. `person_identities` telegram mapping) stay a normal
   edit — not entity soft-delete.

## Requirements (from Anthony, 2026-08-13)
1. **Every data table shows an ID column** — the id of the datapoint: `people.id`
   (person id), `request_id` for Activity and Inbox, and the row id for every other
   entity table.
2. **The ID also appears on the edit and view screens** (not on the "new/create"
   screen — no id exists yet there).
3. **No hard delete, ever.** Every "delete" becomes a **soft delete**. Nothing is
   physically removed from a data-entity table via the admin UI.

## Current state (surveyed)
- No admin data table renders an ID column today.
- Hard deletes of a data entity: `people` in `main.py:227-232` (form POST) and
  `routes/people.py:184-196` (API DELETE). `person_identities` removal
  (`routes/people.py:63`) is a sub-edit; `hermes_session_mappings` DELETE
  (`settings.py:59`) is an operational reset, not an entity.
- Live-CRUD entity today: **people**. Companies / Knowledge / Memories / Tools /
  Automations / Job Credentials are UI-only shells (no backend yet).

## Proposed scope
- **A. ID columns (all tables, UI):** add an `ID` column to every data table, and
  show the id on each entity's view + edit screen. Cheap; do for all tables now
  (UI-only ones show the column even while empty, for consistency).
- **B. Soft-delete (people, now):** convert the two `people` hard-deletes to soft
  delete; hide soft-deleted rows from the default list; keep them restorable.
- **C. Pattern for the rest:** document the soft-delete + ID convention so each
  UI-only entity adopts it when its backend is built (no hard-delete ever ships).

## Open decisions for Anthony
1. **Which identifier is "the ID" per entity?**
   - People: integer `people.id` (the person id). Confirm — the URL uses email, but
     the shown/edit-screen ID would be the integer id.
   - Activity / Inbox: the text `request_id`.
   - Others: their integer row id. OK?
2. **Soft-delete mechanism (data-model):**
   - (a, recommended) add `deleted_at timestamptz NULL` to each entity — NULL =
     active, set = deleted, records *when*. Clean, uniform, restorable.
   - (b) reuse a `status`/`archived` flag. But `people.status` already means
     governance (allowed/blocked), so overloading it is muddy. → recommend (a).
3. **Default views hide soft-deleted rows?** Show only active by default, with a
   "Show deleted" toggle/filter and a **Restore** action on deleted rows? (recommend yes)
4. **Sub-entity removals** (e.g. removing a person's Telegram identity in
   `person_identities`): leave as a real edit (it's changing a mapping, not deleting
   a person), or also soft? (recommend: leave as edit — it's not entity deletion.)
5. **Label:** call the action "Delete" (soft under the hood) or rename to "Archive"
   in the UI? (recommend keep "Delete" so muscle memory holds, but it soft-deletes.)

## Acceptance
- Every admin data table has an ID column showing the entity's id / request_id.
- Each view + edit screen shows the id; create/new screens do not.
- No admin action issues `DELETE FROM` on a data entity; people "delete" sets the
  soft-delete marker; deleted rows are hidden by default and restorable.
- Convention documented so UI-only entities inherit it when built.

## Key files
- Templates: `templates/admin/*.html`, `templates/admin/people/{index,view,form}.html`
- Routes: `main.py` (people create/edit/delete), `routes/people.py`
- Schema: `admin_api/schema.sql` (soft-delete columns)

## Notes
- Governance rule alignment: this hardens the admin UI (no destructive deletes) and
  improves traceability (ids visible), consistent with the durable/audited posture.
