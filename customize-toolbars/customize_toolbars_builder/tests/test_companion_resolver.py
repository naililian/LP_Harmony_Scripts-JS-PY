from customize_toolbars_builder.models.script_index import scan_scripts
from customize_toolbars_builder.services.companion_resolver import resolve, resolve_all


def _info(scripts_root, name):
    return next(i for i in scan_scripts([scripts_root]) if i.name == name)


def test_solo_bundles_just_the_js_and_reports_icon(scripts_root):
    cs = resolve(_info(scripts_root, "LP_solo"))
    assert [p.name for p in cs.scripts] == ["LP_solo.js"]
    assert [p.name for p in cs.icons] == ["LP_solo.png"]
    assert cs.unresolved == []


def test_pair_bundles_py_sibling(scripts_root):
    cs = resolve(_info(scripts_root, "LP_pair"))
    names = sorted(p.name for p in cs.scripts)
    assert names == ["LP_pair.js", "LP_pair.py"]


def test_envonly_bundles_py_and_ui(scripts_root):
    cs = resolve(_info(scripts_root, "LP_envonly"))
    names = sorted(p.name for p in cs.scripts)
    assert names == ["LP_envonly.js", "LP_envonly.py", "LP_envonly.ui"]


def test_extra_globs(scripts_root):
    (scripts_root / "LP_pair_helper.py").write_text("x=1\n", encoding="utf-8")
    (scripts_root / "LP_pair_data.json").write_text("{}\n", encoding="utf-8")
    cs = resolve(_info(scripts_root, "LP_pair"), extra_globs=["LP_pair_*.py", "LP_pair_*.json"])
    names = sorted(p.name for p in cs.scripts)
    assert "LP_pair_helper.py" in names and "LP_pair_data.json" in names


def test_unresolved_glob_reported(scripts_root):
    cs = resolve(_info(scripts_root, "LP_solo"), extra_globs=["nothing_matches_*.py"])
    assert cs.unresolved == ["nothing_matches_*.py"]


def test_resolve_all(scripts_root):
    infos = scan_scripts([scripts_root])
    sets = resolve_all(infos, {"LP_pair": ["LP_pair_*.py"]})
    assert set(sets) == {"LP_solo", "LP_pair", "LP_envonly"}
