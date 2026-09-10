import json

from customize_toolbars_builder.models.toolbar_project import ToolbarProject, slugify


def test_add_toolbar_and_ids():
    p = ToolbarProject()
    tb = p.add_toolbar("LP Rig", abbr="rig")
    assert tb["id"] == "lp_rig"
    assert tb["abbr"] == "RIG"
    assert tb["items"] == []
    assert p.toolbar("lp_rig") is tb


def test_add_toolbar_rejects_duplicate():
    p = ToolbarProject()
    p.add_toolbar("Rig", id="rig")
    try:
        p.add_toolbar("Rig again", id="rig")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_script_names_and_companion_globs():
    p = ToolbarProject()
    p.toolbars = [
        {
            "id": "rig",
            "title": "Rig",
            "items": [
                "LP_a",
                "---",
                {"type": "script", "script": "LP_b", "companions": ["LP_b_*.py"]},
                {"type": "submenu", "label": "More", "items": ["LP_c"]},
            ],
        }
    ]
    assert p.script_names() == {"LP_a", "LP_b", "LP_c"}
    assert p.companion_globs() == {"LP_b": ["LP_b_*.py"]}


def test_file_round_trip(tmp_path):
    p = ToolbarProject(package_name="Customize_Toolbars", version="1.2.3", author="LP")
    p.source_roots = [tmp_path / "harmony"]
    p.add_toolbar("Rig", abbr="RIG", id="rig")
    p.toolbar("rig")["items"].append("LP_x")

    dst = tmp_path / "proj.lptb.json"
    p.to_file(dst)
    loaded = ToolbarProject.from_file(dst)

    assert loaded.version == "1.2.3"
    assert loaded.author == "LP"
    assert [str(r) for r in loaded.source_roots] == [str(tmp_path / "harmony")]
    assert loaded.toolbars == p.toolbars


def test_from_package(tmp_path):
    pkg = tmp_path / "Customize_Toolbars"
    (pkg / "toolbars").mkdir(parents=True)
    (pkg / "tbpackage.json").write_text(json.dumps({"name": "Customize_Toolbars", "version": "9.9"}), encoding="utf-8")
    (pkg / "toolbars" / "rig.json").write_text(
        json.dumps({"$schema": "../engine/toolbar.schema.json", "id": "rig", "title": "Rig", "items": ["LP_x"]}),
        encoding="utf-8",
    )
    loaded = ToolbarProject.from_package(pkg)
    assert loaded.version == "9.9"
    assert loaded.toolbars == [{"id": "rig", "title": "Rig", "items": ["LP_x"]}]


def test_validate_flags_bad_config():
    p = ToolbarProject()
    p.toolbars = [{"id": "ok", "title": "Ok", "items": ["LP_a"]},
                  {"id": "bad", "title": "Bad", "abbr": "TOOLONG"}]
    errors = p.validate()
    assert any("bad" in e for e in errors)
    assert not any("ok:" in e for e in errors)


def test_slugify():
    assert slugify("LP · Rig Tools!") == "lp_rig_tools"
