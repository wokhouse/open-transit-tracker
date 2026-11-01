#!/usr/bin/env python3
"""The dot-printer sheet as one shared SVG renderer.

One component, three outputs:
  - scripts/make_widgets.py writes the sheet SVGs for GitHub Pages
    (widgets/widget-<slug>.svg, widgets/widget-large-<slug>.svg,
    sheet.svg, and sheet-mobile.svg).
  - server.py serves the same SVG at /api/sheet.svg for the live app,
    at a width the page picks from the viewport.

The page (index.html) draws only the interactive chrome over the sheet:
the add-vehicle form, the ride tooltip, and the delete button. The sheet
itself is static print: green-bar continuous-feed paper, tractor-feed
margins, perforated tears between agency reports, and a LAST UPDATED
stamp.

Geometry follows the line-printer prototype: everything vertical is a
multiple of the 21px line grid. Text is 13px monospace. The bar chart is
printed with block glyphs, like a line printer would do it.

The layout is width-driven (see _layout). Width >= 700 renders the
desktop sheet with the exact original geometry. Narrow widths render a
real mobile sheet: narrower tractor strips, more grid columns per row of
content that fits, and wrapped range headers. The page fetches the width
that matches its viewport, so the printout stays readable instead of
scaled down.
"""

import math
from xml.sax.saxutils import escape

# ---- the grid: one print line is 21px, one text size is 13px ----
LINE = 21
FONT_SIZE = 13
GLYPH_W = FONT_SIZE * 0.6          # monospace advance width
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

# ---- print-shop palette (same values as the line-printer prototype) ----
PAPER = "#f6f3e8"
BAND = "#e3ead9"
INK = "#26251f"
INK_MID = "#6f6a5c"
INK_FAINT = "#b3ad9c"
RED = "#b3382b"
PAPER_EDGE = "#e7e2d2"

# ---- desktop sheet layout (all multiples of LINE) ----
SHEET_W = 1080
MOBILE_W = 375                     # the width the page requests on phones
DESKTOP_BREAK = 700                # widths below this get the mobile layout

# record-form gap: the live app overlays its HTML form here.
FORM_GAP_ROWS = 4
# mobile form stacks one control per row with one blank grid row between
# fields: label, input, blank, select, blank, button, msg = 7 rows
MOBILE_FORM_GAP_ROWS = 7

# perforated tear: blank rows above and below a tear line
PERF_ROWS = 3

TOP_PAD = 42                       # paper padding above the title


def _layout(width):
    """All horizontal geometry, derived from the sheet width."""
    if width >= DESKTOP_BREAK:
        return dict(
            width=width, tractor=48, margin=72,
            content=width - 2 * 72,
            cell_w=44, cell_gap=3, cols=16, bar_w=60,
            gap_rows=FORM_GAP_ROWS, hole_r=5,
        )
    margin, tractor, cell_w, cell_gap = 30, 24, 40, 2
    content = width - 2 * margin
    return dict(
        width=width, tractor=tractor, margin=margin, content=content,
        cell_w=cell_w, cell_gap=cell_gap,
        cols=(content + cell_gap) // (cell_w + cell_gap),
        bar_w=max(10, int((content - 4) // GLYPH_W)),
        gap_rows=MOBILE_FORM_GAP_ROWS, hole_r=3,
    )


def _tw(s):
    """Approximate rendered width of monospace text."""
    return len(str(s)) * GLYPH_W


def num(v):
    """Vehicle number from a label like '5701' or 'KF-212'; None if absent."""
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return int(digits) if digits else None


def range_label(r):
    if r.get("prefix") is not None:
        return f"{r['prefix']}-series"
    if r.get("cars"):
        return f"{r['cars'][0]}\u2013{r['cars'][-1]} (irregular)"
    if r["lo"] == r["hi"]:
        return str(r["lo"])
    return f"{r['lo']}\u2013{r['hi']}"


def group_by_slug(rows):
    out = {}
    for row in rows:
        out.setdefault(row["agency_slug"], []).append(row)
    return out


def sort_agencies(data):
    """Agencies biggest-coverage-first, same rule as the page JS."""
    rides_by = group_by_slug(data["rides"])
    agencies = [dict(a) for a in data["agencies"]]
    for a in agencies:
        n = len(rides_by.get(a["slug"], []))
        a["_pct"] = n / a["total_fleet"] * 100 if a["total_fleet"] else 0.0
    agencies.sort(key=lambda a: -a["_pct"])
    return agencies


def _text(x, y, s, *, fill=INK, weight="normal", anchor="start",
          spacing=None, family=MONO):
    attrs = f' x="{x}" y="{y}" fill="{fill}" text-anchor="{anchor}"'
    if weight != "normal":
        attrs += f' font-weight="{weight}"'
    if spacing:
        attrs += f' letter-spacing="{spacing}"'
    return (f'<text class="t"{attrs} xml:space="preserve">'
            f'{escape(str(s))}</text>')


def _wrap(s, max_w):
    """Split text at spaces so every line is at most max_w wide."""
    s = str(s)
    if _tw(s) <= max_w:
        return [s]
    lines, cur = [], ""
    for word in s.split(" "):
        cand = f"{cur} {word}".strip()
        if _tw(cand) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _defs(L):
    return f"""  <defs>
    <style>
      .t {{ font: {FONT_SIZE}px {MONO}; }}
      .t.bold {{ font-weight: 700; }}
    </style>
    <pattern id="bands" width="1" height="{LINE * 2}" patternUnits="userSpaceOnUse">
      <rect width="1" height="{LINE}" fill="{PAPER}"/>
      <rect y="{LINE}" width="1" height="{LINE}" fill="{BAND}"/>
    </pattern>
  </defs>"""


def _paper(L, h):
    """Paper bands plus the two tractor strips, as one continuous sheet.

    The strip holes are real cutouts: what is behind the paper shows
    through them. One mask punches both strips out of the whole paper
    group. The mask cannot be per-strip - the bands rect must run full
    width under the strips, or the strip/paper seam leaks the background
    as a hairline.
    """
    w = L["width"]
    t = L["tractor"]
    r = L["hole_r"]
    # Explicit circles, not a tiled pattern. A pattern needs
    # patternTransform to line the right strip's holes up with the left
    # strip, and renderers that ignore that attribute put the right
    # holes at the paper edge instead of in the strip.
    holes = []
    cy = 24
    while cy - r < h:
        for cx in (t / 2, w - t / 2):
            holes.append(f'      <circle cx="{cx:g}" cy="{cy}" r="{r}" fill="#000"/>')
        cy += 48
    return (
        '  <defs>\n'
        + f'    <mask id="paper-holes" maskUnits="userSpaceOnUse" x="0" y="0"'
          f' width="{w}" height="{h}">\n'
          f'      <rect width="{w}" height="{h}" fill="#fff"/>\n'
          + "\n".join(holes) + "\n"
          + f'    </mask>\n'
          '  </defs>\n'
          '  <g mask="url(#paper-holes)">\n'
          f'    <rect width="{w}" height="{h}" fill="url(#bands)"/>\n'
          f'    <rect width="{t}" height="{h}" fill="{PAPER}"/>\n'
          f'    <rect x="{w - t}" width="{t}" height="{h}" fill="{PAPER}"/>\n'
          '  </g>')


def _header(L, y, updated):
    """Title + optional LAST UPDATED stamp. Returns (svg, next_y)."""
    cx = L["width"] // 2
    out = [_text(cx, y + 15, "* OPEN TRANSIT TRACKER *",
                 weight="bold", anchor="middle", spacing="1.6")]
    y += LINE
    if updated:
        y += LINE  # blank row between title and stamp
        label = f"last updated {updated}"
        spacing = 1.3
        # the box must cover the letter-spacing too, or the text
        # overflows the border
        w = round(len(label) * (GLYPH_W + spacing)) + 24
        x0 = cx - w // 2
        out.append(
            f'  <g transform="rotate(-3 {cx} {y + LINE / 2})" opacity="0.8">'
            f'<rect x="{x0}" y="{y + 2}" width="{w}" height="{LINE - 4}" '
            f'rx="4" fill="none" stroke="{RED}" stroke-width="2"/>'
            + _text(cx, y + 15, label.upper(), fill=RED, weight="bold",
                    anchor="middle", spacing=str(spacing))
            + "</g>")
        y += LINE
    return "\n".join(out), y + LINE


def _printed_bar(L, y, pct):
    on = round(min(pct, 100) / 100 * L["bar_w"])
    x = L["margin"]
    on_w = on * GLYPH_W
    out = []
    if on:
        out.append(f'  <rect x="{x}" y="{y + 4}" width="{on_w:.1f}" '
                   f'height="{LINE - 8}" fill="{INK}"/>')
    if L["bar_w"] - on:
        out.append(f'  <rect x="{x + on_w:.1f}" y="{y + 4}" '
                   f'width="{(L["bar_w"] - on) * GLYPH_W:.1f}" height="{LINE - 8}" '
                   f'fill="{INK_FAINT}"/>')
    return "\n".join(out), y + LINE


def _grid(L, y, cells, ridden_map, agency):
    """Vehicle cells: plain text when not ridden, reversed block when ridden.

    Ridden cells carry data-* attributes (the live app wires its tooltip
    and delete button to them) and an SVG <title> (native hover tooltip,
    also what a static README reader sees).
    """
    out = []
    for i, (label, n) in enumerate(cells):
        r, c = divmod(i, L["cols"])
        x = L["margin"] + c * (L["cell_w"] + L["cell_gap"])
        cy = y + r * LINE
        ride = ridden_map.get(n) if n is not None else None
        if ride:
            tip = escape(f'{ride["vehicle"]} \u2014 ridden '
                         f'{ride.get("date") or "unknown date"}')
            out.append(
                f'  <rect x="{x}" y="{cy}" width="{L["cell_w"]}" height="{LINE}" '
                f'fill="{INK}" style="cursor:pointer" '
                f'data-vehicle="{escape(str(ride["vehicle"]))}" '
                f'data-agency="{escape(agency["slug"])}" '
                f'data-agency-name="{escape(agency["name"])}" '
                f'data-date="{escape(ride.get("date") or "")}">'
                f'<title>{tip}</title></rect>')
            out.append(_text(x + L["cell_w"] / 2, cy + 15, label, fill=PAPER,
                             weight="bold", anchor="middle"))
        else:
            out.append(_text(x + L["cell_w"] / 2, cy + 15, label, fill=INK_FAINT,
                             anchor="middle"))
    rows = math.ceil(len(cells) / L["cols"]) if cells else 0
    return "\n".join(out), y + rows * LINE


def _range_header(L, y, rng, ridden_in, denom):
    """Range title line(s). Wraps onto more lines when the text is too
    wide for the sheet. Returns (svg, next_y)."""
    type_s = str(rng["type"])
    range_s = range_label(rng)
    count_s = f"{ridden_in}/{denom}"
    right = L["width"] - L["margin"]
    if _tw(type_s) + 16 + _tw(range_s) + 12 + _tw(count_s) <= L["content"]:
        out = [_text(L["margin"], y + 15, type_s, weight="bold"),
               _text(L["margin"] + len(type_s) * 10 + 16, y + 15,
                     range_s, fill=INK_MID),
               _text(right, y + 15, count_s, fill=INK_MID, anchor="end")]
        return "\n".join(out), y + LINE
    # narrow sheet: type on its own wrapped line(s), count right-aligned
    # on the first line, range label on the line below
    lines = _wrap(type_s, L["content"] - _tw(count_s) - 12)
    out = []
    for i, ln in enumerate(lines):
        out.append(_text(L["margin"], y + 15, ln, weight="bold"))
        if i == 0:
            out.append(_text(right, y + 15, count_s, fill=INK_MID,
                             anchor="end"))
        y += LINE
    for ln in _wrap(range_s, L["content"]):
        out.append(_text(L["margin"], y + 15, ln, fill=INK_MID))
        y += LINE
    return "\n".join(out), y


def _agency_block(L, y, agency, ranges, rides):
    """One agency report. Returns (svg, next_y)."""
    ridden_map = {}
    for r in rides:
        n = num(r["vehicle"])
        if n is not None:
            ridden_map[n] = r
    total = agency["total_fleet"]
    count = len(rides)
    pct = count / total * 100 if total else 0.0

    label = f"{agency['name'].upper()}: "
    out = [_text(L["margin"], y + 15, label, weight="bold", spacing="1.0"),
           _text(L["margin"] + len(label) * (GLYPH_W + 1.0), y + 15,
                 f"{pct:.2f}% ({count}/{total})")]
    y += LINE
    bar, y = _printed_bar(L, y, pct)
    out.append(bar)

    for rng in ranges:
        y += LINE  # blank row before each range
        cells = []
        if rng.get("cars"):
            for c in rng["cars"]:
                cells.append((str(c), num(c)))
        elif rng["lo"] is not None and rng["hi"] is not None:
            for n in range(rng["lo"], rng["hi"] + 1):
                cells.append((str(n), n))
        ridden_in = sum(1 for _, n in cells if n in ridden_map)
        denom = rng.get("count") if rng.get("count") is not None else len(cells)

        hdr, y = _range_header(L, y, rng, ridden_in, denom)
        out.append(hdr)
        if not cells:
            out.append(_text(L["margin"], y + 15,
                             f"{ridden_in} of {denom} ridden", fill=INK_MID))
            y += LINE
            continue
        grid, y = _grid(L, y, cells, ridden_map, agency)
        out.append(grid)

    return "\n".join(out), y


def _perf(L, y):
    """Perforated tear: fold shadow above, dashed line at the crease."""
    return (f'  <rect x="0" y="{y}" width="{L["width"]}" height="11" '
            f'fill="black" opacity="0.06"/>\n'
            f'  <line x1="12" y1="{y + 11}" x2="{L["width"] - 12}" y2="{y + 11}" '
            f'stroke="rgba(62,50,31,0.45)" stroke-dasharray="4 4"/>')


FOOTER_TEXT = "*** end of report *** \u00b7 data auto-updates daily"
SOURCE_URL = "https://github.com/wokhouse/open-transit-tracker"


def _footer_lines(L):
    """Footer as centered lines that fit the sheet: each line is a list
    of (text, link) segments."""
    if _tw(FOOTER_TEXT) + 10 + _tw("source") <= L["content"]:
        return [[(FOOTER_TEXT, None), ("source", SOURCE_URL)]]
    lines = [[(t, None)] for t in _wrap(FOOTER_TEXT, L["content"])]  # type: ignore
    lines.append([("source", SOURCE_URL)])  # type: ignore
    return lines


def _footer(L, y):
    cx = L["width"] // 2
    out = []
    for i, line in enumerate(_footer_lines(L)):
        body = " · ".join(
            f'<a href="{link}">{escape(t)}</a>' if link else escape(t)
            for t, link in line)
        out.append(f'  <text class="t" x="{cx}" y="{y + i * LINE + 15}" '
                   f'fill="{INK_MID}" text-anchor="middle" '
                   f'xml:space="preserve">{body}</text>')
    return "\n".join(out)


def render_sheet(data, slug=None, form_gap=False, footer=False,
                 width=SHEET_W):
    """Render the whole dot-printer sheet as one standalone SVG string.

    slug=None renders every agency, biggest coverage first. A slug renders
    that one agency only (the README widget). form_gap reserves blank rows
    after the stamp (marked with id="form-gap") where the live app
    overlays its HTML record form. footer adds the end-of-report line.
    width picks the layout: >= 700 is the desktop sheet, below that the
    mobile sheet.
    """
    L = _layout(width)
    rides_by = group_by_slug(data["rides"])
    ranges_by = group_by_slug(data["ranges"])
    agencies = sort_agencies(data)
    if slug is not None:
        agencies = [a for a in agencies if a["slug"] == slug]

    # pass 1: measure the sheet height
    y = TOP_PAD
    _, y = _header(L, y, data.get("updated"))
    if form_gap:
        y += L["gap_rows"] * LINE
    for i, a in enumerate(agencies):
        if i:
            y += PERF_ROWS * LINE
        _, y = _agency_block(L, y, a, ranges_by.get(a["slug"], []),
                             rides_by.get(a["slug"], []))
    if footer:
        y += LINE + len(_footer_lines(L)) * LINE
    height = y + TOP_PAD

    # pass 2: emit
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L["width"]}" '
        f'height="{height}" viewBox="0 0 {L["width"]} {height}" role="img" '
        f'aria-label="open transit tracker fleet coverage">',
        _defs(L),
        _paper(L, height),
    ]
    y = TOP_PAD
    header, y = _header(L, y, data.get("updated"))
    parts.append(header)
    if form_gap:
        parts.append(f'  <rect id="form-gap" x="{L["margin"]}" y="{y}" '
                     f'width="{L["content"]}" '
                     f'height="{L["gap_rows"] * LINE}" fill="none"/>')
        y += L["gap_rows"] * LINE
    for i, a in enumerate(agencies):
        if i:
            parts.append(_perf(L, y + LINE))
            y += PERF_ROWS * LINE
        block, y = _agency_block(L, y, a, ranges_by.get(a["slug"], []),
                                 rides_by.get(a["slug"], []))
        parts.append(block)
    if footer:
        y += 2 * LINE
        parts.append(_footer(L, y - LINE))
    parts.append("</svg>")
    return "\n".join(parts)


CARD_W = 420                       # README summary card width


def render_card(data, slug):
    """Small summary card for one agency: same paper, grid, and type as
    the sheet. Header line, printed bar, last-ride line, link row.
    Everything sits on the 21px line grid, one text size, tractor-feed
    margins with holes like the sheet.
    """
    agency = next(a for a in data["agencies"] if a["slug"] == slug)
    rides = [r for r in data["rides"] if r["agency_slug"] == slug]
    L = _layout(CARD_W)
    total = agency["total_fleet"]
    count = len(rides)
    pct = count / total * 100 if total else 0.0
    h = 7 * LINE
    aria = escape(f"{agency['name']}: {count}/{total} ({pct:.2f}%)")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L["width"]}" '
        f'height="{h}" viewBox="0 0 {L["width"]} {h}" role="img" '
        f'aria-label="{aria}">',
        _defs(L),
        _paper(L, h),
    ]
    y = LINE
    label = f"{agency['name'].upper()}: "
    parts.append(_text(L["margin"], y + 15, label, weight="bold",
                       spacing="1.0"))
    parts.append(_text(L["margin"] + len(label) * (GLYPH_W + 1.0), y + 15,
                       f"{pct:.2f}% ({count}/{total})"))
    y += LINE
    bar, y = _printed_bar(L, y, pct)
    parts.append(bar)
    last = max((r["date"] for r in rides if r.get("date")), default=None)
    if last:
        parts.append(_text(L["margin"], y + 15, f"last ride {last}",
                           fill=INK_MID))
    y += 2 * LINE
    updated = data.get("updated")
    if updated:
        yy, mm, dd = updated.split("-")
        parts.append(_text(L["margin"], y + 15,
                           f"updated {int(mm)}/{int(dd)}/{yy}",
                           fill=INK_MID))
    parts.append('<a href="' + SOURCE_URL + '">'
                 + _text(L["width"] - L["margin"], y + 15,
                         "open transit tracker", fill=INK_MID,
                         anchor="end") + "</a>")
    parts.append("</svg>")
    return "\n".join(parts)


GRID_CARD_W = 690                  # README contribution-grid card width


def _fleet_cells(agency, ranges, rides):
    """One boolean per fleet vehicle, in range order.

    Cars lists, lo-hi blocks, and prefix blocks in order; vehicles that
    belong to no range become filler squares at the end. This is the
    original large-widget cell model.
    """
    ridden = {r["vehicle_num"] for r in rides
              if r.get("vehicle_num") is not None}
    cells = []
    numbered, prefix_nums, explicit_nums = set(), set(), set()
    for rng in ranges:
        if rng.get("cars"):
            for c in rng["cars"]:
                n = num(c)
                cells.append(n in ridden)
                explicit_nums.add(n)
        elif rng["lo"] is not None and rng["hi"] is not None:
            for n in range(rng["lo"], rng["hi"] + 1):
                cells.append(n in ridden)
                numbered.add(n)
        else:
            matched = sum(
                1 for r in rides
                if r.get("vehicle_num") is not None
                and str(r["vehicle_num"]).startswith(str(rng["prefix"]))
            )
            prefix_nums.update(
                r["vehicle_num"] for r in rides
                if r.get("vehicle_num") is not None
                and str(r["vehicle_num"]).startswith(str(rng["prefix"]))
            )
            for i in range(rng["count"] or 0):
                cells.append(i < matched)
                if i < matched:
                    matched -= 1
    leftover = agency["total_fleet"] - len(cells)
    if leftover > 0:
        orphan = sum(
            1 for r in rides
            if r.get("vehicle_num") is not None
            and r["vehicle_num"] not in numbered
            and r["vehicle_num"] not in prefix_nums
            and r["vehicle_num"] not in explicit_nums
        )
        for i in range(leftover):
            cells.append(i < orphan)
    return cells


def render_grid_card(data, slug):
    """Large README card: one square per vehicle, whole fleet, no
    numbers — a GitHub-contributions grid printed on the same
    dot-printer paper. Squares sit on the 21px line grid: one square
    per grid row, header and footer rows like the small card.
    """
    agency = next(a for a in data["agencies"] if a["slug"] == slug)
    rides = [r for r in data["rides"] if r["agency_slug"] == slug]
    ranges = [r for r in data["ranges"] if r["agency_slug"] == slug]
    L = _layout(GRID_CARD_W)
    total = agency["total_fleet"]
    count = len(rides)
    pct = count / total * 100 if total else 0.0
    cells = _fleet_cells(agency, ranges, rides)
    # Half-block encoding: the cell box is split in half. A top-half
    # block = first vehicle ridden, a bottom-half block = the next, a
    # full block = both. Two vehicles per cell, solid print like the
    # bar chart — much higher contrast than Braille dots.
    pairs = -(-len(cells) // 2)
    cols = L["content"] // LINE
    grid_rows = -(-pairs // cols) if pairs else 0
    h = (grid_rows + 7) * LINE
    aria = escape(f"{agency['name']}: {count}/{total} ({pct:.2f}%)")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L["width"]}" '
        f'height="{h}" viewBox="0 0 {L["width"]} {h}" role="img" '
        f'aria-label="{aria}">',
        _defs(L),
        _paper(L, h),
    ]
    y = LINE
    label = f"{agency['name'].upper()}: "
    parts.append(_text(L["margin"], y + 15, label, weight="bold",
                       spacing="1.0"))
    parts.append(_text(L["margin"] + len(label) * (GLYPH_W + 1.0), y + 15,
                       f"{pct:.2f}% ({count}/{total})"))
    y += LINE
    bar, y = _printed_bar(L, y, pct)
    parts.append(bar)
    y += LINE  # blank row between the bar and the grid
    # Cells are <rect> areas, not text glyphs. A browser that scales the
    # card down (GitHub mobile renders this 690px card ~308px wide, a
    # 0.45x downscale) hint-rasterizes text: the faint glyph frames and
    # the half-blocks collapse to noise, and the grid stops reading.
    # Rects scale exactly, so the same encoding — faint INK_FAINT blocks
    # for empty vehicles, solid INK over the ridden halves, two vehicles
    # per cell on the 21px grid — stays legible at either size.
    # cw matches the old text-glyph footprint (a 13px font block) so the
    # desktop card keeps its approved sparse look; the paper gutters
    # between cells stay wide.
    cw = FONT_SIZE                   # cell width; wide paper gutters
    half = (cw + 6) / 2 - 0.5        # split the 19px box into two halves
    for i in range(pairs):
        r, c = divmod(i, cols)
        x = L["margin"] + c * LINE + (LINE - cw) // 2
        cy = y + r * LINE + 1
        # the pair's frame: faint areas print so empty vehicles are
        # visible too; solid INK halves go over the ridden vehicles
        parts.append(f'  <rect x="{x}" y="{cy}" width="{cw}" '
                     f'height="{half}" fill="{INK_FAINT}"/>')
        if 2 * i + 1 < len(cells):
            parts.append(f'  <rect x="{x}" y="{cy + half + 1}" '
                         f'width="{cw}" height="{half}" fill="{INK_FAINT}"/>')
        a = cells[2 * i]
        b = 2 * i + 1 < len(cells) and cells[2 * i + 1]
        if a:
            parts.append(f'  <rect x="{x}" y="{cy}" width="{cw}" '
                         f'height="{half}" fill="{INK}"/>')
        if b:
            parts.append(f'  <rect x="{x}" y="{cy + half + 1}" '
                         f'width="{cw}" height="{half}" fill="{INK}"/>')
    y += grid_rows * LINE + LINE
    updated = data.get("updated")
    if updated:
        yy_, mm, dd = updated.split("-")
        parts.append(_text(L["margin"], y + 15,
                           f"updated {int(mm)}/{int(dd)}/{yy_}",
                           fill=INK_MID))
    parts.append('<a href="' + SOURCE_URL + '">'
                 + _text(L["width"] - L["margin"], y + 15,
                         "open transit tracker", fill=INK_MID,
                         anchor="end") + "</a>")
    parts.append("</svg>")
    return "\n".join(parts)
