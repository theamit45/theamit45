#!/usr/bin/env python3
"""Render the animated SVG assets used by the profile README.

The public card services (github-readme-stats, github-profile-trophy,
github-readme-activity-graph) are chronically rate limited or over quota, and
none of them can see private repositories. This queries the GitHub GraphQL API
directly and writes self-hosted SVGs into assets/.

Animation uses SMIL rather than CSS keyframes because SMIL is what renders
reliably when an SVG is embedded through GitHub's camo image proxy.

Requires a token in GH_TOKEN or GITHUB_TOKEN with the `repo` scope so that
private repositories are included in the totals.
"""

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

ASSETS = Path(__file__).resolve().parent.parent / "assets"

BG = "#1a1b27"
BORDER = "#2f3352"
TITLE = "#4169E1"
TEXT = "#a9b1d6"
VALUE = "#00CED1"
FONT = "'Segoe UI', Ubuntu, Sans-Serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

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


def fetch():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req = Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY}).encode(),
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "profile-card-generator",
            },
        )
        with urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    else:
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={QUERY}"],
            capture_output=True, text=True, check=True,
        ).stdout
        payload = json.loads(out)

    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["viewer"]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# Every entrance animation starts at t=0 and encodes its delay in keyTimes
# instead of using begin="…s". That matters for two reasons: the element never
# flashes at its base value before the animation takes over, and the base
# attribute can be left at the *finished* state so anything that does not run
# SMIL (reduced-motion settings, static renderers) still shows the content.
ENTRANCE = 2.4


def fade_in(delay, dur=0.55, total=ENTRANCE):
    a, b = delay / total, min((delay + dur) / total, 1.0)
    return (
        f'<animate attributeName="opacity" values="0;0;1;1" '
        f'keyTimes="0;{a:.4f};{b:.4f};1" dur="{total}s" fill="freeze"/>'
    )


def slide_in(delay, dx=-14, dur=0.55, total=ENTRANCE):
    a, b = delay / total, min((delay + dur) / total, 1.0)
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{dx},0;{dx},0;0,0;0,0" '
        f'keyTimes="0;{a:.4f};{b:.4f};1" dur="{total}s" fill="freeze"/>'
    )


def frame(width, height, title, body, title_delay=0.1):
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 18px {FONT}; fill: {TITLE}; }}
    .label {{ font: 400 14px {FONT}; fill: {TEXT}; }}
    .value {{ font: 600 14px {FONT}; fill: {VALUE}; }}
    .small {{ font: 400 12px {FONT}; fill: {TEXT}; }}
  </style>
  <rect x="0.5" y="0.5" rx="8" width="{width - 1}" height="{height - 1}" fill="{BG}" stroke="{BORDER}"/>
  <g opacity="1"><text x="25" y="35" class="title">{esc(title)}</text>{fade_in(title_delay)}</g>
  {body}
</svg>
"""


def overview_card(stats):
    rows = [
        ("Total Repositories", stats["repos"]),
        ("Private Repositories", stats["private"]),
        ("Dynamo Tasks Shipped", stats["dynamo"]),
        ("Languages Used", stats["languages"]),
        ("Primary Language", stats["primary"]),
    ]
    body, y = [], 68
    for i, (label, value) in enumerate(rows):
        delay = round(0.35 + i * 0.13, 2)
        body.append(
            f'<g opacity="1">{fade_in(delay)}{slide_in(delay)}'
            f'<text x="25" y="{y}" class="label">{esc(label)}</text>'
            f'<text x="425" y="{y}" class="value" text-anchor="end">{esc(value)}</text>'
            f"</g>"
        )
        y += 26
    return frame(450, 195, "GitHub Overview", "\n  ".join(body))


def language_card(langs, total):
    width, bar_x, bar_w = 350, 25, 300
    shown = langs[:6]

    segments, x = [], bar_x
    for name, size, color in shown:
        seg = max(bar_w * size / total, 1.5)
        segments.append(f'<rect x="{x:.1f}" y="55" width="{seg:.1f}" height="10" fill="{color or "#858585"}"/>')
        x += seg
    if x < bar_x + bar_w:
        segments.append(f'<rect x="{x:.1f}" y="55" width="{bar_x + bar_w - x:.1f}" height="10" fill="#858585"/>')

    body = [
        f"""<defs>
    <clipPath id="wipe">
      <rect x="{bar_x}" y="53" width="{bar_w}" height="14">
        <animate attributeName="width" values="0;0;{bar_w};{bar_w}"
                 keyTimes="0;0.125;0.583;1" dur="{ENTRANCE}s" fill="freeze"/>
      </rect>
    </clipPath>
  </defs>
  <g clip-path="url(#wipe)">{"".join(segments)}</g>"""
    ]

    y = 95
    for i, (name, size, color) in enumerate(shown):
        col_x = bar_x if i % 2 == 0 else bar_x + 155
        delay = round(1.0 + i * 0.11, 2)
        pct = 100 * size / total
        body.append(
            f'<g opacity="1">{fade_in(delay, 0.45)}'
            f'<circle cx="{col_x + 5}" cy="{y - 4}" r="5" fill="{color or "#858585"}"/>'
            f'<text x="{col_x + 18}" y="{y}" class="small">{esc(name)} {pct:.1f}%</text>'
            f"</g>"
        )
        if i % 2 == 1:
            y += 24
    if len(shown) % 2 == 1:
        y += 24
    return frame(width, 195, "Most Used Languages", "\n  ".join(body))


def wave_path(width, height, baseline, amplitude):
    half = width / 2
    return f"M0,{baseline} q{half / 2},{-amplitude} {half},0 t{half},0 V{height} H0 Z"


def banner(width, height, stops, title=None, subtitle=None, seconds=14):
    """A gradient banner with two scrolling wave layers, replacing capsule-render."""
    gid = f"g{abs(hash(tuple(stops))) % 10000}"
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

    text = ""
    if title:
        ty = height * 0.44 if subtitle else height * 0.56
        text += (
            f'<g opacity="1">{fade_in(0.15, 0.9)}'
            f'<text x="{width / 2}" y="{ty}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="46" font-weight="700" fill="#ffffff">{esc(title)}</text></g>'
        )
    if subtitle:
        text += (
            f'\n  <g opacity="1">{fade_in(0.6, 0.9)}'
            f'<text x="{width / 2}" y="{height * 0.66}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="19" font-weight="400" fill="#ffffff" '
            f'fill-opacity="0.88">{esc(subtitle)}</text></g>'
        )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">
      {stop_tags}
    </linearGradient>
    <clipPath id="bclip"><rect width="{width}" height="{height}"/></clipPath>
  </defs>
  <g clip-path="url(#bclip)">
    <rect width="{width}" height="{height}" fill="url(#{gid})"/>
    {"".join(layers)}
    {shimmer}
  </g>
  {text}
</svg>
"""


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
    (ASSETS / "github-stats.svg").write_text(overview_card(stats))
    (ASSETS / "top-languages.svg").write_text(language_card(ranked, total))
    (ASSETS / "terminal.svg").write_text(terminal_svg())
    (ASSETS / "header.svg").write_text(
        banner(
            1000, 200,
            [(0, "#8A2BE2"), (50, "#4169E1"), (100, "#00CED1")],
            title="Amit Kumar Maurya",
            subtitle="AI Evaluation Specialist & Benchmark Engineer",
        )
    )
    (ASSETS / "footer.svg").write_text(
        banner(1000, 120, [(0, "#00CED1"), (50, "#4169E1"), (100, "#8A2BE2")])
    )
    print(f"wrote 5 assets to {ASSETS}")
    print(stats)


if __name__ == "__main__":
    main()
