# Data: the database and the fleets

## The database (source of truth)

- Path: `$TRANSIT_DB`, default `~/transit/transit.db`.
- Tables:
  - `agencies(slug, name, total_fleet)`
  - `fleet_ranges(id, agency_slug, lo, hi, prefix, type, count, cars)` —
    `cars` holds a JSON list for irregular numbering.
  - `rides` with primary key `(agency_slug, vehicle)`, plus `vehicle_num`,
    `line`, `date`.
- `scripts/init_db.py` bootstraps the DB from `data.json`. It is idempotent
  (`INSERT OR IGNORE`).
- Every `POST`/`DELETE /api/ride` re-exports `data.json` with
  byte-deterministic rules, so `scripts/sync.sh` commits only real changes.

## The `updated` stamp

`data.json` carries a top-level `"updated": "YYYY-MM-DD"` stamp: the date the
data last changed. `scripts/export.py::resolve_updated(payload)` owns the
rule:

- Keep the existing stamp while the payload is unchanged.
- Otherwise stamp today in UTC.
- A git-log fallback stamps files that predate the field.

`server.py` imports `resolve_updated`. Do not duplicate the rule. `index.html`
renders the value as the "last updated …" subtitle and rewrites the meta
description from it. The subtitle element is `hidden` until the data loads.

## Agency slugs (2026-10-10 merge)

Slugs: `sfmta` (MUNI Bus + Muni Metro merged into one SFMTA agency, 1093
fleet), `bart`, `caltrain`, `ac-transit`.

The old slugs `sfmta-bus` and `muni-metro` are legacy: `server.py` maps them
to `sfmta` on POST and DELETE. The DB migration ran in place (`UPDATE
agencies`/`fleet_ranges`/`rides` plus `DELETE` of the muni-metro agency row).
A backup sits at `~/transit/transit.db.bak-YYYYMMDD`.

## The fleet invariant

```
SUM(fleet_ranges.effective_count) == agencies.total_fleet   # per agency
```

`effective_count` is `len(cars)` when `cars` is set, else `count`. Check the
invariant after any fleet edit. All four agencies reconciled on 2026-10-11:
sfmta 1093, bart 1070, caltrain 161, ac-transit 687.

## Rides outside the ranges

Only 4 ridden vehicles fall outside `fleet_ranges`, and all 4 are retired:
sfmta 3597, 3723, 5698, and ac-transit 1726. No grid can place them. The
ranges exactly fill `total_fleet`, so `_fleet_cells` has no filler room. The
header counts will disagree with the grid marks until the ranges are fixed.

bart 4590 and 4727 are NOT retired. They are Phase 2 E-cars and they now sit
inside the 4001-4760 range (corrected in the 2026-10-11 audit).

## SFMTA historic streetcar ranges (added 2026-10-11)

sfmta `total_fleet` = 1093 (1033 bus/LRV + 60 streetcars).

Three ranges use a `cars` list (irregular numbering, the same mechanism as the
Caltrain KISS):

- PCC, 32 cars: 1006-1011, 1015, 1040, 1050-1053, 1055-1063, 1070-1080.
- Peter Witt Milan, 11 cars: 1807-1895, irregular.
- veteran/overseas, 17 cars: C-1, 1, 130, 151, 162, 189, 228, 233, 351, 496,
  578-J, 578, 737, 798, 913, 916, 952.

Source: Wikipedia "San Francisco Municipal Railway fleet" (it cites SFMTA
documents). Do NOT model the streetcars as a contiguous 1006-1055 block. That
was wrong.

## All-agency fleet audit (2026-10-11)

- **bart**: `total_fleet` 775 -> 1070. The Phase 2 (Core Capacity) E-cars
  continue the E-car numbering: 4466-4760 delivered as of Jan 2026 (bart.gov
  reports 1,070 cars received/certified; delivery paused near 4760 by a
  Dec-2025 US Customs Uyghur-forced-labor hold; 1,129 planned). Model one
  range 4001-4760 (760 E-cars) plus D-cars 3001-3310. The legacy A/B/C fleet
  is fully retired
  (Apr 2024). Do not model it.
- **ac-transit**: `total_fleet` 630 -> 687. Fixes: deleted the retired MCI
  6001-6079 range; corrected 6301-6335 to 6301-6336 (36); added Gillig
  1701-1750 (50, 2024) and New Flyer XHE60 2501-2509 (9, 2025-26 hydrogen).
  The actransit.org/ridership table is stale (Dec 2023, it sums to 630). The
  Wikipedia "AC Transit" Current Fleet table is the better source, but its
  asterisked Qty values (9*, 5*, 13*) are stale leftovers; the series ranges
  are authoritative. AC Transit board report 25-151 confirms 625 buses
  maintained during 2024 plus 50 Gillig final acceptance in 2025.
- **caltrain**: verified correct. 46 KISS cab cars (301-346) plus 115
  intermediate cars (3XY1/2/3/5/6, where XY is an odd cab pair = 23 sets).
  161 total.
- **sfmta**: verified correct at 1093. The wiki summary table matches all 13
  ranges. LRV4 stays 2001-2219: the 2220-2249 option was cancelled in 2025.

Source caches: `~/.hermes/cache/scratch/{act.fleet,bart.rolling,caltrain}.wiki`.
Fetch raw wikitext with
`curl 'https://en.wikipedia.org/w/index.php?title=X&action=raw'` — web_extract
fails on that URL, but curl works.
