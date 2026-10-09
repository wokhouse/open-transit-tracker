#!/usr/bin/env bash
# Export the tracker DB -> data.json, commit & push only if the data changed.
# The SVG widgets are NOT built here. The "Build and deploy" workflow
# (.github/workflows/pages.yml) regenerates them from data.json at deploy time.
# Silent no-op on days with no new rides.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/export.py

# no-op until the repo has been pushed to GitHub at least once
if ! git rev-parse --verify -q origin/main >/dev/null; then
  echo "origin/main not found - push the repo first, sync skipped"
  exit 0
fi

if [ -z "$(git status --porcelain -- data.json)" ]; then
  echo "no changes - nothing to commit"
  exit 0
fi

git add data.json
git commit -m "🚍 data update $(date -u +%Y-%m-%d)"
git push origin main
echo "pushed data.json"
