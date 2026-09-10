"""icon_badges.py must match engine/icongen.js byte-for-byte."""

import dukpy
import pytest

from customize_toolbars_builder.services import engine_assets, icon_badges

_ICONGEN = (engine_assets.engine_dir() / "icongen.js").read_text(encoding="utf-8")
_HEAD = "var exports={};\n%s\n;\n" % _ICONGEN


def _js(expr, **kw):
    return dukpy.evaljs(_HEAD + expr, **kw)


@pytest.mark.parametrize(
    "text",
    ["rig", "LP Rig", "Use Drawing Pivot", "Set Pivot by Drawing", "clone_drawing",
     "markers", "a-b-c-d", "X", "", "A&B", "1 2 3 4"],
)
def test_abbreviate_parity(text):
    assert icon_badges.abbreviate(text, 3) == _js("exports.abbreviate(dukpy['t'],3);", t=text)


@pytest.mark.parametrize("label", ["RIG", "CD", "R", "LP", "UDP", "AB", "A&B"])
@pytest.mark.parametrize("border", [True, False])
def test_badge_svg_parity(label, border):
    got = icon_badges.badge_svg(label, border=border)
    expect = _js("exports.badgeSvg(dukpy['t'],{border:dukpy['b']});", t=label, b=border)
    assert got == expect


def test_full_pipeline_parity():
    # what package_writer actually runs
    for text in ["LP Rig", "Use Drawing Pivot", "clone_drawing"]:
        py = icon_badges.badge_svg(icon_badges.abbreviate(text, 3), border=False)
        js = _js(
            "exports.badgeSvg(exports.abbreviate(dukpy['t'],3),{border:false});", t=text
        )
        assert py == js
