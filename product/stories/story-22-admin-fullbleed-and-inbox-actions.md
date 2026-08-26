# Story 22 - Admin SPA: full-bleed content width + fix piled-up Inbox action buttons

## Status
**Proposed — awaiting approval.** No code changed yet.

## Problem
Two rendering issues in the admin SPA (`admin-client/`), reported by Anthony 2026-08-15:

1. **Massive empty side margins on the core content.** The content wrapper is capped and
   centered — `App.css`:
   ```css
   .page-shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
   ```
   On a wide/ultrawide monitor the tables pin to **1180px** and center, so the area right of
   the 240px sidebar is only ~50–70% used; the rest is dead space each side. Affects every
   page (all render inside the single `<main class="page-shell">`).

2. **Inbox action buttons pile up on top of each other.** The actions column is too narrow
   for three buttons:
   - `.actions-col { width: 220px }` (set only on the `<th>`, not the `<td>`).
   - Approve + Ignore + Reject ≈ **~232px** of buttons + 16px gaps + 32px cell padding
     ≈ **~264px needed** vs 220px available.
   - `.row-actions { flex-wrap: wrap }` then wraps the overflow → buttons stack vertically.
   Only `Inbox.tsx` uses `.row-actions` / `.actions-col`, so this fix is Inbox-scoped.

## Design decision (Anthony, 2026-08-15)
- **Content width:** full-bleed — content fills the area right of the sidebar minus a small
  gutter (24px each side); remove the 1180px cap. (No max-width; margins gone.)
- **Design-guide scope:** the admin SPA is **out of scope** for `design/style-guide.md` for
  now (that guide governs the marketing site only — dark editorial-brutalism, containers
  1280/960/720). So these fixes are pragmatic admin CSS, not guide-derived. Admin design
  governance to be decided separately.

## Proposed changes (config/CSS only — no new components)

### 1. Full-bleed content — `admin-client/src/App.css`
- `.page-shell` (width rule, ~L62): `width: min(1180px, calc(100% - 32px)); margin: 0 auto;`
  → `width: 100%;` (drop cap + auto-margins).
- `.page-shell` (padding rule, ~L145): `padding: 12px 0 40px;` → `padding: 12px 24px 40px;`
  (the 24px horizontal gutter; this later rule is what controls padding in the cascade).
- Mobile `@media (max-width: 720px)` (~L662): `.page-shell { width: min(100% - 20px, 1180px) }`
  → `width: 100%;` (padding supplies the gutter; keeps phones full-width, no double gutter).

### 2. Inbox action buttons — `admin-client/src/App.css`
- `.row-actions` (~L434): `flex-wrap: wrap;` → `flex-wrap: nowrap;` (force single line —
  the core fix; flex no longer wraps regardless of column width).
- `.actions-col` (~L440): `width: 220px;` → `width: 1%; white-space: nowrap;` (column shrinks
  to its content on the now-wide table; header label doesn't wrap). The `@media ≤980px`
  override `.actions-col { width: auto }` (~L655) is left as-is.

No change to `Inbox.tsx` required (nowrap on `.row-actions` is sufficient).

## Acceptance
- On a wide monitor, admin tables (Inbox, People, Activity, Tools, Memories, Settings, stubs)
  fill the space right of the sidebar with only a ~24px gutter each side — no large centered
  margins.
- Inbox Approve / Ignore / Reject render on a **single row**, not stacked.
- Mobile (≤720px) still renders the stacked "card" table layout with a sensible gutter; no
  horizontal scroll regression.
- Build succeeds (`npm run build` in `admin-client/`) and the SPA serves at `/app`.

## Key files
- `admin-client/src/App.css` — `.page-shell` (×2 + mobile), `.row-actions`, `.actions-col`.
- `admin-client/src/pages/Inbox.tsx` — the only consumer of the action-button classes.

## Notes
- Global blast radius verified: `.page-shell` width is one wrapper (all pages); `.row-actions`
  / `.actions-col` are Inbox-only; `.data-table` (8 pages) merely gets wider — intended.
- Per rule 2b, `design/` was checked first: it does **not** specify admin layout/table/button
  widths (marketing-site guide only), so the width was an explicit ask to Anthony, not an
  assumption.
