#!/usr/bin/env python3
"""Render the GitHub stat cards used by the profile README.

The public card services (github-readme-stats, github-profile-trophy,
github-readme-activity-graph) are chronically rate limited or over quota, and
none of them can see private repositories. This queries the GitHub GraphQL API
directly and writes self-hosted SVGs into assets/.

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


def frame(width, height, title, body):
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 18px {FONT}; fill: {TITLE}; }}
    .label {{ font: 400 14px {FONT}; fill: {TEXT}; }}
    .value {{ font: 600 14px {FONT}; fill: {VALUE}; }}
    .small {{ font: 400 12px {FONT}; fill: {TEXT}; }}
  </style>
  <rect x="0.5" y="0.5" rx="8" width="{width - 1}" height="{height - 1}" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="title">{esc(title)}</text>
  {body}
</svg>
"""


def overview_card(stats):
    rows = [
        ("Total Repositories", stats["repos"]),
        ("Private Repositories", stats["private"]),
        ("Dynamo Task Environments", stats["dynamo"]),
        ("Languages Used", stats["languages"]),
        ("Primary Language", stats["primary"]),
    ]
    body = []
    y = 68
    for label, value in rows:
        body.append(f'<text x="25" y="{y}" class="label">{esc(label)}</text>')
        body.append(f'<text x="425" y="{y}" class="value" text-anchor="end">{esc(value)}</text>')
        y += 26
    return frame(450, 195, "GitHub Overview", "\n  ".join(body))


def language_card(langs, total):
    width, bar_x, bar_w = 350, 25, 300
    shown = langs[:6]
    body, x = [], bar_x
    for name, size, color in shown:
        seg = max(bar_w * size / total, 1.5)
        body.append(f'<rect x="{x:.1f}" y="55" width="{seg:.1f}" height="10" fill="{color or "#858585"}"/>')
        x += seg
    if x < bar_x + bar_w:
        body.append(f'<rect x="{x:.1f}" y="55" width="{bar_x + bar_w - x:.1f}" height="10" fill="#858585"/>')

    y = 95
    for i, (name, size, color) in enumerate(shown):
        col_x = bar_x if i % 2 == 0 else bar_x + 155
        body.append(f'<circle cx="{col_x + 5}" cy="{y - 4}" r="5" fill="{color or "#858585"}"/>')
        pct = 100 * size / total
        body.append(f'<text x="{col_x + 18}" y="{y}" class="small">{esc(name)} {pct:.1f}%</text>')
        if i % 2 == 1:
            y += 24
    if len(shown) % 2 == 1:
        y += 24
    return frame(width, 195, "Most Used Languages", "\n  ".join(body))


def wave_path(width, height, baseline, amplitude):
    half = width / 2
    return (
        f"M0,{baseline} q{half / 2},{-amplitude} {half},0 t{half},0 "
        f"V{height} H0 Z"
    )


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

    text = ""
    if title:
        ty = height * 0.44 if subtitle else height * 0.56
        text += (
            f'<text x="{width / 2}" y="{ty}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="46" font-weight="700" fill="#ffffff">{esc(title)}</text>'
        )
    if subtitle:
        text += (
            f'\n  <text x="{width / 2}" y="{height * 0.66}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="19" font-weight="400" fill="#ffffff" '
            f'fill-opacity="0.88">{esc(subtitle)}</text>'
        )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">
      {stop_tags}
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#{gid})"/>
  {"".join(layers)}
  {text}
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
        "dynamo": sum(1 for r in repos if r["name"].startswith("dynamo-")),
        "languages": len(counter),
        "primary": ranked[0][0] if ranked else "n/a",
    }

    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "github-stats.svg").write_text(overview_card(stats))
    (ASSETS / "top-languages.svg").write_text(language_card(ranked, total))
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
    print(f"wrote 4 assets to {ASSETS}")
    print(stats)


if __name__ == "__main__":
    main()
