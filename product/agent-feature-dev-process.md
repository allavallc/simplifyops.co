# Agent Feature-Dev Process (exact commands)

Concrete command flow for implementation work in this repo. The *principles* are in
`product/product-dev-guidelines.md`; the *rules/invariants* are in `AGENTS.md` +
`product/product-decisions/current-architecture.md`. This file is the **how**, adapted to our setup:
**native/systemd, no Docker, `main` is the trunk** (staging→prod split is pending — story-30).

## Flow

```bash
# 1. Start from latest main, on a story branch
git checkout main && git fetch origin -q && git reset --hard origin/main
git checkout -b story-<N>-<slug>

# 2. Write the full story first (product/stories/story-<N>-<slug>.md), implement code+tests together.

# 3. Gate — run in order, print the progress line, advance the (**HERE**) marker:
#    brooks audit > focused ruff > focused pytest > full ruff > full pytest > sync check > done
./.venv/bin/ruff check <changed paths>            # focused
./.venv/bin/pytest <changed tests> -q             # focused
bash scripts/agent_pre_push_check.sh              # full ruff + full pytest + sync check + divergence

# 4. Commit (code + tests together), end message with the Co-Authored-By trailer.
git add -A && git commit -m "...

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

# 5. Rebase onto origin/main, re-run the gate on the integrated result, then merge --no-ff:
git fetch origin -q && git rebase origin/main
git checkout main && git merge --no-ff story-<N>-<slug> && git push origin main

# 6. Post-push + cleanup
bash scripts/agent_post_push_check.sh "$(git rev-parse HEAD)"
git branch -d story-<N>-<slug>
# archive the story when done, then resync summaries:
git mv product/stories/story-<N>-<slug>.md product/stories/archive/
python3 scripts/sync_story_summaries.py generate && python3 scripts/sync_story_summaries.py check
```

## Progress line
Once in the gate/testing phase, print this and reprint it as each stage advances, marking the current
stage with `(**HERE**)`:

> `brooks audit > focused ruff > focused pytest > full ruff > full pytest > sync check > done`

## Rules
- **Branch per story off `main`;** merge only after the gate is green. Markdown-only changes may stay
  in the main checkout (blueprint), but this repo defaults to a branch when in doubt.
- **Coordinate before commit/merge/push** if another agent is active (`agent-coordination.md`).
- **Never push straight to prod;** `main` is the trunk today (staging/prod split = story-30).
- **Shared infra** (systemd restarts, `config.yaml`, DB, Telegram token) — coordinate first (rule 8).

## Known gaps (not yet automated)
- **CI** (GitHub Actions running ruff/pytest) — story 41.
- **Schemathesis** API gate — story 42.
- **Brooks** is invoked by an agent, not scripted/CI-enforced.
- **Staging→prod** split + deploy verification — story 30 (post-push check currently verifies local
  service health, not a separate deployed environment).
