#!/usr/bin/env python3
"""Serve open-transit-tracker locally with a write API.

GitHub Pages serves the same index.html without this server, so the page
stays read-only there. Locally the page probes /api/config, finds this
server, and shows the record-ride bar.

DB: $TRANSIT_DB (default ~/transit/transit.db). Every write re-exports
data.json with the same byte-deterministic rules as scripts/export.py, so
scripts/sync.sh only commits real changes.

Endpoints:
  GET  /                    site (index.html, data.json, widgets/*.svg)
  GET  /api/config          {"writable": true, "agencies": [...]}
  POST /api/ride            {agency_slug, vehicle, date?, line?}
  DELETE /api/ride?agency=..&vehicle=..   remove one ride (typo fix)
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get("TRANSIT_DB", Path.home() / "transit" / "transit.db"))
PORT = int(os.environ.get("TRANSIT_PORT", "8321"))

# Only these paths are served as static files. scripts/, .git/, dotfiles 404.
ALLOWED_STATIC = re.compile(r"^/(index\.html|data\.json|favicon\.ico|widgets/[\w-]+\.svg)?$")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def export_data():
    """Rewrite data.json from the DB. Same ordering as scripts/export.py."""
    conn = db()
    try:
        range_cols = {r[1] for r in conn.execute("PRAGMA table_info(fleet_ranges)")}
        has_cars = "cars" in range_cols
        sel = "id, agency_slug, lo, hi, prefix, type, count" + (", cars" if has_cars else "")
        ranges = []
        for r in conn.execute(f"SELECT {sel} FROM fleet_ranges ORDER BY agency_slug, id"):
            d = {k: r[k] for k in r.keys() if k != "cars"}
            if has_cars and r["cars"] not in (None, ""):
                d["cars"] = json.loads(r["cars"])
            ranges.append(d)
        data = {
            "agencies": [
                dict(r) for r in conn.execute(
                    "SELECT slug, name, total_fleet FROM agencies ORDER BY slug")
            ],
            "ranges": ranges,
            "rides": [
                dict(r) for r in conn.execute(
                    "SELECT agency_slug, vehicle, vehicle_num, line, date "
                    "FROM rides ORDER BY agency_slug, vehicle_num, vehicle")
            ],
        }
    finally:
        conn.close()
    (ROOT / "data.json").write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    return data


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/config":
            conn = db()
            try:
                agencies = [
                    dict(r) for r in conn.execute(
                        "SELECT slug, name, total_fleet FROM agencies ORDER BY slug")
                ]
                for a in agencies:
                    a["ridden"] = conn.execute(
                        "SELECT COUNT(*) c FROM rides WHERE agency_slug=?",
                        (a["slug"],)).fetchone()["c"]
            finally:
                conn.close()
            return self._json(200, {"writable": True, "agencies": agencies})
        if not ALLOWED_STATIC.match(path):
            return self.send_error(404)
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/ride":
            return self.send_error(404)
        try:
            n = int(self.headers.get("content-length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json(400, {"ok": False, "error": "bad json"})
        agency = str(payload.get("agency_slug", "")).strip()
        # old slugs from before the MUNI merge map onto the SFMTA agency
        agency = {"sfmta-bus": "sfmta", "muni-metro": "sfmta"}.get(agency, agency)
        vehicle = str(payload.get("vehicle", "")).strip()
        line = payload.get("line")
        date = payload.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        m = re.search(r"\d+", vehicle)
        if not m:
            return self._json(400, {"ok": False, "error": "vehicle must contain a number"})
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)):
            return self._json(400, {"ok": False, "error": "date must be YYYY-MM-DD"})
        conn = db()
        try:
            ag = conn.execute(
                "SELECT slug, name, total_fleet FROM agencies WHERE slug=?",
                (agency,)).fetchone()
            if not ag:
                return self._json(400, {"ok": False, "error": f"unknown agency {agency!r}"})
            cur = conn.execute(
                "INSERT OR IGNORE INTO rides (agency_slug, vehicle, vehicle_num, line, date) "
                "VALUES (?,?,?,?,?)",
                (agency, vehicle, int(m.group()), line, date))
            conn.commit()
            new = cur.rowcount == 1
            count = conn.execute(
                "SELECT COUNT(*) c FROM rides WHERE agency_slug=?",
                (agency,)).fetchone()["c"]
        finally:
            conn.close()
        export_data()
        total = ag["total_fleet"]
        return self._json(200, {
            "ok": True, "new": new, "agency_slug": agency, "vehicle": vehicle,
            "date": date, "count": count, "total": total,
            "pct": round(count / total * 100, 2) if total else 0,
        })

    def do_DELETE(self):
        q = parse_qs(urlparse(self.path).query)
        agency = (q.get("agency") or [""])[0]
        agency = {"sfmta-bus": "sfmta", "muni-metro": "sfmta"}.get(agency, agency)
        vehicle = (q.get("vehicle") or [""])[0]
        conn = db()
        try:
            cur = conn.execute(
                "DELETE FROM rides WHERE agency_slug=? AND vehicle=?",
                (agency, vehicle))
            conn.commit()
            removed = cur.rowcount
        finally:
            conn.close()
        if removed:
            export_data()
        return self._json(200, {"ok": True, "removed": removed})


def main():
    if not DB.exists():
        raise SystemExit(
            f"no DB at {DB} — run scripts/init_db.py first")
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"open-transit-tracker serving {ROOT} on :{PORT} (db: {DB})")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
