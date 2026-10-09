# open transit tracker

A static tracker of fleet coverage. Ride each vehicle in a fleet. Then see the grid fill.

**Live page:** https://wokhouse.github.io/open-transit-tracker/

## Files

- `index.html` — the full site. The page gets `data.json` and shows one fleet grid for each agency. A green cell shows a ride. Hover over a cell to see the ride date.
- `data.json` — the data for the site. A script exports this file from the tracker database.
- `widgets/widget-<agency>.svg` — the status widget for one agency.
- `widgets/widget-large-<agency>.svg` — the fleet grid for one agency, in the style of a contribution graph.

The widget files are static SVG. They use no JavaScript. They obey the dark color scheme and the light color scheme. You can put a widget in a GitHub profile README:

```markdown
![SFMTA fleet coverage](https://raw.githubusercontent.com/wokhouse/open-transit-tracker/main/widgets/widget-sfmta-bus.svg)
![SFMTA fleet grid](https://raw.githubusercontent.com/wokhouse/open-transit-tracker/main/widgets/widget-large-sfmta-bus.svg)
```

These agencies are available: `sfmta-bus`, `muni-metro`, `bart`, `ac-transit`, and `caltrain`.

## How the site changes

A task starts each day. The task does these steps:

1. `scripts/export.py` reads the tracker database and writes `data.json`. The sequence of the data is always the same.
2. `scripts/make_widgets.py` makes the SVG widgets again.
3. If there is no change, the task stops with no output. If there is a change, the task makes one commit, then pushes the commit. The title of the commit is `🚍 data update YYYY-MM-DD`. The live page changes automatically.

Record a ride with the Discord `/record-transit` command, with the web app, or with `transit.py add`. This repository is read-only output.
