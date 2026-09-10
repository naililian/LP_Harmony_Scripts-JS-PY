"""Python port of ``engine/icongen.js`` so the builder can pre-generate the title
and monogram badge SVGs (committed with the package, works on a read-only
install).

``test_icon_badges.py`` asserts byte-for-byte parity with the JS via dukpy — if
you touch one side, update the other until that test passes.
"""

from __future__ import annotations

import re

_COLOR = "#d0d0d0"


def escape_xml(text: str) -> str:
    return (
        str("" if text is None else text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def abbreviate(source: str, max_len: int = 3) -> str:
    clean = re.sub(r"[^A-Z0-9]+", " ", ("" if source is None else str(source)).upper())
    words = [w for w in clean.split(" ") if w]
    if len(words) >= 2:
        initials = ""
        for w in words:
            if len(initials) >= max_len:
                break
            initials += w[0]
        return initials
    return (words[0][:max_len] if words else "") or "?"


def badge_svg(text: str, border: bool = True) -> str:
    label = str(text or "?")[:3].upper()
    color = _COLOR
    w, h = 30, 22
    font_size = 9.5 if len(label) >= 3 else (12 if len(label) == 2 else 14)
    baseline = h / 2 + font_size * 0.35

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}"'
        ' viewBox="0 0 {} {}">'.format(w, h, w, h)
    ]
    if border:
        parts.append(
            '<rect x="1" y="1" width="{}" height="{}" rx="3.5" ry="3.5" fill="none"'
            ' stroke="{}" stroke-opacity="0.55" stroke-width="1.5"/>'.format(w - 2, h - 2, color)
        )
    parts.append(
        '<text x="{}" y="{:.1f}" fill="{}" font-family="Arial, Helvetica, sans-serif"'
        ' font-size="{}" font-weight="700" text-anchor="middle" letter-spacing="0.5">{}</text>'.format(
            w // 2, baseline, color, _fmt_num(font_size), escape_xml(label)
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def _fmt_num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
