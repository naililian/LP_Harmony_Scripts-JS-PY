from customize_toolbars_builder.models.harmony_locations import discover_locations


def test_discovers_roaming_scripts_folders(fake_appdata):
    locs = discover_locations(appdata=fake_appdata, env={})
    paths = [str(loc.path) for loc in locs]
    assert all(p.endswith("packages") for p in paths)
    labels = " ".join(loc.label for loc in locs)
    assert "Harmony 25 Premium" in labels
    assert "Harmony 24 Premium" in labels
    assert "Harmony 25 Advanced" in labels


def test_roaming_packages_folder_not_yet_created_is_writable(fake_appdata):
    locs = discover_locations(appdata=fake_appdata, env={})
    loc = next(loc for loc in locs if "25 Premium" in loc.label)
    assert loc.exists is False          # packages/ subdir not created yet
    assert loc.writable is True         # parent is writable


def test_version_inferred_from_sibling_folders(tmp_path):
    """A version whose <NNNN>-scripts folder doesn't exist yet is still offered,
    inferred from 2700-layouts-xml / full-2700-pref siblings."""
    appdata = tmp_path / "AppData" / "Roaming"
    edition = appdata / "Toon Boom Animation" / "Toon Boom Harmony Premium"
    (edition / "2500-scripts").mkdir(parents=True)
    (edition / "2700-layouts-xml").mkdir()
    (edition / "full-2700-pref").mkdir()

    locs = discover_locations(appdata=appdata, env={})
    labels = {loc.label for loc in locs}
    assert any("Harmony 25" in l for l in labels)
    h27 = next(loc for loc in locs if "Harmony 27" in loc.label)
    assert h27.path.name == "packages"
    assert h27.path.parent.name == "2700-scripts"
    assert h27.exists is False
    assert h27.writable is True


def test_env_targets(fake_appdata, tmp_path):
    env = {
        "TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER": str(tmp_path / "ext"),
        "TOONBOOM_GLOBAL_SCRIPT_LOCATION": str(tmp_path / "glob"),
    }
    locs = discover_locations(appdata=fake_appdata, env=env)
    kinds = {loc.kind for loc in locs}
    assert {"roaming", "env", "global"} <= kinds
    glob_loc = next(loc for loc in locs if loc.kind == "global")
    assert glob_loc.path.name == "packages"


def test_repo_root_target(tmp_path):
    (tmp_path / "harmony" / "packages").mkdir(parents=True)
    locs = discover_locations(appdata=None, env={}, repo_root=tmp_path)
    assert len(locs) == 1
    assert locs[0].kind == "repo"
    assert locs[0].exists is True


def test_dedupes(tmp_path):
    env = {"TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER": str(tmp_path / "harmony" / "packages")}
    (tmp_path / "harmony" / "packages").mkdir(parents=True)
    locs = discover_locations(appdata=None, env=env, repo_root=tmp_path)
    assert len(locs) == 1  # same path via env + repo -> one entry
