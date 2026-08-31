#!/usr/bin/env python3
"""Render the animated SVG assets used by the profile README.

The public card services (github-readme-stats, github-profile-trophy,
github-readme-activity-graph) are chronically rate limited or over quota, and
none of them can see private repositories. This queries the GitHub GraphQL API
directly and writes self-hosted SVGs into assets/.

Two constraints shape how these are drawn:

* Animation uses SMIL, not CSS keyframes, because SMIL is what survives
  GitHub's camo image proxy.
* An SVG embedded through <img> cannot load anything external, so the tech
  logos in assets/icons are inlined into the output rather than referenced.

Requires a token in GH_TOKEN or GITHUB_TOKEN with the `repo` scope so that
private repositories are included in the totals.
"""

import json
import os
import re
import ssl
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen


def ssl_context():
    """python.org builds on macOS ship without a populated trust store, so fall
    back to certifi when OpenSSL has no CA file configured. Returning None lets
    urlopen use the system default, which is what happens on CI."""
    if ssl.get_default_verify_paths().cafile:
        return None
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICON_DIR = ASSETS / "icons"
TILES = ASSETS / "tech"

BG = "#1a1b27"
BORDER = "#2f3352"
TITLE = "#4169E1"
TEXT = "#a9b1d6"
VALUE = "#00CED1"
FONT = "'Segoe UI', Ubuntu, Sans-Serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

PURPLE, BLUE, CYAN = "#8A2BE2", "#4169E1", "#00CED1"

# Only a subset of Dynamo work lands in this account's repositories, so the
# total is tracked by hand rather than counted from repo names.
DYNAMO_TASKS = "150+"

QUERY = """
{ viewer {
    login
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        name isPrivate isFork stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  } }
"""


def gql(query):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req = Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "profile-card-generator",
            },
        )
        with urlopen(req, timeout=30, context=ssl_context()) as resp:
            payload = json.load(resp)
    else:
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, check=True,
        ).stdout
        payload = json.loads(out)

    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def fetch():
    return gql(QUERY)["viewer"]


LEETCODE_USER = "theamit45"
LEETCODE_QUERY = """
query u($username: String!) {
  matchedUser(username: $username) {
    profile { ranking }
    submitStatsGlobal { acSubmissionNum { difficulty count submissions } }
  }
  allQuestionsCount { difficulty count }
}
"""


def fetch_leetcode(username=LEETCODE_USER):
    """LeetCode's API is unofficial and unauthenticated, so treat a failure as
    'no new data' rather than an error. The caller keeps the card that is
    already committed instead of overwriting it with placeholder numbers.
    """
    req = Request(
        "https://leetcode.com/graphql",
        data=json.dumps({"query": LEETCODE_QUERY, "variables": {"username": username}}).encode(),
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/u/{username}/",
            "User-Agent": "Mozilla/5.0 (profile-card-generator)",
        },
    )
    try:
        with urlopen(req, timeout=20, context=ssl_context()) as resp:
            data = json.load(resp)["data"]
        user = data["matchedUser"]
        solved = {r["difficulty"]: r["count"] for r in user["submitStatsGlobal"]["acSubmissionNum"]}
        subs = {r["difficulty"]: r["submissions"] for r in user["submitStatsGlobal"]["acSubmissionNum"]}
        return {
            "solved": solved,
            "submissions": subs.get("All", 0),
            "ranking": user["profile"]["ranking"],
            "available": {r["difficulty"]: r["count"] for r in data["allQuestionsCount"]},
        }
    except Exception as exc:
        print(f"LeetCode fetch failed ({exc}), keeping the committed card")
        return None


def fetch_calendar(year):
    query = (
        "{ viewer { contributionsCollection("
        f'from: "{year}-01-01T00:00:00Z", to: "{year}-12-31T23:59:59Z"'
        ") { contributionCalendar { totalContributions weeks {"
        " contributionDays { date contributionCount weekday } } } } } }"
    )
    return gql(query)["viewer"]["contributionsCollection"]["contributionCalendar"]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# --------------------------------------------------------------------------
# animation helpers
# --------------------------------------------------------------------------
# There are deliberately no entrance animations in here. A browser does not
# advance an SMIL timeline for an <img> it has not painted, so anything that
# starts at opacity 0 or at zero width renders as an empty box for as long as
# it sits below the fold. Motion comes from loops that look correct on their
# very first frame instead: the drifting backdrop, bob() and sweep().
def bob(phase, amount=3.0, dur=4.6):
    """A slow vertical drift, desynchronised between elements by a negative
    begin so they do not all rise and fall together."""
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0,0;0,{-amount};0,0" dur="{dur}s" begin="-{phase:.2f}s" '
        f'repeatCount="indefinite"/>'
    )


# --------------------------------------------------------------------------
# shared animated backdrop
# --------------------------------------------------------------------------
def backdrop(width, height, uid, rx=10):
    """A drifting dot grid over slowly moving colour blooms.

    Returns (defs, background) so callers can place the defs in their own
    <defs> block. Every id is namespaced by uid because several of these can
    end up in one document.
    """
    orbs = [
        (PURPLE, 0.30, width * 0.18, height * 0.30, max(width, height) * 0.42, 17),
        (CYAN, 0.24, width * 0.82, height * 0.66, max(width, height) * 0.38, 23),
        (BLUE, 0.26, width * 0.52, height * 0.85, max(width, height) * 0.40, 29),
    ]

    grads = "".join(
        f'<radialGradient id="{uid}o{i}">'
        f'<stop offset="0%" stop-color="{c}" stop-opacity="{o}"/>'
        f'<stop offset="100%" stop-color="{c}" stop-opacity="0"/>'
        f"</radialGradient>"
        for i, (c, o, *_rest) in enumerate(orbs)
    )

    defs = f"""<pattern id="{uid}grid" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="1.5" cy="1.5" r="1.05" fill="#2c3150"/>
      <animateTransform attributeName="patternTransform" type="translate"
        values="0,0;26,26" dur="20s" repeatCount="indefinite"/>
    </pattern>
    {grads}
    <clipPath id="{uid}clip"><rect x="0.5" y="0.5" rx="{rx}" width="{width - 1}" height="{height - 1}"/></clipPath>"""

    blobs = ""
    for i, (_c, _o, cx, cy, r, dur) in enumerate(orbs):
        dx, dy = width * 0.16, height * 0.20
        blobs += (
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="url(#{uid}o{i})">'
            f'<animate attributeName="cx" values="{cx:.0f};{cx + dx:.0f};{cx - dx:.0f};{cx:.0f}" '
            f'dur="{dur}s" repeatCount="indefinite"/>'
            f'<animate attributeName="cy" values="{cy:.0f};{cy - dy:.0f};{cy + dy:.0f};{cy:.0f}" '
            f'dur="{dur * 1.3:.0f}s" repeatCount="indefinite"/>'
            f"</circle>"
        )

    background = f"""<g clip-path="url(#{uid}clip)">
    <rect width="{width}" height="{height}" fill="{BG}"/>
    {blobs}
    <rect width="{width}" height="{height}" fill="url(#{uid}grid)"/>
  </g>"""
    return defs, background


def sweep(width, height, uid, dur=7.0, opacity=0.07):
    """A translucent band crossing the card on a loop.

    Safe in a way a one-shot reveal is not: the content underneath is fully
    drawn at every frame, the band only adds a highlight on top. Reuses the
    clip path that backdrop() defines for the same uid.
    """
    return (
        f'<g clip-path="url(#{uid}clip)" opacity="{opacity}">'
        f'<rect x="{-width * 0.35:.0f}" y="{-height:.0f}" width="{width * 0.13:.0f}" '
        f'height="{height * 3:.0f}" fill="#ffffff" transform="rotate(14)">'
        f'<animate attributeName="x" values="{-width * 0.5:.0f};{width * 1.25:.0f}" '
        f'dur="{dur}s" repeatCount="indefinite"/></rect></g>'
    )


# --------------------------------------------------------------------------
# tech logos
# --------------------------------------------------------------------------
# devicon ships these three with no usable fill on a dark background: express
# and linux declare none at all (so they default to black) and github is
# near-black. The first two inherit a fill from their wrapping group, the third
# needs its hex swapped out.
ICON_INHERIT_FILL = {"express": "#e6edf3", "linux": "#FCC624"}
ICON_RECOLOUR = {
    "github": [("#181616", "#e6edf3")],
    "bash": [("#293138", "#41505c")],
}

ICON_LABELS = {
    "python": "Python", "cplusplus": "C++", "c": "C", "java": "Java",
    "javascript": "JavaScript", "bash": "Bash", "react": "React",
    "nodejs": "Node.js", "express": "Express", "mongodb": "MongoDB",
    "html5": "HTML5", "css3": "CSS3", "docker": "Docker", "linux": "Linux",
    "git": "Git", "github": "GitHub", "pytest": "Pytest", "vscode": "VS Code",
}

TECH_GROUPS = [
    ("Languages", ["python", "cplusplus", "c", "java", "javascript", "bash"]),
    ("Web and Data", ["react", "nodejs", "express", "mongodb", "html5", "css3"]),
    ("Evaluation Toolchain", ["docker", "linux", "git", "github", "pytest", "vscode"]),
]

TECH_LINKS = {
    "python": "https://www.python.org",
    "cplusplus": "https://isocpp.org",
    "c": "https://en.cppreference.com/w/c",
    "java": "https://dev.java",
    "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "bash": "https://www.gnu.org/software/bash/",
    "react": "https://react.dev",
    "nodejs": "https://nodejs.org",
    "express": "https://expressjs.com",
    "mongodb": "https://www.mongodb.com",
    "html5": "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "css3": "https://developer.mozilla.org/en-US/docs/Web/CSS",
    "docker": "https://www.docker.com",
    "linux": "https://www.kernel.org",
    "git": "https://git-scm.com",
    "github": "https://github.com",
    "pytest": "https://docs.pytest.org",
    "vscode": "https://code.visualstudio.com",
}


def inline_icon(name, x, y, size):
    """Drop a devicon logo into the document at (x, y), scaled to `size`.

    All devicon files share a 0 0 128 128 viewBox, so scaling is a single
    factor. Internal ids are namespaced because a dozen of these share one
    document and several define gradients called "a", "b", "c".
    """
    raw = (ICON_DIR / f"{name}.svg").read_text()
    inner = raw[raw.index(">", raw.index("<svg")) + 1: raw.rindex("</svg>")]

    for old, new in ICON_RECOLOUR.get(name, []):
        inner = inner.replace(old, new)

    for ident in set(re.findall(r'id="([^"]+)"', inner)):
        scoped = f"{name}-{ident}"
        inner = inner.replace(f'id="{ident}"', f'id="{scoped}"')
        inner = inner.replace(f"url(#{ident})", f"url(#{scoped})")
        inner = inner.replace(f'href="#{ident}"', f'href="#{scoped}"')

    fill = ICON_INHERIT_FILL.get(name)
    fill_attr = f' fill="{fill}"' if fill else ""
    scale = size / 128
    return (
        f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.5f})"{fill_attr}>'
        f"{inner}</g>"
    )


def tech_tile(name, index, width=132, height=110):
    """One technology as its own image so the README can wrap it in a link.

    Each tile carries its own backdrop and sweep. They stay out of step with
    each other because the drift begins at a negative offset that varies by
    index, so eighteen separate images do not rise and fall in unison.
    """
    uid = f"t{name}"
    defs, background = backdrop(width, height, uid, rx=12)
    icon_px = 46.0

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    {defs}
  </defs>
  {background}
  <rect x="0.75" y="0.75" rx="12" width="{width - 1.5}" height="{height - 1.5}" fill="none" stroke="{BORDER}"/>
  <g>{bob(index * 0.37, 3.0 + index % 3, 4.2 + (index % 4) * 0.55)}
    {inline_icon(name, (width - icon_px) / 2, 21, icon_px)}
  </g>
  <text x="{width / 2}" y="{height - 17}" text-anchor="middle" font-family="{FONT}"
        font-size="12" fill="{TEXT}">{esc(ICON_LABELS[name])}</text>
  {sweep(width, height, uid, 6.5)}
</svg>
"""


# --------------------------------------------------------------------------
# focus chips
# --------------------------------------------------------------------------
# Things with no logo in devicon, so they are drawn as accent-coloured chips
# rather than shoehorned into the icon grid.
FOCUS_GROUPS = [
    ("AI and LLM Systems", [
        ("Prompt Engineering", PURPLE), ("LLM Evaluation", BLUE),
        ("Terminal-Bench", CYAN), ("RLHF", "#16A085"),
        ("Failure-mode Analysis", "#F0883E"), ("Agent Sandboxing", "#8957E5"),
        ("GPT-5", "#10A37F"), ("Claude Sonnet", "#D97757"),
    ]),
]

CHIP_H = 34.0
CHIP_FONT = 13.0


def _chip_width(label):
    # Segoe UI advances roughly 0.545 em for mixed-case text. This only needs
    # to be close, since the chip is padded on both sides.
    return 30 + len(label) * CHIP_FONT * 0.545 + 18


def _flow(items, max_w, gap=10.0):
    rows, cur, cur_w = [], [], 0.0
    for label, color in items:
        w = _chip_width(label)
        if cur and cur_w + gap + w > max_w:
            rows.append((cur, cur_w))
            cur, cur_w = [], 0.0
        cur_w += (gap if cur else 0) + w
        cur.append((label, color, w))
    if cur:
        rows.append((cur, cur_w))
    return rows


def render_chip(x, y, label, color, w, index):
    return (
        f"<g>{bob(index * 0.31, 2.4 + index % 3, 4.4 + (index % 5) * 0.4)}"
        f'<rect x="{x:.1f}" y="{y:.1f}" rx="{CHIP_H / 2}" width="{w:.1f}" height="{CHIP_H}" '
        f'fill="{color}" fill-opacity="0.13" stroke="{color}" stroke-opacity="0.55"/>'
        f'<circle cx="{x + 17:.1f}" cy="{y + CHIP_H / 2:.1f}" r="4.5" fill="{color}"/>'
        f'<text x="{x + 30:.1f}" y="{y + CHIP_H / 2 + 4.6:.1f}" font-family="{FONT}" '
        f'font-size="{CHIP_FONT}" font-weight="600" fill="#e6edf3">{esc(label)}</text>'
        f"</g>"
    )


def focus_panel(width=900):
    pad_x, gap, row_gap, group_gap, label_h = 26.0, 10.0, 12.0, 24.0, 22.0
    max_w = width - pad_x * 2

    laid, y = [], 22.0
    for group_name, items in FOCUS_GROUPS:
        laid.append(("label", group_name, y))
        y += label_h
        for row, row_w in _flow(items, max_w, gap):
            laid.append(("row", (row, row_w), y))
            y += CHIP_H + row_gap
        y += group_gap - row_gap
    height = y - group_gap + row_gap + 8

    uid = "fp"
    defs, background = backdrop(width, int(height), uid)

    parts, index = [], 0
    for kind, payload, yy in laid:
        if kind == "label":
            parts.append(
                f'<text x="{pad_x + 6}" y="{yy + 13}" font-family="{FONT}" font-size="12" '
                f'font-weight="600" letter-spacing="1.6" fill="{TEXT}" '
                f'fill-opacity="0.75">{esc(payload.upper())}</text>'
            )
            continue

        row, row_w = payload
        x = (width - row_w) / 2
        for label, color, w in row:
            parts.append(render_chip(x, yy, label, color, w, index))
            x += w + gap
            index += 1

    return f"""<svg width="{width}" height="{height:.0f}" viewBox="0 0 {width} {height:.0f}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    {defs}
  </defs>
  {background}
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1:.0f}" fill="none" stroke="{BORDER}"/>
  {"".join(parts)}
  {sweep(width, int(height), uid, 10.0)}
</svg>
"""


# --------------------------------------------------------------------------
# DSA panel
# --------------------------------------------------------------------------
DSA_TOTAL = "350+"
DIFF_COLORS = {"Easy": "#00B8A3", "Medium": "#FFC01E", "Hard": "#FF375F"}
PLATFORMS = [
    ("LeetCode", "#FFA116"), ("GeeksforGeeks", "#2F8D46"),
    ("CodeChef", "#5B4638"), ("Coding Ninjas", "#DD6620"),
]


def dsa_panel(lc, width=900):
    height = 296
    uid = "dsa"
    defs, background = backdrop(width, height, uid)

    solved = lc["solved"]
    available = lc["available"]
    total_solved = solved.get("All", 0)
    order = ["Easy", "Medium", "Hard"]

    # Donut split by difficulty. Drawn complete at rest with a dot orbiting it,
    # rather than an arc that grows, so the first frame is already correct.
    cx, cy, r, stroke = 152.0, 142.0, 66.0, 16.0
    circumference = 2 * 3.141592653589793 * r
    arcs, offset = [], 0.0
    for name in order:
        frac = (solved.get(name, 0) / total_solved) if total_solved else 0
        seg = circumference * frac
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{DIFF_COLORS[name]}" '
            f'stroke-width="{stroke}" stroke-dasharray="{seg:.2f} {circumference - seg:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += seg

    orbit = (
        f'<g><circle cx="{cx}" cy="{cy - r}" r="4.5" fill="#ffffff" fill-opacity="0.9"/>'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="0 {cx} {cy};360 {cx} {cy}" dur="9s" repeatCount="indefinite"/></g>'
    )

    donut = (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#252a4a" stroke-width="{stroke}"/>'
        + "".join(arcs) + orbit
        + f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="{FONT}" font-size="34" '
          f'font-weight="700" fill="#e6edf3">{total_solved}</text>'
        + f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" font-family="{FONT}" font-size="11.5" '
          f'fill="{TEXT}" fill-opacity="0.85">LeetCode solved</text>'
    )

    x0, right = 296.0, float(width - 30)
    peak = max((solved.get(n, 0) for n in order), default=1) or 1
    bar_x, bar_w = 386.0, 300.0

    rows = ""
    for i, name in enumerate(order):
        y = 116 + i * 38
        count = solved.get(name, 0)
        fill_w = max(bar_w * count / peak, 3)
        rows += (
            f'<text x="{x0}" y="{y + 4}" font-family="{FONT}" font-size="13.5" '
            f'font-weight="600" fill="#e6edf3">{name}</text>'
            f'<rect x="{bar_x}" y="{y - 5}" width="{bar_w}" height="9" rx="4.5" fill="#252a4a"/>'
            f'<rect x="{bar_x}" y="{y - 5}" width="{fill_w:.1f}" height="9" rx="4.5" '
            f'fill="{DIFF_COLORS[name]}"/>'
            f'<text x="{right}" y="{y + 4}" text-anchor="end" font-family="{FONT}" font-size="12.5" '
            f'fill="{TEXT}">{count} of {available.get(name, 0):,}</text>'
        )

    accepted = (100 * total_solved / lc["submissions"]) if lc["submissions"] else 0
    header = (
        f'<text x="{x0}" y="52" font-family="{FONT}" font-size="19" font-weight="700" '
        f'fill="{TITLE}">{DSA_TOTAL} problems solved across four platforms</text>'
        f'<text x="{x0}" y="76" font-family="{FONT}" font-size="12.5" fill="{TEXT}" '
        f'fill-opacity="0.85">LeetCode breakdown, acceptance {accepted:.0f}% over '
        f'{lc["submissions"]} submissions, global rank #{lc["ranking"]:,}</text>'
    )

    chips, widths = [], [_chip_width(n) for n, _ in PLATFORMS]
    row_w = sum(widths) + 10 * (len(PLATFORMS) - 1)
    cxp = (width - row_w) / 2
    for i, ((name, colour), w) in enumerate(zip(PLATFORMS, widths)):
        chips.append(render_chip(cxp, 236, name, colour, w, i))
        cxp += w + 10

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    {defs}
  </defs>
  {background}
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1}" fill="none" stroke="{BORDER}"/>
  {donut}
  {header}
  {rows}
  {"".join(chips)}
  {sweep(width, height, uid, 9.5)}
</svg>
"""


# --------------------------------------------------------------------------
# contribution heatmap
# --------------------------------------------------------------------------
CONTRIB_YEAR = 2023
HEAT = ["#1c2040", "#2f3d78", "#3A5CB8", "#4169E1", "#00CED1"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def contribution_card(cal, year, width=900):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    cell, gap = 12, 3
    pitch = cell + gap
    left, top = 62, 78
    grid_bottom = top + 7 * pitch - gap
    height = grid_bottom + 50

    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    peak = max(counts) if counts else 1

    def level(count):
        if count <= 0:
            return 0
        ratio = count / peak
        for i, edge in enumerate((0.15, 0.35, 0.65)):
            if ratio <= edge:
                return i + 1
        return 4

    uid = "cg"
    defs, background = backdrop(width, int(height), uid)

    cells, month_labels, prev_month = [], [], None
    for wi, week in enumerate(weeks):
        x = left + wi * pitch
        for day in week["contributionDays"]:
            y = top + day["weekday"] * pitch
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" '
                f'fill="{HEAT[level(day["contributionCount"])]}"/>'
            )
        month = week["contributionDays"][0]["date"][5:7]
        if month != prev_month:
            prev_month = month
            month_labels.append(
                f'<text x="{x}" y="{top - 11}" font-family="{FONT}" font-size="11" '
                f'fill="{TEXT}" fill-opacity="0.8">{MONTHS[int(month) - 1]}</text>'
            )

    weekdays = "".join(
        f'<text x="{left - 12}" y="{top + row * pitch + 10}" text-anchor="end" '
        f'font-family="{FONT}" font-size="10.5" fill="{TEXT}" fill-opacity="0.7">{name}</text>'
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )

    legend_x = width - 26 - 5 * 17 - 74
    legend = (
        f'<text x="{legend_x}" y="{grid_bottom + 26}" font-family="{FONT}" font-size="11" '
        f'fill="{TEXT}" fill-opacity="0.75">Less</text>'
    )
    for i, colour in enumerate(HEAT):
        legend += (
            f'<rect x="{legend_x + 32 + i * 17}" y="{grid_bottom + 16}" width="12" height="12" '
            f'rx="2.5" fill="{colour}"/>'
        )
    legend += (
        f'<text x="{legend_x + 32 + 5 * 17 + 6}" y="{grid_bottom + 26}" font-family="{FONT}" '
        f'font-size="11" fill="{TEXT}" fill-opacity="0.75">More</text>'
    )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    {defs}
  </defs>
  {background}
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1}" fill="none" stroke="{BORDER}"/>
  <text x="26" y="34" font-family="{FONT}" font-size="18" font-weight="600" fill="{TITLE}">{total:,} contributions in {year}</text>
  <text x="26" y="54" font-family="{FONT}" font-size="12" fill="{TEXT}" fill-opacity="0.8">Peak day: {peak} contributions</text>
  {"".join(month_labels)}
  {weekdays}
  {"".join(cells)}
  {legend}
  {sweep(width, height, uid, 8.0, 0.09)}
</svg>
"""


# --------------------------------------------------------------------------
# cards
# --------------------------------------------------------------------------
def stats_card(stats, langs, total, width=900, height=230):
    """Overview and language split in one panel.

    These used to be two images at fixed pixel widths, which left them the
    only things on the page not scaling to the container. One 900 wide card
    lines up with the DSA and contribution panels at any window size.
    """
    uid = "st"
    defs, background = backdrop(width, height, uid)
    gutter, mid = 26.0, width / 2
    left_end = mid - 24
    right_x, right_end = mid + 24, width - gutter

    rows = [
        ("Total Repositories", stats["repos"]),
        ("Private Repositories", stats["private"]),
        ("Dynamo Tasks Shipped", stats["dynamo"]),
        ("Languages Used", stats["languages"]),
        ("Primary Language", stats["primary"]),
    ]
    left = f'<text x="{gutter}" y="42" class="title">GitHub Overview</text>'
    y = 82
    for label, value in rows:
        left += (
            f'<text x="{gutter}" y="{y}" class="label">{esc(label)}</text>'
            f'<text x="{left_end}" y="{y}" class="value" text-anchor="end">{esc(value)}</text>'
        )
        y += 28

    shown = langs[:6]
    bar_w = right_end - right_x
    segments, x = [], right_x
    for _name, size, color in shown:
        seg = max(bar_w * size / total, 1.5)
        segments.append(
            f'<rect x="{x:.1f}" y="64" width="{seg:.1f}" height="11" fill="{color or "#858585"}"/>'
        )
        x += seg
    if x < right_end:
        segments.append(
            f'<rect x="{x:.1f}" y="64" width="{right_end - x:.1f}" height="11" fill="#858585"/>'
        )

    right = (
        f'<text x="{right_x}" y="42" class="title">Most Used Languages</text>'
        f'<clipPath id="{uid}bar"><rect x="{right_x}" y="64" width="{bar_w}" height="11" rx="5.5"/></clipPath>'
        f'<g clip-path="url(#{uid}bar)">{"".join(segments)}</g>'
    )
    col_w, y = bar_w / 2, 118
    for i, (name, size, color) in enumerate(shown):
        col_x = right_x + (0 if i % 2 == 0 else col_w)
        right += (
            f'<circle cx="{col_x + 5}" cy="{y - 4}" r="5" fill="{color or "#858585"}"/>'
            f'<text x="{col_x + 18}" y="{y}" class="small">{esc(name)} {100 * size / total:.1f}%</text>'
        )
        if i % 2 == 1:
            y += 32

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 18px {FONT}; fill: {TITLE}; }}
    .label {{ font: 400 14px {FONT}; fill: {TEXT}; }}
    .value {{ font: 600 14px {FONT}; fill: {VALUE}; }}
    .small {{ font: 400 12.5px {FONT}; fill: {TEXT}; }}
  </style>
  <defs>
    {defs}
  </defs>
  {background}
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1}" fill="none" stroke="{BORDER}"/>
  <line x1="{mid}" y1="30" x2="{mid}" y2="{height - 30}" stroke="{BORDER}" stroke-opacity="0.8"/>
  {left}
  {right}
  {sweep(width, height, uid, 8.5)}
</svg>
"""


# --------------------------------------------------------------------------
# banners and dividers
# --------------------------------------------------------------------------
def wave_path(width, height, baseline, amplitude):
    half = width / 2
    return f"M0,{baseline} q{half / 2},{-amplitude} {half},0 t{half},0 V{height} H0 Z"


# --------------------------------------------------------------------------
# contact pills
# --------------------------------------------------------------------------
# GitHub renders README images through <img>, and an <a> inside an SVG loaded
# that way is inert. The only clickable unit is a whole image, so each contact
# is emitted as its own pill that the README wraps in a real anchor.
CONTACT_PILLS = [
    ("email", "gmail", "amitmaurya7071@gmail.com", "#EA4335"),
    ("linkedin", "linkedin", "in/amit-kumar-maurya", "#0A66C2"),
    ("github", "github", "github.com/theamit45", "#C9D1D9"),
    ("leetcode", "leetcode", "leetcode.com/u/theamit45", "#FFA116"),
]

# Tools with no devicon logo. Same pill, drawn with an accent dot instead of a
# mark, so they can carry a link the way the contact pills do.
TOOL_PILLS = [
    ("sql", "SQL", "#4479A1", "https://en.wikipedia.org/wiki/SQL"),
    ("ruff", "Ruff", "#D7FF64", "https://docs.astral.sh/ruff/"),
    ("toml", "TOML", "#C75B39", "https://toml.io"),
    ("uv", "uv / uvx", "#DE5FE9", "https://docs.astral.sh/uv/"),
    ("zod", "Zod", "#3E67B1", "https://zod.dev"),
    ("cursor", "Cursor", "#C9D1D9", "https://cursor.com"),
]


def simple_icon_path(name):
    src = (ICON_DIR / f"si-{name}.svg").read_text()
    return re.search(r'<path[^>]*\sd="([^"]+)"', src).group(1)


def link_pill(label, colour, icon, uid, height=44.0):
    """A pill sized to its label. `icon` is a 24x24 path, or None for a plain
    accent dot when the tool has no mark worth inlining."""
    font, glyph = 14.5, 18.0
    pad_l, gap, pad_r = 17.0, 10.0, 19.0
    width = pad_l + glyph + gap + len(label) * font * 0.545 + pad_r
    r = height / 2
    scale = glyph / 24.0
    icon_y = (height - glyph) / 2

    if icon:
        mark = (f'<g transform="translate({pad_l},{icon_y:.1f}) scale({scale:.4f})">'
                f'<path d="{icon}" fill="{colour}"/></g>')
    else:
        mark = f'<circle cx="{pad_l + glyph / 2:.1f}" cy="{height / 2}" r="5.5" fill="{colour}"/>'

    return f"""<svg width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}"
     fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="{uid}f" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{colour}" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="{colour}" stop-opacity="0.06"/>
    </linearGradient>
    <clipPath id="{uid}c">
      <rect x="0" y="0" rx="{r}" width="{width:.0f}" height="{height:.0f}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#{uid}c)">
    <rect width="{width:.0f}" height="{height:.0f}" fill="{BG}"/>
    <rect width="{width:.0f}" height="{height:.0f}" fill="url(#{uid}f)"/>
    <rect x="{-width * 0.35:.0f}" y="{-height:.0f}" width="{width * 0.22:.0f}" height="{height * 3:.0f}"
          fill="#ffffff" fill-opacity="0.07" transform="rotate(18)">
      <animate attributeName="x" values="{-width * 0.5:.0f};{width * 1.25:.0f}"
               dur="4.5s" repeatCount="indefinite"/>
    </rect>
  </g>
  <rect x="0.75" y="0.75" rx="{r - 0.75}" width="{width - 1.5:.1f}" height="{height - 1.5:.1f}"
        fill="none" stroke="{colour}" stroke-opacity="0.55"/>
  {mark}
  <text x="{pad_l + glyph + gap:.1f}" y="{height / 2 + font * 0.35:.1f}" font-family="{FONT}"
        font-size="{font}" font-weight="600" fill="#e6edf3">{esc(label)}</text>
</svg>
"""


def banner(width, height, stops, uid, title=None, subtitle=None, seconds=14):
    """A gradient banner with scrolling waves over the shared backdrop."""
    stop_tags = "\n      ".join(
        f'<stop offset="{off}%" stop-color="{color}"/>' for off, color in stops
    )

    layers = []
    for opacity, amp, base, speed in ((0.18, 16, height * 0.62, seconds), (0.30, 11, height * 0.78, seconds * 0.7)):
        path = wave_path(width, height, base, amp)
        layers.append(
            f"""<g opacity="{opacity}">
      <g>
        <path d="{path}" fill="#ffffff"/>
        <path d="{path}" fill="#ffffff" transform="translate({width},0)"/>
        <animateTransform attributeName="transform" type="translate"
          from="0,0" to="{-width},0" dur="{speed}s" repeatCount="indefinite"/>
      </g>
    </g>"""
        )

    # A slow diagonal light sweep so the banner keeps moving even where the
    # waves are flat.
    shimmer = f"""<g opacity="0.10">
    <rect x="{-width * 0.3}" y="{-height}" width="{width * 0.14}" height="{height * 3}"
          fill="#ffffff" transform="rotate(18)">
      <animate attributeName="x" from="{-width * 0.4}" to="{width * 1.3}"
               dur="7s" repeatCount="indefinite"/>
    </rect>
  </g>"""

    if title:
        title_y, sub_y = (height * 0.44 if subtitle else height * 0.56), height * 0.66
    else:
        title_y, sub_y = 0, height * 0.56

    # No entrance fades on the lettering. A browser will not advance an SMIL
    # timeline for an <img> it has not painted yet, so anything that starts at
    # opacity 0 can stay invisible on a banner below the fold.
    text = ""
    if title:
        text += (
            f'<text x="{width / 2}" y="{title_y}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="46" font-weight="700" fill="#ffffff">{esc(title)}</text>'
        )
    if subtitle:
        text += (
            f'\n  <text x="{width / 2}" y="{sub_y}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{19 if title else 21}" font-weight="400" fill="#ffffff" '
            f'fill-opacity="0.88">{esc(subtitle)}</text>'
        )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
  <defs>
    <linearGradient id="{uid}g" x1="0" y1="0" x2="1" y2="0">
      {stop_tags}
    </linearGradient>
    <pattern id="{uid}dots" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.16"/>
      <animateTransform attributeName="patternTransform" type="translate"
        values="0,0;24,24" dur="16s" repeatCount="indefinite"/>
    </pattern>
    <clipPath id="{uid}clip"><rect width="{width}" height="{height}"/></clipPath>
  </defs>
  <g clip-path="url(#{uid}clip)">
    <rect width="{width}" height="{height}" fill="url(#{uid}g)"/>
    <rect width="{width}" height="{height}" fill="url(#{uid}dots)"/>
    {"".join(layers)}
    {shimmer}
  </g>
  {text}
</svg>
"""


def divider(width=900, height=8):
    """A hairline rule with a light pulse running along it, used between
    sections in place of a plain markdown rule."""
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
  <defs>
    <linearGradient id="dvline" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0"/>
      <stop offset="18%" stop-color="{PURPLE}" stop-opacity="0.85"/>
      <stop offset="50%" stop-color="{BLUE}" stop-opacity="0.85"/>
      <stop offset="82%" stop-color="{CYAN}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="dvpulse">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect y="{height / 2 - 0.75}" width="{width}" height="1.5" fill="url(#dvline)"/>
  <ellipse cx="-80" cy="{height / 2}" rx="64" ry="{height / 2}" fill="url(#dvpulse)">
    <animate attributeName="cx" values="-80;{width + 80}" dur="6s" repeatCount="indefinite"/>
  </ellipse>
</svg>
"""


# --------------------------------------------------------------------------
# terminal
# --------------------------------------------------------------------------
GREEN, RED, MUTED, DIM, FG, ACCENT = "#3fb950", "#f85149", "#7d8590", "#3d444d", "#e6edf3", "#00CED1"

# (label, result, colour). Labels are padded to a fixed column so the dot
# leaders line up; the font is monospace, so padding with spaces is enough.
_STEPS = [
    ("building sandbox image", "ok", GREEN),
    ("oracle solution", "1.0  PASS", GREEN),
    ("nop baseline", "0.0  PASS", GREEN),
    ("agent attempt", "0.0  FAIL", RED),
]
_LABEL_COL = max(len(label) for label, _, _ in _STEPS) + 2


def _terminal_lines():
    lines = [
        [("$ ", ACCENT), ("tb run --task security/jwt-forgery --agent claude-sonnet", FG)],
    ]
    for label, result, color in _STEPS:
        lines.append([
            (f"  {label.ljust(_LABEL_COL)}", MUTED),
            ("." * 10 + "  ", DIM),
            (result, color),
        ])
    lines.append([("     missed constant-time compare in verify()", "#8b949e")])
    lines.append([("$ ", ACCENT), ("tb validate", FG), ("  ->  ", DIM), ("task accepted", "#4169E1")])
    return lines


TERMINAL_LINES = _terminal_lines()


def terminal_svg(width=720, cycle=11.0):
    bar_h, top, line_h = 36, 68, 26
    height = top + line_h * len(TERMINAL_LINES) + 26

    dots = "".join(
        f'<circle cx="{22 + i * 20}" cy="{bar_h / 2}" r="6" fill="{c}"/>'
        for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840"))
    )

    body, y = [], top
    for i, segments in enumerate(TERMINAL_LINES):
        appear = 0.5 + i * 0.78
        a = round(appear / cycle, 4)
        b = round((appear + 0.32) / cycle, 4)
        spans = "".join(
            f'<tspan fill="{color}" xml:space="preserve">{esc(t)}</tspan>' for t, color in segments
        )
        body.append(
            f'<g opacity="1">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" '
            f'keyTimes="0;{a};{b};0.90;1" dur="{cycle}s" repeatCount="indefinite"/>'
            f'<text x="22" y="{y}" font-family="{MONO}" font-size="13.5">{spans}</text>'
            f"</g>"
        )
        y += line_h

    cursor_y = y - line_h + 6
    cursor = (
        f'<rect x="22" y="{cursor_y}" width="8" height="15" fill="#00CED1">'
        f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" '
        f'dur="1.1s" repeatCount="indefinite"/></rect>'
    )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1}" fill="#0d1117" stroke="{BORDER}"/>
  <path d="M0.5,10.5 a10,10 0 0 1 10,-10 h{width - 21} a10,10 0 0 1 10,10 v{bar_h - 10} h-{width - 1} Z" fill="#161b26"/>
  <line x1="0.5" y1="{bar_h}" x2="{width - 0.5}" y2="{bar_h}" stroke="{BORDER}"/>
  {dots}
  <text x="{width / 2}" y="{bar_h / 2 + 4}" text-anchor="middle" font-family="{MONO}"
        font-size="12" fill="#7d8590">amit@dynamo: ~/terminal-bench</text>
  {"".join(body)}
  {cursor}
</svg>
"""


def main():
    viewer = fetch()
    repos = viewer["repositories"]["nodes"]

    counter, colors = Counter(), {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            counter[edge["node"]["name"]] += edge["size"]
            colors[edge["node"]["name"]] = edge["node"]["color"]

    total = sum(counter.values()) or 1
    ranked = [(n, s, colors.get(n)) for n, s in counter.most_common()]

    stats = {
        "repos": viewer["repositories"]["totalCount"],
        "private": sum(1 for r in repos if r["isPrivate"]),
        "dynamo": DYNAMO_TASKS,
        "languages": len(counter),
        "primary": ranked[0][0] if ranked else "n/a",
    }

    ASSETS.mkdir(exist_ok=True)
    written = {
        "stats.svg": stats_card(stats, ranked, total),
        "terminal.svg": terminal_svg(),
        "focus.svg": focus_panel(),
        "contributions.svg": contribution_card(fetch_calendar(CONTRIB_YEAR), CONTRIB_YEAR),
        "divider.svg": divider(),
        "header.svg": banner(
            1000, 200, [(0, PURPLE), (50, BLUE), (100, CYAN)], "hdr",
            title="Amit Kumar Maurya",
            subtitle="AI Evaluation Specialist & Benchmark Engineer",
        ),
        "footer.svg": banner(
            1000, 130, [(0, CYAN), (50, BLUE), (100, PURPLE)], "ftr",
            subtitle="If it isn't tested, it doesn't work.",
        ),
    }

    for key, icon, label, colour in CONTACT_PILLS:
        written[f"contact-{key}.svg"] = link_pill(label, colour, simple_icon_path(icon), f"p{key}")

    for key, label, colour, _url in TOOL_PILLS:
        written[f"tool-{key}.svg"] = link_pill(label, colour, None, f"t{key}")

    TILES.mkdir(exist_ok=True)
    index = 0
    for _group, names in TECH_GROUPS:
        for name in names:
            (TILES / f"{name}.svg").write_text(tech_tile(name, index))
            index += 1
    print(f"wrote {index} tech tiles to {TILES}")

    leetcode = fetch_leetcode()
    if leetcode:
        written["dsa.svg"] = dsa_panel(leetcode)

    for name, content in written.items():
        (ASSETS / name).write_text(content)

    print(f"wrote {len(written)} assets to {ASSETS}")
    print(stats)


if __name__ == "__main__":
    main()
