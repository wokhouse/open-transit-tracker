# open transit tracker developer guide

A static tracker of fleet coverage. Ride each vehicle in a fleet, then watch
the grid fill. One dot-printer sheet shows every fleet.

Repo: `/home/fungj/open-transit-tracker` (canonical copy, branch `main`).
Live page: https://wokhouse.github.io/open-transit-tracker/

Read `README.md` and the `docs/` files listed at the end before you change
code.

## Commands

Serve the app locally (systemd user service, `server.py` on 0.0.0.0:8321):

```bash
systemctl --user restart open-transit-tracker.service
systemctl --user status  open-transit-tracker.service
journalctl --user -u open-transit-tracker.service -n 50
```

Run it by hand instead of the service:

```bash
TRANSIT_DB=~/transit/transit.db python3 server.py
```

Record a ride:

```bash
curl -sX POST localhost:8321/api/ride -H 'content-type: application/json' \
  -d '{"agency_slug":"sfmta","vehicle":"5701"}'
```

Export, preview, and publish:

```bash
python3 scripts/export.py          # DB -> data.json (byte-deterministic)
python3 scripts/make_widgets.py    # write widgets/ + sheet*.svg locally
scripts/sync.sh                    # export, commit, push (no-op if unchanged)
```

Bootstrap the DB from `data.json` (idempotent, one-time):

```bash
python3 scripts/init_db.py
```

Inspect the DB (the `sqlite3` CLI is absent on this host):

```bash
python3 -c "import sqlite3;print(sqlite3.connect('/home/fungj/transit/transit.db').execute('select slug,total_fleet from agencies').fetchall())"
```

## Structure

| Path | Contents |
|---|---|
| `index.html` | The whole site. One dot-printer sheet, one section per agency. |
| `server.py` | Local server (stdlib `http.server`). Writable API + live sheet. |
| `scripts/dotprinter.py` | The single SVG renderer. Sheet, cards, and widgets. |
| `scripts/export.py` | DB -> `data.json`. Owns the `updated` stamp rule. |
| `scripts/make_widgets.py` | Writes `widgets/*.svg`, `sheet.svg`, `sheet-mobile.svg`. |
| `scripts/sync.sh` | Daily publish: export, commit, push. Silent no-op if unchanged. |
| `scripts/init_db.py` | Creates and seeds the SQLite DB from `data.json`. |
| `data.json` | The ONLY tracked data. Exported from the DB. |
| `.github/workflows/pages.yml` | Builds the widgets and deploys Pages. |
| `widgets/`, `sheet*.svg` | Generated build output. Gitignored. |

## Boundaries

- The DB at `$TRANSIT_DB` (default `~/transit/transit.db`) is the source of
  truth. `data.json` is exported output. `index.html` is the same file on
  every host.
- Only the local server answers `/api/config`. GitHub Pages does not, so the
  Pages copy stays read-only and shows no record form.
- `server.py` serves only `index.html`, `data.json`, `favicon.ico`, and
  `widgets/*.svg`. `scripts/` and `.git` return 404.
- Every `POST`/`DELETE /api/ride` re-exports `data.json` with
  byte-deterministic rules, so `sync.sh` commits only real changes.
- `scripts/export.py::resolve_updated()` owns the `updated` stamp rule.
  `server.py` imports it. Do not copy the rule.
- The daily job is the Hermes cron `transit-sync-daily` (script
  `~/.hermes/scripts/transit-sync.sh`, 9am, local delivery).
- `widgets/*.svg` come from the Pages workflow, not from git. Pages must have
  `build_type=workflow`, or the widgets 404. See `docs/ops.md`.

## MUST / MUST NOT

- MUST read `docs/rendering.md` before any change to `dotprinter.py`,
  `index.html`, or the widget look. It holds the design rules. Read
  `docs/rendering-qa.md` before you claim a visual defect.
- MUST restart `open-transit-tracker.service` after a `dotprinter.py` change.
  The server imports the renderer once at startup.
- MUST keep every function in a restyle: the record form, the hover tooltip,
  and the delete action. Never trade interactivity for the print look.
- MUST keep the 21px line grid. All line-heights, element heights, and paper
  padding are multiples of 21px.
- MUST route every widget through `dotprinter.py` (`render_card`,
  `render_grid_card`, `render_sheet`). Never hand-draw widget SVG in
  `make_widgets.py`.
- MUST measure before you claim a visual defect. Regenerate artifacts first,
  then verify against the SVG source or the pixels. Vision alone reports false
  defects.
- MUST verify a renderer change on the deployed artifact, not on the local
  file. See the ship path in `docs/ops.md`.
- MUST judge a widget look change against the `~/fungj.net` host page, which
  frames the card. The card has no backdrop.
- MUST kill `server.py` by PID from `ss -tlnp`.
- MUST NOT use `pkill -f server.py`. The pattern matches the calling shell.
- MUST NOT add `overflow-x: hidden` or `clip` to mask overflow.
- MUST NOT re-introduce a tiled `<pattern>` for the tractor holes.
- MUST NOT change a widget's content model in a restyle. The large widget
  stays squares-only; the numbered grid belongs to the live sheet.
- MUST NOT commit `widgets/*.svg` or `sheet*.svg`; they are generated.
- MUST NOT edit the Pages config or the remote DB without a stated reason.

## Docs

- `docs/rendering.md` — dot-printer architecture, design rules, widget tiers,
  mobile fit.
- `docs/rendering-qa.md` — verification methods and past defect fixes.
- `docs/ops.md` — sync chain, Pages, widget URLs, ship path, tailscale,
  gotchas.
- `docs/data-and-fleets.md` — DB schema, agency slugs, fleet audit, the
  range/total invariant.
