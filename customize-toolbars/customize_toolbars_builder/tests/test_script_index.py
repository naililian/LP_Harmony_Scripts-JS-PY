from customize_toolbars_builder.models.script_index import describe_script, scan_scripts


def test_scan_finds_all_and_sorts(scripts_root):
    infos = scan_scripts([scripts_root])
    assert [i.name for i in infos] == ["LP_envonly", "LP_pair", "LP_solo"]


def test_plain_launcher(scripts_root):
    info = next(i for i in scan_scripts([scripts_root]) if i.name == "LP_solo")
    assert info.launcher_kind == "plain"
    assert info.entry == "LP_solo"
    assert info.has_py is False
    assert info.icon and info.icon.name == "LP_solo.png"
    assert info.portable is True


def test_pair_launcher_is_portable_and_refs_py(scripts_root):
    info = next(i for i in scan_scripts([scripts_root]) if i.name == "LP_pair")
    assert info.launcher_kind == "file_fallback"
    assert info.has_py is True
    assert "LP_pair.py" in info.sibling_refs
    assert info.portable is True


def test_envonly_launcher_flagged_not_portable(scripts_root):
    info = next(i for i in scan_scripts([scripts_root]) if i.name == "LP_envonly")
    assert info.launcher_kind == "env_only"
    assert info.portable is False
    assert [p.name for p in info.ui_files] == ["LP_envonly.ui"]


def test_later_root_wins_on_name_collision(scripts_root, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "LP_solo.js").write_text("function LP_solo(){}\n", encoding="utf-8")
    infos = scan_scripts([scripts_root, other])
    solo = next(i for i in infos if i.name == "LP_solo")
    assert solo.root == other


def test_describe_real_repo_script():
    # sanity against a real launcher in the repo
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    js = repo / "harmony" / "LP_deformer_tool.js"
    if not js.is_file():
        return
    info = describe_script(js, js.parent)
    assert info.launcher_kind in {"file_fallback", "plain", "require_run", "unknown"}
    assert info.icon is not None  # harmony/script-icons/LP_deformer_tool.png exists
