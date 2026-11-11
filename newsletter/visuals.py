"""Small inline SVG/colour helpers (no external libraries, works offline)."""

import math

GAUGE_BANDS = [
    (0, 25, "#e4572e", "Extreme fear"),
    (25, 45, "#f29e4c", "Fear"),
    (45, 55, "#c8c8c8", "Neutral"),
    (55, 75, "#8bc48a", "Greed"),
    (75, 100, "#2e8b57", "Extreme greed"),
]


def _pt(score, r, cx=150, cy=150):
    a = math.pi * (1 - score / 100)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def gauge_svg(score) -> str:
    if score is None:
        return ""
    r = 118
    parts = []
    for lo, hi, colour, _ in GAUGE_BANDS:
        x1, y1 = _pt(lo + 0.6, r)
        x2, y2 = _pt(hi - 0.6, r)
        active = lo <= score < hi or (hi == 100 and score == 100)
        parts.append(
            f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 0 1 {x2:.1f},{y2:.1f}" fill="none" '
            f'stroke="{colour}" stroke-width="30" opacity="{1 if active else 0.3}"/>'
        )
    for v in (0, 25, 50, 75, 100):
        x, y = _pt(v, r - 30)
        parts.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="11" fill="#8a8f98" text-anchor="middle">{v}</text>')
    nx, ny = _pt(score, r - 18)
    parts.append(f'<line x1="150" y1="150" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1f2933" stroke-width="4" stroke-linecap="round"/>')
    parts.append('<circle cx="150" cy="150" r="9" fill="#1f2933"/>')
    parts.append(f'<text x="150" y="190" font-size="30" font-weight="700" fill="#1f2933" text-anchor="middle">{round(score)}</text>')
    return (
        '<svg viewBox="0 0 300 200" width="100%" role="img" '
        f'aria-label="Fear and Greed gauge at {round(score)} out of 100">' + "".join(parts) + "</svg>"
    )


def heat(change, cap=5.0):
    """Background + text colour for a % change (green up, red down)."""
    if change is None:
        return "#eef0f3", "#1f2933"
    t = max(-1.0, min(1.0, change / cap))
    base = (30, 142, 90) if t >= 0 else (214, 69, 69)
    k = abs(t) * 0.85 + 0.12
    rgb = tuple(round(255 + (c - 255) * k) for c in base)
    return "#%02x%02x%02x" % rgb, ("#ffffff" if k > 0.55 else "#1f2933")
