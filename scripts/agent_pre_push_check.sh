#!/usr/bin/env bash
# Pre-push gate (story-38): full ruff + full pytest + story-summary check + divergence report.
# Exit non-zero on any failure. Run before merging/pushing a story branch.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

RUFF="./.venv/bin/ruff"
PYTEST="./.venv/bin/pytest"
fail=0

echo "== full ruff =="
"$RUFF" check . || fail=1

echo "== full pytest =="
"$PYTEST" || fail=1

echo "== story-summary check =="
python3 scripts/sync_story_summaries.py check || fail=1

echo "== divergence vs origin/main =="
git fetch origin -q || true
ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo '?')
behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo '?')
echo "  ahead(local): ${ahead}  behind(origin): ${behind}"
echo "  commits to push:"
git log --oneline origin/main..HEAD 2>/dev/null | sed 's/^/    /'

if [ "$fail" -ne 0 ]; then
  echo "PRE-PUSH: FAILED"
  exit 1
fi
echo "PRE-PUSH: OK  (reminder: run brooks-audit for architecture-affecting changes)"
