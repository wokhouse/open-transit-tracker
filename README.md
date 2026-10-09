# open transit tracker

Static fleet-coverage tracker: ride every vehicle in the fleet, watch the grid fill in.

**Live page:** https://wokhouse.github.io/open-transit-tracker/

- `index.html` — the whole site. Fetches `data.json`, renders one fleet grid per agency (green = ridden, hover for ride date).
- `data.json` — exported from the on-Pi SQLite DB (`~/transit/transit.db`).
- `widget-<agency>.svg` — per-agency stat widgets; `widget-large-<agency>.svg` — contribution-graph-style fleet grids. Static SVG (no JS), dark/light aware. Embed in a GitHub profile README:

  ```markdown
  ![SFMTA fleet coverage](https://raw.githubusercontent.com/wokhouse/open-transit-tracker/main/widget-sfmta-bus.svg)
  ![SFMTA fleet grid](https://raw.githubusercontent.com/wokhouse/open-transit-tracker/main/widget-large-sfmta-bus.svg)
  ```

  Available: `sfmta-bus`, `muni-metro`, `bart`, `ac-transit`, `caltrain`.

## How it updates

A daily job on the Pi (`sleepy`) runs `scripts/sync.sh`:

1. `scripts/export.py` reads the SQLite DB → writes `data.json` (canonical ordering, no timestamps).
2. `scripts/make_widgets.py` regenerates the SVG widgets.
3. If nothing changed → exits silently. If it did → one commit (`🚍 data update YYYY-MM-DD`) and push. Pages redeploys automatically.

Logging rides stays wherever it always has: the Discord `/record-transit` slash command, the web app, or `transit.py add` on the Pi. This repo is read-only output.
