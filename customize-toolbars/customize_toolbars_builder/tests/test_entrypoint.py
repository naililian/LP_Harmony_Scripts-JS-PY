"""`python -m customize_toolbars_builder` routes an explicit subcommand to the CLI
(everything else is the GUI, not tested here)."""

import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2]


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "customize_toolbars_builder", *args],
        cwd=str(_TOOLS),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_help_routes_to_cli():
    r = _run("-h")
    assert r.returncode == 0
    assert "{build,scan,locations}" in r.stdout


def test_locations_routes_to_cli():
    r = _run("locations")
    assert r.returncode in (0, 1)
    assert "packages" in (r.stdout + r.stderr).lower()


def test_unknown_subcommand_is_not_a_cli_error():
    # "wat" is treated as a GUI arg, not an argparse error; with no display the
    # GUI may fail to start, but it must not print the argparse usage error.
    r = _run("scan")  # scan needs roots -> real CLI usage error (exit 2)
    assert r.returncode == 2
