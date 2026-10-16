# Operations: sync, Pages, network

## Sync chain

1. Write a ride through the UI bar, or `POST /api/ride`
   (`{agency_slug, vehicle, date?, line?}`). The vehicle must contain a
   number. The date defaults to today UTC.
2. The cron job `transit-sync-daily` (no_agent script
   `~/.hermes/scripts/transit-sync.sh`, daily at 9am, deliver local) runs
   `scripts/sync.sh`: export, commit `🚍 data update YYYY-MM-DD`, push. The
   GH Pages workflow then regenerates the widgets and deploys.
3. The widgets are generated in CI. They are never tracked in git.

## GitHub Pages widget URLs

- URLs:
  `https://wokhouse.github.io/open-transit-tracker/widgets/widget-<slug>.svg`
  and `.../widgets/widget-large-<slug>.svg`.
- Known consumers: the GitHub profile README pattern in `README.md`, and the
  portfolio site `~/fungj.net` (`src/App.jsx` embeds
  `widget-large-sfmta.svg` in an `<img>`). A widget appearance change is a
  change on her portfolio page. Judge it against that host's background, and
  expect a stale copy there until the Pages TTL passes.
- Widget footer (both kinds): on the left, `updated M/D/YYYY` (from the
  `data.json` `updated` stamp, no leading zeros); on the right,
  `open transit tracker` as an `<a>` to the repo. The dotprinter card
  renderers draw the footer rows, not `make_widgets.py`. Note: inside a GitHub
  README the SVG is an `<img>`, so the link is not clickable there. It works
  when the SVG is inlined or opened directly.
- The URLs serve only when the Pages `build_type` is `workflow` (deploy the
  Actions artifact). Pitfall: with `build_type: legacy` (source branch
  `main/`), GitHub deploys the raw branch through Jekyll instead of the
  workflow's `_site` artifact. Git-tracked files (`index.html`, `data.json`)
  serve fine while generated files (`widgets/`) 404, even though the CI log
  shows them built and uploaded. Diagnose by probing one tracked URL against
  one generated URL: a tracked-200 / generated-404 split means the wrong
  `build_type`. Confirm with
  `gh api repos/wokhouse/open-transit-tracker/pages --jq .build_type`. Fix:
  `gh api -X PUT repos/wokhouse/open-transit-tracker/pages -f
  build_type=workflow`, then re-run the workflow
  (`gh workflow run pages.yml`). After the flip, trigger the workflow once:
  the old legacy deploy keeps serving until a new deploy lands. Fixed
  2026-10-11.

## Ship path for a renderer change

1. Commit on the worktree branch.
2. `git push origin <branch>:main`.
3. The Pages workflow regenerates `widgets/` (they are never in git).
4. `git pull --ff-only` in the canonical `/home/fungj/open-transit-tracker`,
   then `systemctl --user restart open-transit-tracker.service`. Without the
   restart the local app keeps serving the old renderer.

Verify the deployed artifact, not the local file:

```bash
curl -s 'https://wokhouse.github.io/open-transit-tracker/widgets/widget-large-<slug>.svg?cb=$RANDOM' | grep -c '23262b'
```

That count must be 0 (no backdrop on any surface), and the mask block must
contain the `paper-holes` mask. A host page that embeds the widget with an
uncache-busted `<img>` can keep showing the old SVG for the Pages TTL
(~10 min). Say so instead of assuming the fix failed.

## Tailscale

- The serve config needs root:
  `sudo tailscale serve --bg --https=443 http://127.0.0.1:8321`. The user runs
  the privileged steps.
- One-time convenience: `sudo tailscale set --operator=fungj`.
- Direct tailnet access works without serve: `http://100.73.247.126:8321`
  (the server binds 0.0.0.0).

## Gotchas

- The `sqlite3` CLI is not installed. Use the python3 `sqlite3` module.
- `pkill -f server.py` in a terminal command can SIGTERM the calling shell:
  the pattern matches the shell itself. Kill by PID from `ss -tlnp` instead.
- Retired predecessor: `/home/fungj/transit-tracker` (Next.js + rosters.json
  experiment) was retired 2026-10-10. Its service `transit-tracker.service` is
  disabled. Its SQLite DB still exists at
  `transit-tracker/app/data/transit-tracker.sqlite` if ever needed.
- Only 4 ridden vehicles fall outside `fleet_ranges` (retired: sfmta
  3597/3723/5698, ac-transit 1726). No grid can place them. See
  `data-and-fleets.md`.
