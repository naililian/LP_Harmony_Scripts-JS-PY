"""Locate the canonical Customize_Toolbars engine (the files copied verbatim into every
generated package).

Single source of truth: ``harmony/packages/Customize_Toolbars/engine/`` in the dev
repo. Resolution order:
  1. ``$CUSTOMIZE_TOOLBARS_ENGINE``
  2. walk up from this file looking for ``harmony/packages/Customize_Toolbars/engine``
  3. a bundled ``_bundled_package/`` next to this package — a full copy of the
     Harmony package, used in a standalone / released distribution
"""

from __future__ import annotations

import os
from pathlib import Path

ENGINE_FILES = (
    "index.js",
    "plan.js",
    "register.js",
    "fsutil.js",
    "log.js",
    "icongen.js",
    "toolbar.schema.json",
)

_PKG_ROOT = Path(__file__).resolve().parents[1]  # tools/customize_toolbars_builder/


def _looks_like_engine(path: Path) -> bool:
    return path.is_dir() and (path / "plan.js").is_file() and (path / "toolbar.schema.json").is_file()


def engine_dir() -> Path:
    override = os.environ.get("CUSTOMIZE_TOOLBARS_ENGINE")
    if override:
        p = Path(override)
        if _looks_like_engine(p):
            return p
        raise FileNotFoundError("CUSTOMIZE_TOOLBARS_ENGINE does not point at an engine folder: " + override)

    for parent in [_PKG_ROOT, *_PKG_ROOT.parents]:
        candidate = parent / "harmony" / "packages" / "Customize_Toolbars" / "engine"
        if _looks_like_engine(candidate):
            return candidate

    bundled = _PKG_ROOT / "_bundled_package" / "engine"
    if _looks_like_engine(bundled):
        return bundled

    raise FileNotFoundError(
        "Could not locate the Customize_Toolbars engine. Set $CUSTOMIZE_TOOLBARS_ENGINE, or "
        "run from the dev repo, or ship a _bundled_package/ next to the builder."
    )


def schema_path() -> Path:
    return engine_dir() / "toolbar.schema.json"


def configure_js_path() -> Path:
    """The package-root configure.js that Harmony calls (sits beside engine/)."""
    return engine_dir().parent / "configure.js"
