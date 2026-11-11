"""Build the HTML newsletter from a weekly data file.

Usage:
    python build_newsletter.py                          # newest output/*.json
    python build_newsletter.py output/2026-W47.json

Writes the HTML next to the JSON (output/2026-W47.html). Open it in a browser.
"""

import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsletter.story import Story

ROOT = Path(__file__).resolve().parent


def main():
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    else:
        files = sorted((ROOT / "output").glob("*-W*.json"))
        if not files:
            sys.exit("No data files in output/. Run fetch_weekly_data.py first.")
        src = files[-1]

    data = json.loads(src.read_text(encoding="utf-8"))
    ctx = Story(data).build()

    env = Environment(
        loader=FileSystemLoader(ROOT / "newsletter"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template("template.html").render(**ctx)
    out = src.with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
