#!/usr/bin/env bash
# Post-push check (story-38): confirm origin/main has <sha>; check services + admin health.
# Usage: agent_post_push_check.sh [<commit-sha>]   (defaults to HEAD)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

sha="${1:-$(git rev-parse HEAD)}"
git fetch origin -q || true
if git merge-base --is-ancestor "$sha" origin/main 2>/dev/null; then
  echo "origin/main contains ${sha:0:9} ✓"
else
  echo "WARNING: origin/main does NOT contain ${sha:0:9}"
fi

echo "== services =="
for s in simplifyops-admin simplifyops-gateway simplifyops-agent-runtime hindsight; do
  printf '  %-28s %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null || echo unknown)"
done

echo "== admin health =="
curl -s -o /dev/null -m 5 -w "  GET /health -> %{http_code}\n" http://127.0.0.1:3000/health \
  || echo "  admin unreachable"
