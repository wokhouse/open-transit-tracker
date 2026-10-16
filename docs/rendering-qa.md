# Rendering verification and defect fixes

Check a rendering claim before you change the renderer. Vision reports false
defects. Pixels and SVG source do not.

## Paper, tractor holes, and cutouts

- `_paper` draws the tractor holes as EXPLICIT `<circle>` elements in the
  mask: one per row at `cx = tractor/2` and `cx = width - tractor/2`, 48px
  pitch. Do NOT reintroduce a tiled `<pattern>`. A pattern tiles from `x=0`,
  so the right strip needs `patternTransform` to phase it; a renderer that
  drops that attribute puts the right holes at the strip's inner edge plus a
  half-hole on the paper edge. The user saw exactly that on fungj.net while
  the deployed SVG was correct in Chrome (2026-10-15, fixed by 0e56f11).
  Reproduce the symptom by deleting `patternTransform` from an old card and
  rendering it: the right-strip red spans read 396-398 and 417-420 instead of
  405-411.
- Expected hole centers: 420px card 12/408, 690px card 12/678, 1080px desktop
  sheet 24/1056, 375px mobile sheet 12/363. The cards and both sheets use the
  mobile geometry (tractor 24, `hole_r` 3).
- `browser_vision` claimed the right holes sat off-center on a correct build.
  For alignment claims, trust the pixel scan over vision. Measure the strip
  edges on a BAND row: a paper-band row reads flat cream across the whole
  width and hides the strip boundary.
- Transparent holes (cutouts, a user requirement): `_paper` wraps the bands
  rect AND both tractor strip rects in ONE
  `<g mask="url(#paper-holes)">`. The mask is a white full-width rect plus
  explicit black circles. The bands rect must span the FULL sheet width
  underneath the strips. A bands rect clipped to the content area plus
  per-strip masks leaves a page-background hairline at each tear line. One
  mask over one unified paper layer is the only shape with no seam.
- Pitfall: the SVG default `fill` is black. Set the fills explicitly on the
  mask circles (black = hole). Never rely on an omitted fill to mean
  transparent.
- No `PAPER_EDGE` seam between the tractor strips and the paper. The user
  wants one continuous sheet: a shadow makes no sense when the border is
  attached.
- No backdrop anywhere (final, 2026-10-15; commit b3bb774 reverted the desk
  from 55517fb). `_paper(L, h)` takes no backdrop argument, and every surface
  keeps true transparent cutouts. The user rejected a painted desk: the
  fungj.net host frames the widget card with a drop shadow, so the paper edge
  reads without help from the hole colour. Accepted trade-off: on a host with
  no framing (a bare GitHub profile README is white in light mode),
  white-on-cream is 1.13:1 and the tractor edge goes faint (a dark desk would
  be 14:1). Do not re-add a backdrop unless she asks.

## Other geometry rules

- The stamp box width includes letter-spacing:
  `w = len(label) * (GLYPH_W + spacing) + 24`. Without the spacing term the
  red border is narrower than its text.
- Footer text wraps to the content width (`_footer_lines`); the height grows
  with the line count. Never let footer or header text run into the tractor
  margins.
- The agency header is ONE line: `NAME: pct% (count/total)` — bold name and
  colon, then the stats at `len(label) * (GLYPH_W + spacing)`. There are no
  separately positioned pct/count texts (the old `len(name)*10` advance math
  was wrong).
- The progress bar carries NO pct label after it. The label was redundant and
  it overflowed narrow sheets. Mobile `bar_w = int((content - 4) // GLYPH_W)`
  fills the content area. Divide by the float `GLYPH_W` (7.8), never
  `int(GLYPH_W)`, or the bar overflows.
- The bar is two rects (`_printed_bar`, shared by the sheet and all cards):
  `INK` fill for the ridden part, `INK_FAINT` solid fill for the unfilled
  part. The user replaced the dashed outline with the solid faint fill.
  Pitfall: `bar_w` in `_layout` is ALREADY a glyph count. Dividing by
  `GLYPH_W` again yields a bar 8x too short. After an encoding change, count
  the per-codepoint glyph occurrences in the regenerated SVG and compare with
  the expectation from the data (ridden = `round(pct/100 * bar_w)`). A raw
  count mismatch caught this bug once.
- Perforation tear line: draw it at `block_end + LINE` (inside the
  `PERF_ROWS` gap). Drawing at `y - PERF_ROWS*LINE + LINE` puts it three lines
  too high, over the last vehicle row.

## Verification methods

- Fastest cutout check (no screenshot): load the SVG same-origin, `drawImage`
  it onto a canvas at natural size, and read `getImageData` alpha. A true hole
  has alpha 0 at the hole center, alpha 255 on the paper beside it, and alpha
  255 at the tear-line columns (which proves no seam). A canvas composites
  nothing behind the image, so test ALPHA, not colour: a colour test reads
  every hole as a miss. Probe several surfaces in one `browser_console` call.
  An image below the fold reports `naturalWidth` 0 until you scroll it into
  view or re-create it with a cache-buster.
- Pixel route with a screenshot: sample the hole center and compare it with
  the page background sampled outside the sheet (the values must match
  exactly); count pure-black pixels inside the sheet (the opaque-hole
  signature must be 0); sample the tear-line columns (they must read paper
  colour). Map a screenshot px to the viewBox by locating the paper bbox first
  (first and last paper-coloured pixel along a row, then along a column). An
  assumed CSS offset is off by the page padding and reads holes as paper. To
  see an asset against a white host, open the asset URL directly: the browser
  page background is white, and the browser tool rejects `data:` URLs.
- Compute the expected feature coordinates from `params(width)` for the width
  the asset ACTUALLY renders at, before you sample. Both card tiers (420 and
  690 px) sit below `DESKTOP_BREAK=700`, so they use the mobile geometry —
  tractor 24, `hole_r` 3, hole centers at `x=12` and `width-12`. They do not
  use the desktop 48/5 with centers at 24. Sampling desktop coordinates on a
  card reads band/paper colour and looks exactly like missing holes.
- Any screenshot is a PNG on disk. Sample it with PIL, whichever stack
  produced it. `browser_vision` returns a `screenshot_path` that is usable for
  pixel measurement; take that path when the Paseo tab is gone
  (`browser_new_tab` recreates one) or when the tool returns
  `screenshot_no_frame`.
- Revert any temporary test style (for example a solid page background to
  prove transparency) in the same turn you confirm the fix. `git status
  --short` must then list only the intended files.
- QA method: screenshot at 390x844 (Paseo `browser_resize` +
  `browser_screenshot`), measure with PIL (hole centers, text spans against
  the content edges), then confirm with `vision_analyze` on crops. Vision can
  hallucinate clipping. Settle a claim with pixel spans before you change the
  renderer.
- The Paseo browser runs on the user's machine. Use the tailnet URL
  (`http://100.73.247.126:PORT`), never `127.0.0.1`. After you edit
  `index.html`, navigate with a fresh cache-buster query (`?v=N`). The browser
  caches the page and the new CSS silently never applies, which reads as a
  failed fix. Confirm that the change landed by checking a computed style
  before you measure geometry.

## The HTML record form on the grid

- The HTML record form obeys the 21px line grid like the SVG. Below a 560px
  viewport it stacks: `.rec-row { flex-direction: column; gap: 0 }` plus
  controls at `width: 100%` — one control per grid row. Chrome sizes
  `<select>` from UA metrics, not `line-height`: force
  `height: 21px; box-sizing: border-box`. The button height is a 19px line-box
  plus a 1px border on each side = 21px (the border uses the background
  colour, so it is invisible).
- The user wants one blank grid row between each form field and button:
  `.record select, .record button { margin-top: 21px }`. Use margins, not a
  flex `gap`, because an empty msg span is still a flex item and `gap` adds a
  phantom row. Pair it with `.msg:empty { display: none }`. The layout is
  label, input, blank, select, blank, button, msg = 7 rows, so
  `MOBILE_FORM_GAP_ROWS = 7`.
- Any dynamic status text the app injects into the grid must fit ONE row at
  the narrowest content width (~38 mono chars at 302px). The add confirmation
  is `added <veh> — <count>/<total> (<pct>%)`, with no date: the stamp already
  shows it. A wrapped msg row overflows the reserved block and breaks the
  grid.
- Form grid verification: measure a control's `getBoundingClientRect().top`
  minus the `#form-gap` element's rect top (NOT the gap's SVG `y` attribute —
  that misses the SVG's own page offset). Every control must show a `top_rel`
  that is a multiple of 21 (stacked and gapped: 0/21/63/105, msg 126) and a
  height of 21. The bands are a 42px pattern (cream 0-21, green 21-42)
  anchored at SVG `y=0`, so any multiple of 21 is a band boundary. Confirm
  with a PIL column scan of the screenshot before you trust vision: vision
  claimed misalignment on a pixel-perfect form.
