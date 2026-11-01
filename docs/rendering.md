# Dot-printer rendering

The site is one printed report. `scripts/dotprinter.py` draws it.

## One renderer

- `scripts/dotprinter.py` draws the whole sheet as one SVG: green-bar paper,
  tractor margins, agency headers, printed bar charts, vehicle grids.
- The server, the static `sheet.svg`, the small cards, the XL cards, and the
  widgets all call it. One style lives in one file. Change the look only
  there.
- `server.py` serves `GET /api/sheet.svg` from the live DB.
- Pitfall: `server.py` imports `dotprinter` once at startup. A renderer edit
  never reaches a running server. Restart the server process after a
  `dotprinter.py` change, then re-fetch `/api/sheet.svg?width=N` and grep for
  the new markup before you trust visual QA.
- `index.html` embeds that SVG. After any `POST`/`DELETE /api/ride` the page
  re-fetches the sheet, so the app stays reactive.
- Static Pages copy: `make_widgets.py` writes `sheet.svg` and
  `sheet-mobile.svg`. `pages.yml` copies `index.html`, `data.json`,
  `sheet.svg`, `sheet-mobile.svg`, and `widgets/` into `_site`. When the
  `api/config` probe 404s, `index.html` fetches `sheet.svg` relatively,
  renders read-only (no form), and relies on the native `<title>` elements
  baked into each ridden cell for the hover dates.
- Live tooltip: a click on a `[data-vehicle]` cell opens a fixed-position
  `.tip` (vehicle, agency, ridden date, delete button gated on `WRITABLE`).
  Delete calls `DELETE api/ride?...`, then re-fetches the sheet. The record
  form is the `ADD VEHICLE` row (vehicle-id input + agency select + `RECORD`
  button).
- User requirement for any restyle: keep ALL functionality — the record form,
  the hover tooltip, and delete. Never trade interactivity for the print look.

## Design rules (user-enforced)

- The `line-printer.html` prototype (worktree root, served ad hoc with
  `python3 -m http.server 8417`) was approved and integrated into
  `index.html` + the widgets. The prototype file may still sit untracked in a
  worktree. The authoritative design is `dotprinter.py`.
- Strict 21px vertical grid. All line-heights, element heights, and paper
  padding (42px top / 63px bottom) are multiples of 21px.
- All text is 13px monospace.
- The green bar background (21px pitch, `#e3ead9`) is always on. No toggle.
- The tractor-feed holes keep a continuous 48px pitch across the tear lines.
- The perforation dashed line sits at `top: 11px`, to match the fold shadow.
- Ridden cells use `background: var(--ink)` (white on black).
- The header holds only the h1 and the red rotated last-updated stamp. The
  jobline element was removed per user request.
- The tooltip delete button stays gated on `WRITABLE`. The user asked to
  un-gate it, then reversed: keep the gate.
- Record bar (prototype mode): when `api/config` 404s, `prototypeCfg(data)`
  builds the form from `data.json`. A submit edits in-memory only
  (`lastData.rides`; the message says "prototype: not saved"). The bar has NO
  dashed border. An uppercase `ADD VEHICLE` label row (`.rec-label`,
  line-height 21px, color `var(--ink)` — the same black as the body text, not
  `--ink-mid`) sits above the `.rec-row` controls. The bar uses
  `padding: 0; margin: 0 0 21px`, and its left edge aligns with the headings
  through the paper padding (no extra 1rem).

## Spacing edits

- The user specifies a vertical gap in grid rows ("remove 2 of the 3 lines
  between X and Y").
- Sum the padding, margin, and line-height values that compose the gap.
  Subtract exactly N x 21px. Keep every value a multiple of 21px.
- Verify by measuring the gap in rows: `(next.top - prev.bottom) / 21` with
  `browser_console`. Report the measured row count, not only the CSS diff.
- Grid verification: audit `getBoundingClientRect().top % 21` per element with
  `browser_console`. For CSS-transformed elements (the rotated stamp) use
  `offsetTop` accumulation instead — a transform skews the rect.
- The Paseo browser tab may not survive between turns (`browser_console` 400
  on `/tabs`). Re-run `browser_navigate` to the page first, then evaluate.

## Widget tiers (user-specified content models)

- Every widget tier renders through a function in `dotprinter.py`
  (`render_card`, `render_grid_card`, `render_sheet`) and reuses `_defs`,
  `_paper`, `_text`, and `_printed_bar`. Never hand-draw widget SVG in
  `make_widgets.py`. A hand-drawn card lacks the paper treatment and reads off
  style: no tractor holes, no grid alignment, mixed font sizes.
- Small card (`widgets/widget-<slug>.svg`, `render_card`, 420px wide):
  header row `NAME: pct% (count/total)`, printed bar, `last ride YYYY-MM-DD`
  row, footer row. The height is a multiple of 21px.
- XL card (`widgets/widget-large-<slug>.svg`, `render_grid_card`, 690px wide):
  the GitHub-contributions model — the whole fleet, NO vehicle numbers, one
  grid, no range headers. Approved encoding: two vehicles per glyph on the
  21px grid via stacked `<text>`. Every cell prints a faint `█` frame in
  `INK_FAINT` so that empty vehicles stay visible, then a solid `▀`, `▄`, or
  `█` in `INK` over the ridden halves. The user judges an encoding by
  contrast: solid black on light gray passes; textured or self-shading glyphs
  fail. Rejected: Braille dots (too low contrast), and the legacy-computing
  shade glyphs `🮐🮑🮒🮋` (low contrast; the shade-texture progress bar read as
  broken). When a glyph experiment is rejected, revert it completely —
  constants, font-stack additions, and regenerated artifacts.
- `_fleet_cells` builds the cells: the ranges in order. The
  `ranges == total_fleet` invariant leaves no filler room, so an out-of-range
  ridden vehicle is unplaceable in any grid. Fix `fleet_ranges`, not the
  renderer.
- The numbered per-range vehicle grid belongs ONLY to the live app sheet. A
  restyle must not change a widget's content model: when the XL card gained
  the numbered sheet, the user rejected it. The large widget is
  squares-only.
- Combined card (`widgets/widget-combined.svg`, `render_combined_card`,
  420px wide): every agency on one card. Title row `ALL AGENCIES`, a
  `TOTAL: pct% (count/total)` row with its printed bar (summed over all
  agencies), then per agency the small-card header row and printed bar,
  biggest coverage first. Bars-only: no grids, no vehicle numbers. Footer
  rows like the small card. CI copies it with `cp -r widgets`, so no
  workflow change is needed for a new widget file.

## Rendering pitfalls

- Visual QA: `browser_vision` reported broken columns and missing tractor
  holes in a generated widget. The file on disk was STALE from an earlier
  generator run. Regenerate artifacts (`python3 scripts/make_widgets.py`)
  before you trust a visual finding, and verify a claimed defect against the
  SVG source (grep element x-coords, check `<defs>`/`<pattern>` wiring) before
  you change the renderer.
- Header range/count labels (for example `301-349 6/46`) come from
  `fleet_ranges` in the DB. A label that disagrees with the drawn grid is a
  data problem, not a renderer bug.

## Mobile fit (width-aware rendering)

The sheet renders at the viewer's actual width. There is no scaling of a fixed
1080px sheet. `dotprinter.render(agency, width=...)` takes the target width,
and `params(width)` picks the geometry:

- `DESKTOP_BREAK = 700`.
- mobile (below 700): margin 30, tractor 24, `cell_w` 40, gap 2, `hole_r` 3.
  This fits an iPhone at 390px.
- desktop: margin 72, tractor 48, `cell_w` 44, gap 3, `hole_r` 5.

Details:

- `index.html` requests `api/sheet.svg?width=` at `clientWidth - 28`. The
  parameter is `width`, not `w`; `server.py` reads `qs.get("width")`. The
  value is clamped to 320..1080. The page scales only if the box is narrower
  than the request (a one-shot scrollbar correction). Live mode re-requests on
  resize (debounce 400ms, threshold 40px).
- Static Pages mode fetches the prebuilt `sheet-mobile.svg` under
  `matchMedia('(max-width: 700px)')`. `pages.yml` copies it into `_site`.
  `make_widgets.py` writes both sheets.
- `server.py` clamps the width parameter to 320..1080.
- `sheet*.svg` are gitignored build output.
- Column headers wrap onto multiple lines when they are too wide for the
  content area (`_wrap_text` plus the multi-line header layout in
  `_agency_block`).
- Do not add `overflow-x: hidden` or `clip` masking rules. They hide real
  overflow. The user removed them in commit fcc7068.
