"""Render a ToolbarProject into a self-contained Harmony package folder:

    <out>/<PackageName>/
      configure.js            (verbatim from the engine tree)
      tbpackage.json          (from project metadata)
      engine/*                (verbatim)
      toolbars/<id>.json      (one per project toolbar, + $schema hint)
      scripts/*               (bundled launcher scripts + companions)
      icons/*                 (convention icons + pre-generated badges)

The engine's own planner (via services.planner) decides which badges exist and
what they are named; this module only copies files and renders SVG.

Pure stdlib + dukpy. No Qt.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..models.script_index import ScriptInfo, scan_scripts
from . import engine_assets, icon_badges, planner
from .companion_resolver import CompanionSet, resolve


@dataclass
class WriteReport:
    package_dir: Path
    toolbars: list[str] = field(default_factory=list)
    scripts_bundled: list[str] = field(default_factory=list)
    icons_written: list[str] = field(default_factory=list)
    badges_generated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def text(self) -> str:
        lines = [
            "package: {}".format(self.package_dir),
            "  toolbars: " + (", ".join(self.toolbars) or "(none)"),
            "  scripts:  {} file(s) bundled".format(len(self.scripts_bundled)),
            "  icons:    {} ({} generated badges)".format(
                len(self.icons_written), len(self.badges_generated)
            ),
        ]
        for w in self.warnings:
            lines.append("  ! " + w)
        return "\n".join(lines)


def write_package(
    project,
    out_dir: str | Path,
    script_index: dict[str, ScriptInfo] | None = None,
    harmony_version: int = 0,
) -> WriteReport:
    out_dir = Path(out_dir)
    pkg = out_dir / project.package_name
    if script_index is None:
        script_index = _index_from_roots(project)

    for sub in ("engine", "toolbars", "scripts", "icons"):
        (pkg / sub).mkdir(parents=True, exist_ok=True)

    report = WriteReport(package_dir=pkg)

    # --- engine + configure.js (verbatim) ---
    engine_src = engine_assets.engine_dir()
    for name in engine_assets.ENGINE_FILES:
        shutil.copy2(engine_src / name, pkg / "engine" / name)
    shutil.copy2(engine_assets.configure_js_path(), pkg / "configure.js")

    # --- tbpackage.json ---
    (pkg / "tbpackage.json").write_text(
        json.dumps(
            {
                "name": project.package_name,
                "packageShortName": project.package_name,
                "version": project.version,
                "description": project.description,
                "author": project.author,
                "isProtected": False,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    # --- scripts/ + icons/ (companions) ---
    globs_by_name = project.companion_globs()
    for name in sorted(project.script_names()):
        info = script_index.get(name)
        if info is None:
            report.warnings.append("script not found in source roots: " + name)
            continue
        cs: CompanionSet = resolve(info, globs_by_name.get(name))
        for f in cs.scripts:
            _copy(f, pkg / "scripts")
            report.scripts_bundled.append(f.name)
        for f in cs.icons:
            _copy(f, pkg / "icons")
            report.icons_written.append(f.name)
        for u in cs.unresolved:
            report.warnings.append("{}: could not resolve companion '{}'".format(name, u))
        if info.launcher_kind == "env_only":
            report.warnings.append(
                "{}: reads TOONBOOM_GLOBAL_SCRIPT_LOCATION with no __file__ fallback — "
                "keep that env var set on the target machine, or patch the script".format(name)
            )

    bundled_scripts = {p.stem for p in (pkg / "scripts").glob("*.js")}
    bundled_icons = {p.name for p in (pkg / "icons").iterdir() if p.is_file()}

    # --- toolbars/*.json + generated badges (naming from the real planner) ---
    for tb in project.toolbars:
        doc = {"$schema": "../engine/toolbar.schema.json"}
        doc.update({k: v for k, v in tb.items() if k != "$schema"})
        (pkg / "toolbars" / (tb["id"] + ".json")).write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report.toolbars.append(tb["id"])

        plan = planner.run_plan(
            {k: v for k, v in tb.items() if k != "$schema"},
            scripts=bundled_scripts,
            icons=bundled_icons,
            harmony_version=harmony_version,
        )
        for w in plan.get("warnings", []):
            if w.split(":")[0] not in ("ICON_MISSING",):
                report.warnings.append("{}: {}".format(tb["id"], w))
        for gi in plan.get("generatedIcons", []):
            dst = pkg / "icons" / gi["name"]
            if dst.exists():
                continue
            svg = icon_badges.badge_svg(
                icon_badges.abbreviate(gi["text"], 3), border=gi.get("border", False)
            )
            dst.write_text(svg + "\n", encoding="utf-8")
            report.badges_generated.append(gi["name"])
            report.icons_written.append(gi["name"])

    return report


# ------------------------------------------------------------------- helpers ---


def _copy(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst


def _index_from_roots(project) -> dict[str, ScriptInfo]:
    infos = scan_scripts([Path(p) for p in project.source_roots]) if project.source_roots else []
    return {i.name: i for i in infos}
