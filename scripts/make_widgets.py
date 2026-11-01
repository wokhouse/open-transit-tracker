#!/usr/bin/env python3
"""Generate the SVG widgets from data.json, in the dot-printer style.

Static SVG (no JS) so it works inside a GitHub profile README.
The look comes from scripts/dotprinter.py — the same renderer the live
app serves at /api/sheet.svg. One component, both outputs.

Output:
  widgets/widget-<slug>.svg         small summary card, one agency
  widgets/widget-large-<slug>.svg   full dot-printer sheet, one agency
  widgets/widget-combined.svg       one progress bar per agency, all
                                    agencies on one card
  sheet.svg (repo root)             the whole-site sheet the static
                                   GitHub Pages copy of index.html shows
"""

import json
from pathlib import Path

import dotprinter as dp

ROOT = Path(__file__).resolve().parent.parent
WIDGETS = ROOT / "widgets"


def make_small(agency, data):
    """Small card: the same dot-printer paper as the sheet, at card size."""
    svg = dp.render_card(data, agency["slug"])
    out = WIDGETS / f"widget-{agency['slug']}.svg"
    out.write_text(svg)
    print(f"wrote {out.name}")


def make_large(agency, data):
    """Contribution-grid card: one square per vehicle, no numbers."""
    slug = agency["slug"]
    svg = dp.render_grid_card(data, slug)
    out = WIDGETS / f"widget-large-{slug}.svg"
    out.write_text(svg)
    n = sum(1 for r in data["rides"] if r["agency_slug"] == slug)
    print(f"wrote {out.name}  {n}/{agency['total_fleet']} (grid card)")


def make_combined(data):
    """Combined card: every agency's progress bar on one card."""
    svg = dp.render_combined_card(data)
    out = WIDGETS / "widget-combined.svg"
    out.write_text(svg)
    total = sum(a["total_fleet"] for a in data["agencies"])
    print(f"wrote {out.name}  {len(data['rides'])}/{total} (combined card)")


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Generate the SVG widgets from a data file.")
    ap.add_argument("--data", default=str(ROOT / "data.json"),
                    help="input data file (default: data.json)")
    args = ap.parse_args()

    WIDGETS.mkdir(exist_ok=True)
    data = json.loads(Path(args.data).read_text())

    for agency in data["agencies"]:
        slug = agency["slug"]
        make_small(agency, data)
        make_large(agency, data)
    make_combined(data)

    # the whole-site sheet: the read-only GitHub Pages copy of index.html
    # fetches this file (the local server renders it live at /api/sheet.svg).
    # sheet-mobile.svg is the same report at phone width, so narrow
    # viewports get readable type instead of a scaled-down desktop sheet.
    sheet = dp.render_sheet(data, footer=True)
    (ROOT / "sheet.svg").write_text(sheet)
    print("wrote sheet.svg  (full site, dot-printer sheet)")
    sheet_m = dp.render_sheet(data, footer=True, width=dp.MOBILE_W)
    (ROOT / "sheet-mobile.svg").write_text(sheet_m)
    print("wrote sheet-mobile.svg  (phone width, dot-printer sheet)")


if __name__ == "__main__":
    main()
