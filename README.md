# open transit tracker

A static tracker of fleet coverage. Ride each vehicle in a fleet. Then see the grid fill.

**Live page:** https://wokhouse.github.io/open-transit-tracker/

## Files

- `index.html` — the full site. The page gets `data.json` and shows one fleet grid for each agency. A green cell shows a ride. Hover over a cell to see the ride date.
- `data.json` — the data for the site. This file is the only tracked data. A script exports it from the tracker database.
- `.github/workflows/pages.yml` — the build task. The task makes the SVG widgets from `data.json`, then publishes the site to GitHub Pages.

The widget files are not in the repository. The build task makes them. The widgets are static SVG. They use no JavaScript. They obey the dark color scheme and the light color scheme. You can put a widget in a GitHub profile README:

```markdown
![SFMTA fleet coverage](https://wokhouse.github.io/open-transit-tracker/widgets/widget-sfmta.svg)
![SFMTA fleet grid](https://wokhouse.github.io/open-transit-tracker/widgets/widget-large-sfmta.svg)
```

These agencies are available: `sfmta` (Muni bus, trolleybus, and Metro), `bart`, `ac-transit`, and `caltrain`. To make the widgets before a push, run `python3 scripts/make_widgets.py`. The script writes them to `widgets/`.

## How the site changes

A task starts each day. The task does these steps:

1. `scripts/export.py` reads the tracker database and writes `data.json`. The sequence of the data is always the same.
2. If there is no change, the task stops with no output. If there is a change, the task makes one commit, then pushes the commit. The title of the commit is `🚍 data update YYYY-MM-DD`.
3. The push starts the build task. The build task makes the widgets and publishes the new site. The live page changes automatically.

Record a ride with the Discord `/record-transit` command, with the web app, or with `transit.py add`. This repository is read-only output.
