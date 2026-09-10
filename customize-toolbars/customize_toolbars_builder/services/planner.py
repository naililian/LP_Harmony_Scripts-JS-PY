"""Run the real engine planner (``engine/plan.js``) from Python via dukpy, so the
builder previews exactly what Harmony will register and generates badge icons
with the engine's own naming.

dukpy is a hard dependency of the builder (see requirements.txt).
"""

from __future__ import annotations

import json
from functools import lru_cache

import dukpy

from . import engine_assets

_WRAPPER = """
var exports = {};
%s
;
(function () {
  var input = dukpy['input'];
  var have = {};
  for (var i = 0; i < (input.scripts || []).length; i += 1) have[input.scripts[i]] = true;
  var haveIcon = {};
  for (var j = 0; j < (input.icons || []).length; j += 1) haveIcon[input.icons[j]] = true;
  var ctx = {
    scriptsDir: input.scriptsDir || "scripts",
    harmonyVersion: input.harmonyVersion || 0,
    hasScript: function (n) { return !!have[n]; },
    hasIcon: function (n) { return !!haveIcon[n]; }
  };
  return JSON.stringify(exports.build(input.config, ctx));
})();
"""


@lru_cache(maxsize=1)
def _plan_source() -> str:
    return (engine_assets.engine_dir() / "plan.js").read_text(encoding="utf-8")


def run_plan(
    config: dict,
    scripts: set[str] | list[str] | None = None,
    icons: set[str] | list[str] | None = None,
    scripts_dir: str = "scripts",
    harmony_version: int = 0,
) -> dict:
    raw = dukpy.evaljs(
        _WRAPPER % _plan_source(),
        input={
            "config": config,
            "scripts": sorted(scripts or []),
            "icons": sorted(icons or []),
            "scriptsDir": scripts_dir,
            "harmonyVersion": harmony_version,
        },
    )
    return json.loads(raw)
