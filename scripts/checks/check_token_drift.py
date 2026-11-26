#!/usr/bin/env python3
"""Check that the chart theme mirrors the colour tokens exactly.

The SVG charts take concrete colour strings, so chartTheme.js repeats values
from the token layer. This script is the drift guard: if a token changes and
the chart theme does not, it fails with the mismatched pairs.

Standard library only. Run from anywhere:

    python3 scripts/checks/check_token_drift.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "apps/web/src/styles/tokens/color.css"
CHART = ROOT / "apps/web/src/lib/chartTheme.js"

# token name in color.css -> key exported by chartTheme.js
PAIRS = [
    ("color-silver-050", "silverBright"),
    ("color-silver-300", "silver"),
    ("color-silver-400", "silverMuted"),
    ("color-silver-500", "silverDim"),
    ("color-graphite-500", "silverFaint"),
    ("color-crimson-500", "crimson"),
    ("color-crimson-400", "crimsonLight"),
    ("color-obsidian-800", "surface"),
    ("color-obsidian-900", "surfaceRaised"),
    ("color-silver-100", "text"),
    ("color-silver-500", "axis"),
    ("color-silver-500", "textMuted"),
    ("wash-silver-07", "grid"),
    ("rule", "rule"),
]


def token_values(path):
    text = path.read_text()
    values = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", text))
    return {k: v.strip() for k, v in values.items()}


def chart_values(path):
    text = path.read_text()
    return {k: v.strip() for k, v in re.findall(r"(\w+):\s*'([^']+)'", text)}


def resolve(name, values, seen=None):
    seen = seen or set()
    if name in seen:
        raise ValueError(f"cyclic token alias: --{name}")
    value = values.get(name)
    if value is None:
        raise KeyError(f"missing token --{name}")
    match = re.fullmatch(r"var\(--([a-z0-9-]+)\)", value)
    return resolve(match.group(1), values, seen | {name}) if match else value


def main():
    tokens = token_values(TOKENS)
    chart = chart_values(CHART)
    problems = []
    for token_name, chart_key in PAIRS:
        try:
            expected = resolve(token_name, tokens)
        except (KeyError, ValueError) as exc:
            problems.append(f"--{token_name}: {exc}")
            continue
        actual = chart.get(chart_key)
        if actual is None:
            problems.append(f"CHART.{chart_key}: missing")
        elif actual.lower() != expected.lower():
            problems.append(f"CHART.{chart_key}: {actual} != --{token_name} ({expected})")

    if problems:
        print("Token drift detected:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Palette drift check: {len(PAIRS)} chart values match the token layer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
