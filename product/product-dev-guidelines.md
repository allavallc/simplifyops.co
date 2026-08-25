# Product Development Guidelines (for LLMs working in this repo)

The day-to-day process for building in this repo. This is the **how**; the binding **rules** live in
two places and win over anything here if they disagree:

- **`AGENTS.md`** — governance rules (stories-first, no architecture without asking, no short-term
  fixes, the review gate, work-branch lifecycle).
- **`ops/current-architecture.md` → "Architectural rules"** — the binding architectural rules
  (API-first; server-rendered Jinja not React; no god-modules; one-way dependencies; single source
  of truth for settings; repo-owned/declared dependencies; test seams; local → staging → prod).

If a task would break an architectural rule, **stop and get an explicit decision recorded in a
story** (AGENTS.md rule 3). Do not work around it.

---

## 0. Before you build

1. **Read the graph.** `graphify update .` then read `graphify-out/GRAPH_REPORT.md` (or use
   `graphify query/path/explain`). It is the primary map — use it before grep/raw files.
2. **Read the architectural rules** in `ops/current-architecture.md`.
3. **Have a story.** All implementation needs a numbered story in `product/stories/`
   (`story-N-<slug>.md`) — written, planned, and **approved** before code. Numbers are permanent.
4. **Explain before acting** and, for non-trivial changes, ask before proceeding.

---

## 1. The pipeline (end to end)

```
story → plan → approval → work branch → code → logging → tests → commit (WIP)
      → rebase onto origin/main → brooks-review + brooks-audit (fix, re-run until clean)
      → focused ruff + pytest → full ruff + pytest → amend → push to STAGING
      → (later, deliberate) promote staging → prod → archive story → delete branch
```

Every step below is mandatory. "Green" only counts **after the rebase**, on the integrated result.

---

## 2. Build

- **Minimal code.** Write the least code that solves the problem. Prefer configuration over custom
  code. Don't add helpers/abstractions unless necessary. If a framework provides it, use that.
- **Follow the architectural rules.** In particular: business logic in the FastAPI layer exposed as
  `/api/*` JSON; admin UI as **Jinja** templates in `admin_api/templates/` (no React/SPA/build
  step); one responsibility per module; one-way dependencies; settings read through one accessor.
- **Match the surrounding code** — comment density, naming, idioms.
- **UI conforms to `design/`** (AGENTS.md rule 2b) — no improvisation; if anything is unspecified or
  conflicts, ask.

---

## 3. Logging

- Use the **repo-local logger** (`get_logger(...)`), not a host-global module and not bare `print`.
  Logging is per-repo (architectural rule 6).
- Log at the boundaries of each durable step (message intake, governance decision, work-item state
  transitions, outbound send, retries/dead-letter) with the **request/work-item id** so a message
  can be traced end to end through the flow in `ops/current-architecture.md`.
- Log enough to debug a failure without a rerun; never log secrets, tokens, or PII (SECURITY RULES
  in `CLAUDE.md`).

---

## 4. Test

Order matters — run the **static brooks gate first**, then the executable checks.

1. **brooks review gate (static — reads code + tests, doesn't run them):** run **both**
   `brooks-review` (diff) **and** `brooks-audit` (architecture) on the **rebased** branch. Iterate:
   fix findings and re-run until clean. An unresolved 🔴 **Critical** from either **blocks
   push/merge** — fix it, or record an explicit justification in the story's `## Review` section.
2. **Focused `ruff` + `pytest`** — scoped to what you changed.
3. **Full `ruff` + `pytest`** — `./.venv/bin/ruff check .` and the full suite; both must be green.

Config: `pyproject.toml` (`ruff` select `E9,F,I`; `pytest` `testpaths=["tests"]`). Write tests
**with** the code (rule 2 lifecycle), and give infrastructure boundaries **test seams** so units can
be tested with doubles (architectural rule 7).

**Testing-phase readout.** Once in the testing phase, print this status line and reprint it each
time you advance, marking the current stage with `(**HERE**)`:

> `brooks audit > fixing findings > focused ruff > focused pytest > full ruff > full pytest > done`

---

## 5. Fix

- Fix findings at the root — **no short-term workarounds** (AGENTS.md rule 4). If the right fix is
  bigger than the story, say so and hold; don't leave scaffolding.
- After fixing, **re-run the gate from the top** (brooks first, then ruff/pytest) — findings can
  reappear or move.

---

## 6. Commit

- Work on a **work branch off `main`**, named for the story: `story-N-<slug>` (never commit
  feature work to `main`). Non-feature housekeeping (docs, story archiving, `agent-coordination.md`)
  may go straight to `main`.
- **Commit WIP first**, then rebase (`git fetch origin && git rebase origin/main`), then run the
  gate on the rebased result, then **amend**. Committing first is what lets the rebase validate the
  *integrated* code so "green" can't be stale.
- Clear message: what changed and why. Include the co-author trailer your agent is configured to use
  (e.g. `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- Fill the story's **`## Review`** section before push: both brooks scores, each 🔴 Critical and how
  it was resolved/justified, and confirmation that focused + full `ruff`/`pytest` are green.

---

## 7. Push to staging

**Environments: local (this machine) → staging (GitHub) → prod (GitHub).**

- Develop and test **locally** on this machine.
- **Pushing to GitHub publishes to _staging_.** Verify on staging before anything goes further.
- **Promotion staging → prod is a separate, deliberate step** — do not push work straight to prod.

> ⚠️ **Pending — `story-30`.** The staging/prod split is **not wired yet**. Today GitHub Pages still
> publishes `main` to the prod domain `simplifyops.co`, and the control plane deploys by pull +
> `systemctl restart` on this pi. Until `story-30` lands, **treat any GitHub `main` push with
> production-level care.** When it lands, this section and AGENTS.md rule 10 get updated to the wired
> reality.

After a story is merged/promoted: **archive it** (`git mv product/stories/story-N-<slug>.md
product/stories/archive/`) and **delete the work branch** (local + remote).

---

## Quick checklist

- [ ] Graph read, architectural rules read, approved story exists
- [ ] Code is minimal and obeys the architectural rules; UI matches `design/`
- [ ] Repo-local logging at step boundaries with ids; no secrets/PII
- [ ] Committed WIP → rebased onto `origin/main`
- [ ] `brooks-review` + `brooks-audit` clean on the rebased branch (Criticals resolved/justified)
- [ ] Focused then full `ruff` + `pytest` green
- [ ] Story `## Review` filled; commit amended with co-author trailer
- [ ] Pushed to **staging** (not prod); `graphify update .` re-run if code changed
