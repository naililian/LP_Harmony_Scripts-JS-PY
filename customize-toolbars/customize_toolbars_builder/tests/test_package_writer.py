import json

import pytest

from customize_toolbars_builder.models.script_index import scan_scripts
from customize_toolbars_builder.models.toolbar_project import ToolbarProject
from customize_toolbars_builder.services import engine_assets, package_writer, planner

jsonschema = pytest.importorskip("jsonschema")

_SCHEMA = json.loads(engine_assets.schema_path().read_text(encoding="utf-8"))


@pytest.fixture
def project(scripts_root):
    p = ToolbarProject(package_name="Customize_Toolbars", version="0.2.0", author="LP")
    p.source_roots = [scripts_root]
    p.add_toolbar("LP Rig", abbr="RIG", id="rig")
    p.toolbar("rig")["items"] = [
        {"type": "script", "script": "LP_solo", "label": "Solo"},          # has convention icon
        {"type": "script", "script": "LP_pair", "label": "The Pair"},      # no icon -> monogram
        {"type": "script", "script": "LP_envonly", "label": "Env Only"},   # flagged
    ]
    return p


def test_writes_full_structure(project, tmp_path):
    report = package_writer.write_package(project, tmp_path / "dist")
    pkg = report.package_dir
    assert pkg == tmp_path / "dist" / "Customize_Toolbars"

    assert (pkg / "configure.js").is_file()
    for name in engine_assets.ENGINE_FILES:
        assert (pkg / "engine" / name).is_file()
    assert (pkg / "toolbars" / "rig.json").is_file()

    meta = json.loads((pkg / "tbpackage.json").read_text(encoding="utf-8"))
    assert meta["version"] == "0.2.0" and meta["name"] == "Customize_Toolbars"


def test_bundles_scripts_and_companions(project, tmp_path):
    package_writer.write_package(project, tmp_path / "dist")
    scripts = {p.name for p in (tmp_path / "dist" / "Customize_Toolbars" / "scripts").iterdir()}
    assert scripts == {
        "LP_solo.js",
        "LP_pair.js", "LP_pair.py",
        "LP_envonly.js", "LP_envonly.py", "LP_envonly.ui",
    }


def test_icons_convention_plus_generated_badges(project, tmp_path):
    report = package_writer.write_package(project, tmp_path / "dist")
    icons = {p.name for p in (tmp_path / "dist" / "Customize_Toolbars" / "icons").iterdir()}
    assert "LP_solo.png" in icons              # convention icon copied
    assert "_title-rig.svg" in icons           # title badge (abbr RIG)
    assert "_mono-the_pair.svg" in icons       # LP_pair had no icon
    assert "_mono-solo.svg" not in icons       # LP_solo had one
    assert set(report.badges_generated) == {"_title-rig.svg", "_mono-the_pair.svg", "_mono-env_only.svg"}


def test_envonly_warning_surfaced(project, tmp_path):
    report = package_writer.write_package(project, tmp_path / "dist")
    assert any("LP_envonly" in w and "TOONBOOM_GLOBAL_SCRIPT_LOCATION" in w for w in report.warnings)


def test_generated_config_validates_and_plans_clean(project, tmp_path):
    package_writer.write_package(project, tmp_path / "dist")
    pkg = tmp_path / "dist" / "Customize_Toolbars"

    cfg = json.loads((pkg / "toolbars" / "rig.json").read_text(encoding="utf-8"))
    jsonschema.validators.validator_for(_SCHEMA)(_SCHEMA).validate(cfg)

    bundled_scripts = {p.stem for p in (pkg / "scripts").glob("*.js")}
    bundled_icons = {p.name for p in (pkg / "icons").iterdir()}
    cfg.pop("$schema", None)
    plan = planner.run_plan(cfg, scripts=bundled_scripts, icons=bundled_icons)

    assert plan["ok"] is True
    blocking = [w for w in plan["warnings"] if w.split(":")[0] != "ICON_MISSING"]
    assert blocking == []
    # every generated icon the planner wants now exists in the package
    for gi in plan["generatedIcons"]:
        assert (pkg / "icons" / gi["name"]).is_file()


def test_missing_script_is_warned_not_fatal(scripts_root, tmp_path):
    p = ToolbarProject(source_roots=[scripts_root])
    p.add_toolbar("Rig", id="rig")
    p.toolbar("rig")["items"] = ["LP_does_not_exist"]
    report = package_writer.write_package(p, tmp_path / "dist")
    assert any("LP_does_not_exist" in w for w in report.warnings)
    assert (tmp_path / "dist" / "Customize_Toolbars" / "configure.js").is_file()


def test_rebuild_is_idempotent(project, tmp_path):
    r1 = package_writer.write_package(project, tmp_path / "dist")
    files1 = sorted(p.relative_to(r1.package_dir).as_posix() for p in r1.package_dir.rglob("*") if p.is_file())
    r2 = package_writer.write_package(project, tmp_path / "dist")
    files2 = sorted(p.relative_to(r2.package_dir).as_posix() for p in r2.package_dir.rglob("*") if p.is_file())
    assert files1 == files2
