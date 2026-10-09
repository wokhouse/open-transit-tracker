#!/usr/bin/env bash
# Export DB -> data.json + widgets, commit & push only if something changed.
# Called daily by a scheduled job. Silent no-op on days with no new rides.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/export.py
python3 scripts/make_widgets.py

# no-op until the repo has been pushed to GitHub at least once
if ! git rev-parse --verify -q origin/main >/dev/null; then
  echo "origin/main not found - push the repo first, sync skipped"
  exit 0
fi

CHANGED=$(git status --porcelain -- data.json widgets/)
if [ -z "$CHANGED" ]; then
  echo "no changes - nothing to commit"
  exit 0
fi

git add data.json widgets/
git commit -m "🚍 data update $(date -u +%Y-%m-%d)"
git push origin main
echo "pushed:"
echo "$CHANGED"
