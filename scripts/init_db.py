#!/usr/bin/env python3
"""Create/seed the tracker SQLite DB from data.json (one-time bootstrap).

After this run, the DB is the source of truth: server.py writes rides into
it, scripts/export.py regenerates data.json, scripts/sync.sh pushes changes.
Idempotent: existing rows are kept (INSERT OR IGNORE).
"""

import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("TRANSIT_DB", Path.home() / "transit" / "transit.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS agencies (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  total_fleet INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fleet_ranges (
  id INTEGER PRIMARY KEY,
  agency_slug TEXT NOT NULL,
  lo INTEGER,
  hi INTEGER,
  prefix TEXT,
  type TEXT NOT NULL,
  count INTEGER NOT NULL,
  cars TEXT
);
CREATE TABLE IF NOT EXISTS rides (
  agency_slug TEXT NOT NULL,
  vehicle TEXT NOT NULL,
  vehicle_num INTEGER,
  line TEXT,
  date TEXT,
  PRIMARY KEY (agency_slug, vehicle)
);
"""


def main():
    data = json.loads((ROOT / "data.json").read_text())
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO agencies VALUES (?,?,?)",
            [(a["slug"], a["name"], a["total_fleet"]) for a in data["agencies"]],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO fleet_ranges VALUES (?,?,?,?,?,?,?,?)",
            [
                (r["id"], r["agency_slug"], r["lo"], r["hi"], r["prefix"],
                 r["type"], r["count"],
                 json.dumps(r["cars"]) if r.get("cars") else None)
                for r in data["ranges"]
            ],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO rides VALUES (?,?,?,?,?)",
            [(r["agency_slug"], r["vehicle"], r["vehicle_num"], r["line"], r["date"])
             for r in data["rides"]],
        )
        conn.commit()
        for t in ("agencies", "fleet_ranges", "rides"):
            print(f"{t}: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
        print(f"db: {DB}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
