import json

from customize_toolbars_builder.cli import main


def _project_file(tmp_path, scripts_root):
    proj = {
        "package": {"name": "Customize_Toolbars", "version": "0.3.0", "author": "LP"},
        "sourceRoots": [str(scripts_root)],
        "toolbars": [
            {"id": "rig", "abbr": "RIG", "title": "LP Rig",
             "items": [{"type": "script", "script": "LP_solo", "label": "Solo"}]}
        ],
    }
    path = tmp_path / "p.lptb.json"
    path.write_text(json.dumps(proj), encoding="utf-8")
    return path


def test_build_writes_package(tmp_path, scripts_root, capsys):
    path = _project_file(tmp_path, scripts_root)
    rc = main(["build", str(path), "--out", str(tmp_path / "dist")])
    assert rc == 0
    assert (tmp_path / "dist" / "Customize_Toolbars" / "configure.js").is_file()
    assert "toolbars: rig" in capsys.readouterr().out


def test_build_then_install(tmp_path, scripts_root, capsys):
    path = _project_file(tmp_path, scripts_root)
    target = tmp_path / "roaming" / "packages"
    rc = main(["build", str(path), "--out", str(tmp_path / "dist"), "--install", str(target)])
    assert rc == 0
    assert (target / "Customize_Toolbars" / "configure.js").is_file()
    out = capsys.readouterr().out
    assert "Restart Harmony" in out
    assert "Done" in out


def test_build_install_multiple_versions(tmp_path, scripts_root, capsys):
    path = _project_file(tmp_path, scripts_root)
    t24 = tmp_path / "h24" / "2400-scripts" / "packages"
    t25 = tmp_path / "h25" / "2500-scripts" / "packages"
    rc = main(["build", str(path), "--out", str(tmp_path / "dist"),
               "--install", str(t24), "--install", str(t25)])
    assert rc == 0
    assert (t24 / "Customize_Toolbars" / "configure.js").is_file()
    assert (t25 / "Customize_Toolbars" / "configure.js").is_file()


def test_build_zip(tmp_path, scripts_root):
    path = _project_file(tmp_path, scripts_root)
    zip_path = tmp_path / "out.zip"
    rc = main(["build", str(path), "--out", str(tmp_path / "dist"), "--zip", str(zip_path)])
    assert rc == 0
    assert zip_path.is_file()


def test_build_rejects_bad_config(tmp_path, scripts_root, capsys):
    proj = {
        "package": {"name": "Customize_Toolbars"},
        "sourceRoots": [str(scripts_root)],
        "toolbars": [{"id": "bad", "title": "Bad", "abbr": "WAYTOOLONG"}],
    }
    path = tmp_path / "bad.lptb.json"
    path.write_text(json.dumps(proj), encoding="utf-8")
    rc = main(["build", str(path), "--out", str(tmp_path / "dist")])
    assert rc == 2
    assert "Config errors" in capsys.readouterr().err


def test_scan(tmp_path, scripts_root, capsys):
    rc = main(["scan", str(scripts_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "LP_solo" in out and "env_only" in out


def test_locations_runs(capsys):
    rc = main(["locations"])
    assert rc in (0, 1)
