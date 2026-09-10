"""Test bootstrap for customize_toolbars_builder.

Puts ``tools/`` on sys.path so ``import customize_toolbars_builder...`` works, and offers
fixtures for a fake scripts tree and a fake Harmony %APPDATA%.
"""

import base64
import sys
import textwrap
from pathlib import Path

import pytest

# a real 1x1 transparent PNG
_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

pytest.importorskip("dukpy", reason="pip install -r tools/customize_toolbars_builder/requirements.txt")


@pytest.fixture
def scripts_root(tmp_path: Path) -> Path:
    """A folder shaped like harmony/: launcher .js files, .py/.ui siblings, and a
    script-icons/ folder."""
    root = tmp_path / "harmony"
    root.mkdir()
    (root / "script-icons").mkdir()

    # 1. plain single-file launcher, has a convention icon
    (root / "LP_solo.js").write_text(
        "function LP_solo() { MessageBox.information('hi'); }\n", encoding="utf-8"
    )
    (root / "script-icons" / "LP_solo.png").write_bytes(_PNG_1PX)

    # 2. js + py, __file__-first resolution (portable), references its .py
    (root / "LP_pair.js").write_text(
        textwrap.dedent(
            """
            function LP_pair() {
                var scriptFolder = (typeof __file__ !== 'undefined')
                    ? __file__ : System.getenv('TOONBOOM_GLOBAL_SCRIPT_LOCATION');
                var scriptPy = scriptFolder + "/" + "LP_pair.py";
            }
            """
        ),
        encoding="utf-8",
    )
    (root / "LP_pair.py").write_text("def run(folder):\n    pass\n", encoding="utf-8")

    # 3. env-only launcher (not portable), + a .ui
    (root / "LP_envonly.js").write_text(
        textwrap.dedent(
            """
            function LP_envonly() {
                var scriptFolder = System.getenv('TOONBOOM_GLOBAL_SCRIPT_LOCATION');
                var scriptPy = scriptFolder + "/LP_envonly.py";
            }
            """
        ),
        encoding="utf-8",
    )
    (root / "LP_envonly.py").write_text("x = 1\n", encoding="utf-8")
    (root / "LP_envonly.ui").write_text("<ui/>\n", encoding="utf-8")

    return root


@pytest.fixture
def fake_appdata(tmp_path: Path) -> Path:
    appdata = tmp_path / "AppData" / "Roaming"
    for edition, scripts in [
        ("Toon Boom Harmony Premium", "2500-scripts"),
        ("Toon Boom Harmony Premium", "2400-scripts"),
        ("Toon Boom Harmony Advanced", "2500-scripts"),
    ]:
        (appdata / "Toon Boom Animation" / edition / scripts).mkdir(parents=True)
    return appdata
