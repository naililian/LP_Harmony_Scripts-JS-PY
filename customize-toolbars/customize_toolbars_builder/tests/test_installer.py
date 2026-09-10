import pytest

from customize_toolbars_builder.services import installer


def _fake_package(root, name="Customize_Toolbars"):
    pkg = root / name
    pkg.mkdir(parents=True)
    (pkg / "configure.js").write_text("// x\n", encoding="utf-8")
    (pkg / "engine").mkdir()
    return pkg


def test_install_and_is_installed(tmp_path):
    pkg = _fake_package(tmp_path / "src")
    target = tmp_path / "roaming" / "packages"

    assert installer.is_installed(target, "Customize_Toolbars") is False
    res = installer.install(pkg, target)
    assert res.replaced_existing is False
    assert installer.is_installed(target, "Customize_Toolbars") is True

    res2 = installer.install(pkg, target)
    assert res2.replaced_existing is True


def test_uninstall(tmp_path):
    pkg = _fake_package(tmp_path / "src")
    target = tmp_path / "roaming" / "packages"
    installer.install(pkg, target)

    assert installer.uninstall(target, "Customize_Toolbars") is True
    assert installer.is_installed(target, "Customize_Toolbars") is False
    assert installer.uninstall(target, "Customize_Toolbars") is False  # already gone


def test_uninstall_refuses_non_package_folder(tmp_path):
    target = tmp_path / "packages"
    stray = target / "Customize_Toolbars"
    stray.mkdir(parents=True)
    (stray / "notes.txt").write_text("not a package", encoding="utf-8")
    with pytest.raises(ValueError):
        installer.uninstall(target, "Customize_Toolbars")


def test_make_zip(tmp_path):
    pkg = _fake_package(tmp_path / "src")
    archive = installer.make_zip(pkg, tmp_path / "out.zip")
    assert archive.is_file() and archive.suffix == ".zip"
