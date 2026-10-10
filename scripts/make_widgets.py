#!/usr/bin/env python3
"""Generate one SVG widget per agency from data.json.

Static SVG (no JS) so it works inside a GitHub profile README.
Dark/light aware via prefers-color-scheme media query.
Output: widget-<slug>.svg at repo root.
"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
WIDGETS = ROOT / "widgets"

# widget title overrides (data.json keeps the DB name)
TITLE_OVERRIDES = {
    "sfmta-bus": "MUNI Bus Fleet",
}

W, H = 420, 120
PAD = 20

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title {{ fill: #e6edf3; font: 600 15px -apple-system, 'Segoe UI', sans-serif; }}
    .stat {{ fill: #9198a1; font: 12.5px -apple-system, 'Segoe UI', sans-serif; }}
    .pct  {{ fill: #10b981; font: 700 20px -apple-system, 'Segoe UI', sans-serif; }}
    .bar-bg {{ fill: #21262d; }}
    .bar-fg {{ fill: #10b981; }}
    @media (prefers-color-scheme: light) {{
      .card {{ fill: #ffffff; stroke: #d0d7de; }}
      .title {{ fill: #1f2328; }}
      .stat {{ fill: #656d76; }}
      .bar-bg {{ fill: #eaeef2; }}
    }}
  </style>
  <rect class="card" x="0.5" y="0.5" width="{w_in}" height="{h_in}" rx="10"/>
  <text class="title" x="{pad}" y="34">{name}</text>
  <text class="pct" x="{w_pad}" y="35" text-anchor="end">{pct:.2f}%</text>
  <rect class="bar-bg" x="{pad}" y="52" width="{bar_w}" height="12" rx="6"/>
  <rect class="bar-fg" x="{pad}" y="52" width="{fill_w}" height="12" rx="6"/>
  <text class="stat" x="{pad}" y="92">{sub}</text>
  <text class="stat" x="{w_pad}" y="112" text-anchor="end">open transit tracker</text>
</svg>
"""


def range_label(r):
    if r.get("cars"):
        return f"{r['cars'][0]}\u2013{r['cars'][-1]} (irregular)"
    if r["prefix"] is not None:
        return f"{r['prefix']}-series"
    if r["lo"] == r["hi"]:
        return str(r["lo"])
    return f"{r['lo']}\u2013{r['hi']}"


def make_large(agency, rides, ranges):
    """GitHub-contribution-style grid: one square per vehicle, whole fleet, no numbers."""
    import math

    slug = agency["slug"]
    title = TITLE_OVERRIDES.get(slug, agency["name"])
    total = agency["total_fleet"]
    ridden_set = {r["vehicle_num"] for r in rides if r["vehicle_num"] is not None}

    cells = []  # True = ridden
    numbered = set()
    prefix_nums = set()
    explicit_nums = set()
    for rng in ranges:
        if rng.get("cars"):
            # explicit car list: one square per listed car, in list order
            for c in rng["cars"]:
                n = int("".join(ch for ch in str(c) if ch.isdigit()) or 0)
                cells.append(n in ridden_set)
                explicit_nums.add(n)
        elif rng["lo"] is not None and rng["hi"] is not None:
            for n in range(rng["lo"], rng["hi"] + 1):
                cells.append(n in ridden_set)
                numbered.add(n)
        else:
            matched = sum(
                1 for r in rides
                if r["vehicle_num"] is not None
                and str(r["vehicle_num"]).startswith(str(rng["prefix"]))
            )
            prefix_nums.update(
                r["vehicle_num"] for r in rides
                if r["vehicle_num"] is not None
                and str(r["vehicle_num"]).startswith(str(rng["prefix"]))
            )
            for i in range(rng["count"] or 0):
                cells.append(i < matched)
                if i < matched:
                    matched -= 1

    # vehicles outside every range get filler squares at the end
    leftover = total - len(cells)
    if leftover > 0:
        orphan = sum(
            1 for r in rides
            if r["vehicle_num"] is not None
            and r["vehicle_num"] not in numbered
            and r["vehicle_num"] not in prefix_nums
            and r["vehicle_num"] not in explicit_nums
        )
        for i in range(leftover):
            cells.append(i < orphan)

    COLS, CELL, GAP = 30, 9, 3
    PITCH = CELL + GAP
    rows = math.ceil(len(cells) / COLS)
    w = 40 + COLS * PITCH - GAP
    y0 = 58
    h = y0 + rows * PITCH - GAP + 28

    def rects(cls):
        out = []
        for i, ridden in enumerate(cells):
            if (cls == "on") == ridden:
                x = 20 + (i % COLS) * PITCH
                y = y0 + (i // COLS) * PITCH
                out.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2"/>')
        return "\n    ".join(out)

    pct = len(rides) / total * 100 if total else 0
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(f'{title}: {len(rides)}/{total} ({pct:.2f}%)')}">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title {{ fill: #e6edf3; font: 600 15px -apple-system, 'Segoe UI', sans-serif; }}
    .stat {{ fill: #9198a1; font: 12px -apple-system, 'Segoe UI', sans-serif; }}
    .pct  {{ fill: #10b981; font: 700 15px -apple-system, 'Segoe UI', sans-serif; }}
    .off {{ fill: #21262d; }}
    .on  {{ fill: #10b981; }}
    @media (prefers-color-scheme: light) {{
      .card {{ fill: #ffffff; stroke: #d0d7de; }}
      .title {{ fill: #1f2328; }}
      .stat {{ fill: #656d76; }}
      .off {{ fill: #ebedf0; }}
    }}
  </style>
  <rect class="card" x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10"/>
  <text class="title" x="20" y="30">{escape(title)}</text>
  <text class="pct" x="{w - 20}" y="30" text-anchor="end">{pct:.2f}%</text>
  <text class="stat" x="20" y="47">{len(rides)} / {total} ridden</text>
  <g>
    {rects("off")}
    {rects("on")}
  </g>
  <text class="stat" x="{w - 20}" y="{h - 11}" text-anchor="end">open transit tracker</text>
</svg>
"""
    out = WIDGETS / f"widget-large-{slug}.svg"
    out.write_text(svg)
    print(f"wrote {out.name}  {len(rides)}/{total}, {len(cells)} squares")


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Generate the SVG widgets from a data file.")
    ap.add_argument("--data", default=str(ROOT / "data.json"),
                    help="input data file (default: data.json)")
    args = ap.parse_args()

    WIDGETS.mkdir(exist_ok=True)
    data = json.loads(Path(args.data).read_text())
    rides_by_agency = {}
    for ride in data["rides"]:
        rides_by_agency.setdefault(ride["agency_slug"], []).append(ride)
    ranges_by_agency = {}
    for rng in data["ranges"]:
        ranges_by_agency.setdefault(rng["agency_slug"], []).append(rng)

    last_ride = max((r["date"] for r in data["rides"] if r["date"]), default=None)

    for agency in data["agencies"]:
        slug = agency["slug"]
        rides = rides_by_agency.get(slug, [])
        total = agency["total_fleet"]
        ridden = len(rides)
        pct = ridden / total * 100 if total else 0

        # ride dates are per-vehicle; agency-level "last ride" = newest ride date
        agency_last = max((r["date"] for r in rides if r["date"]), default=last_ride)

        fill_w = max(2, round(W - 2 * PAD) * min(pct, 100) / 100)
        sub = f"{ridden} / {total} vehicles"
        if agency_last:
            sub += f" \u00b7 last ride {agency_last}"

        title = TITLE_OVERRIDES.get(slug, agency["name"])
        svg = TEMPLATE.format(
            w=W,
            h=H,
            w_in=W - 1,
            h_in=H - 1,
            w_pad=W - PAD,
            pad=PAD,
            bar_w=W - 2 * PAD,
            fill_w=f"{fill_w:.1f}",
            name=escape(title),
            pct=pct,
            sub=escape(sub),
            label=escape(f"{title}: {ridden}/{total} ({pct:.2f}%)"),
        )
        out = WIDGETS / f"widget-{slug}.svg"
        out.write_text(svg)
        print(f"wrote {out.name}  {ridden}/{total} = {pct:.2f}%")

        make_large(agency, rides, ranges_by_agency.get(slug, []))


if __name__ == "__main__":
    main()
