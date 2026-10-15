#!/usr/bin/env python3
"""Export the tracker SQLite DB -> data.json (canonical, stable ordering).

No timestamp drift: identical DB content must produce a byte-identical
data.json so the daily sync only commits real changes. The "updated"
field carries the date the data last changed: it is kept from the
existing data.json while the payload is unchanged, and re-stamped to
today (UTC) only when the payload actually differs.
"""

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DB = Path(os.environ.get("TRANSIT_DB", Path.home() / "transit" / "transit.db"))
OUT = Path(__file__).resolve().parent.parent / "data.json"


def _git_last_data_change():
    """UTC date of the last commit that touched data.json, or None.

    Fallback for files that predate the "updated" field, so the first
    export after the migration stamps the real last-change date.
    """
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d",
             "--", OUT.name],
            cwd=OUT.parent, capture_output=True, text=True)
        stamp = r.stdout.strip()
        return stamp if len(stamp) == 10 else None
    except OSError:
        return None


def resolve_updated(payload):
    """Return the data.json "updated" stamp for this payload.

    Keeps the existing stamp while the payload is unchanged; otherwise
    stamps today (UTC). server.py imports this, so both writers agree.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        old = json.loads(OUT.read_text())
    except (OSError, ValueError):
        return _git_last_data_change() or today
    old_updated = old.pop("updated", None)
    if old == payload:
        return old_updated or _git_last_data_change() or today
    return today


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

        payload = {
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

    data = {"updated": resolve_updated(payload), **payload}
    OUT.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    print(f"wrote {OUT} ({len(data['rides'])} rides, {len(data['agencies'])} agencies, updated {data['updated']})")


if __name__ == "__main__":
    main()
