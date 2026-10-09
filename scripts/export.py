#!/usr/bin/env python3
"""Export ~/transit/transit.db -> data.json (canonical, stable ordering).

No timestamp in the output: identical DB content must produce a
byte-identical data.json so the daily sync only commits real changes.
"""

import json
import sqlite3
from pathlib import Path

DB = Path.home() / "transit" / "transit.db"
OUT = Path(__file__).resolve().parent.parent / "data.json"


def main():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # fleet_ranges may carry an optional `cars` column: a JSON list of
        # explicit car ids for fleets whose numbering is irregular (not a
        # contiguous lo..hi range and not a numeric prefix). Emit it as a
        # real list when present, else null.
        range_cols = {r[1] for r in conn.execute("PRAGMA table_info(fleet_ranges)")}
        has_cars = "cars" in range_cols
        sel = "id, agency_slug, lo, hi, prefix, type, count" + \
              (", cars" if has_cars else "")
        ranges = []
        for r in conn.execute(
            f"SELECT {sel} FROM fleet_ranges ORDER BY agency_slug, id"
        ):
            d = {k: r[k] for k in r.keys() if k != "cars"}
            if has_cars and r["cars"] not in (None, ""):
                d["cars"] = json.loads(r["cars"])
            ranges.append(d)

        data = {
            "agencies": [
                dict(r)
                for r in conn.execute(
                    "SELECT slug, name, total_fleet FROM agencies ORDER BY slug"
                )
            ],
            "ranges": ranges,
            "rides": [
                dict(r)
                for r in conn.execute(
                    """SELECT agency_slug, vehicle, vehicle_num, line, date
                       FROM rides ORDER BY agency_slug, vehicle_num, vehicle"""
                )
            ],
        }
    finally:
        conn.close()

    OUT.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    print(f"wrote {OUT} ({len(data['rides'])} rides, {len(data['agencies'])} agencies)")


if __name__ == "__main__":
    main()
