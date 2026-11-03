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
fleet), `bart`, `caltrain`, `ac-transit`, `golden-gate-transit` (added
2026-10-16), `marin-transit` (added 2026-10-19), `vta` (added 2026-11-02).

The old slugs `sfmta-bus` and `muni-metro` are legacy: `server.py` maps them
to `sfmta` on POST and DELETE. The DB migration ran in place (`UPDATE
agencies`/`fleet_ranges`/`rides` plus `DELETE` of the muni-metro agency row).
A backup sits at `~/transit/transit.db.bak-YYYYMMDD`.

## The fleet invariant

```
SUM(fleet_ranges.effective_count) == agencies.total_fleet   # per agency
```

`effective_count` is `len(cars)` when `cars` is set, else `count`. Check the
invariant after any fleet edit. All agencies reconciled: sfmta 1093, bart
1070, caltrain 161, ac-transit 687, golden-gate-transit 124, marin-transit
82 (2026-10-19), vta 523 (2026-11-02).

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

## Golden Gate Transit (added 2026-10-16)

`golden-gate-transit`, `total_fleet` = 124. Three ranges:

- 924-955 (32) and 956-980 (25): MCI D4500CT 45ft coaches (2012/2015).
- 1901-1967 (67): Gillig Low Floor HEV 40ft hybrids (2019).

Do NOT model the 901-923 MCI D4500CT (2010) series: CPTDB lists it retired by
2025. The MTC FY2023-2028 SRTP counted 147 buses before that retirement; the
current Wikipedia infobox (124) matches the roster above. Sources: Wikipedia
"Golden Gate Transit", CPTDB Wiki roster, goldengate.org fleet history page.

## Marin Transit (added 2026-10-19)

`marin-transit`, `total_fleet` = 82. Twenty-one ranges, all of them the
active fixed-route revenue roster:

- 301 (1), ElDorado XHF 29ft (West Marin Stagecoach).
- Gillig BRT HEV: 1501-1504 29ft (4), 1505-1511 40ft (7), 1701-1710 40ft
  (10), 2001-2011 40ft (11), 2401-2404 35ft (4), 2405-2407 40ft (3).
- Gillig BRT 29ft diesel: 2601-2604 (4).
- Gillig Low Floor Plus EV 40ft: 2101-2104 (4).
- BYD K9S 40ft: 1801-1802 (2).
- ElDorado XHF: 1760-1761 29ft (2), 2160-2163 29ft (4), 1860-1861 35ft (2),
  2170-2171 35ft (2), 3062-3064 35ft (3), 3065-3069 35ft (5).
- Ford ElDorado cutaways: 1560-1561 F-550 Aero Elite 270 (2), 1680, 1880,
  1980 E-450 Aerotech (3), 2080-2088 E-450 Aerotech (9).

Do NOT model the paratransit roster (501-514, 601-605, 701-724, 801-807,
808-810, 1830-1833): Marin Access vans run by reservation, and no rider can
board them as a fixed-route vehicle. The retired transit-bus rows (550-559
D60LF, 3301-3307 DE35LF, the RTS-06 cars) stay out for the same reason as the
GGT 901-923 series.

Sources: CPTDB Wiki "Marin Transit" (Transit Bus Roster, Active) and the
series pages for 1505-1511 and 2601-2604. TransSee vehicle locations confirm
1509, 1505, 1501, 1701, 2010, 2080-2088, 2162, 2171, 2405, and 2603 in
2026-10 service. Marin Transit board report 2026-03-02 ("42 Gillig low-floor
buses, orders for nine more", "10 battery electric vehicles, almost 15% of the
fixed route fleet") agrees with the roster. The Wikipedia infobox ("about 105
vehicles for fixed route and demand response") mixes both rosters and is too
loose to model.

## VTA (added 2026-11-02)

`vta`, `total_fleet` = 523 (423 buses + 100 light-rail cars). Fourteen
ranges, the active fixed-route revenue roster:

- Gillig Hybrid 40ft: `0130–0194` (65) and `0195–0220` (25) as `cars` lists —
  the fleet numbers are zero-padded ("0130"), and `0200` never existed, so an
  lo–hi range would print wrong labels and a phantom cell. 3401–3496 (96;
  3493–3496 are a 2025 add-on to the 3401–3492 order), 4101–4138 (38),
  4211–4220 (10; 4201–4210 sold to Santa Cruz Metro), 4301–4329 (29),
  4401–4415 (15), 6201–6210 (10, suburban), 6401–6415 + 6417–6434 (33; 6416
  fire-destroyed 2020), 7401–7456 (56).
- New Flyer XDE60 Hybrid 40ft: 8301–8344 + 8346–8347 (46; 8345 retired).
- Light rail car 900–999 (100, Kinki Sharyo/Alstom 1999–2004).

Excluded, with reasons:

- The 2001–2002 diesel Gilligs (1002–1052, 2011–2021, 2022–2071, 2101–2123,
  2201–2256): the CPTDB 2026-10-11 capture shows 1002–1052 fully retired, and
  TransSee showed zero of 44 spot-checked old-series units in revenue on
  2026-11-02. CPTDB "Active" statuses for the 20xx/21xx/22xx pages lag
  reality; the series is gone.
- Proterra 7501–7505 and 9501–9505 (BE40): "Out of Service" in every 2026
  CPTDB capture, none in revenue on TransSee.
- Gillig BEB 5501–5535 (35 battery-electric, part of an order for 66; VTA
  ZEB Blueprint 2025-04): delivered but not in revenue service — none on
  TransSee 2026-11-02, and VTA says "we'll let you know when we put them into
  service". Add the range when they enter service.
- VTA Access paratransit roster: reservation-run, per the Marin precedent.
- 7437 IS part of the roster: the CPTDB 7401–7456 table lacks the row, but the
  unit was in revenue on TransSee 2026-11-02. Table extraction dropped it; the
  range keeps it.

Sources: CPTDB Wiki series pages via Wayback captures 2025-12 through
2026-10-11 (the live site Cloudflare-blocks curl; capture dates per series),
Wikipedia "Valley Transportation Authority" (LRV fleet "900–999, 100 in
service"), TransSee `fleetfind?a=vta` live spot checks 2026-11-02 (0140,
0160, 0194, 0195, 3401, 3404, 3493, 3494, 3496, 4101, 4211, 4215, 4220,
6201, 7401, 7437, 8301, 0902, 0995, 0996 seen in revenue; 0200, 6416, 8345,
all 44 old-diesel IDs, and 5501–5535 seen absent).

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
