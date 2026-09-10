"""Headless smoke of the PySide6 window: it constructs, scripts populate, items
add/move, the preview runs the planner, and a build produces a package.

Dialog-driven actions (Open, Build to folder, Install) are exercised through the
non-dialog internals.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from customize_toolbars_builder.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(["test"])
    yield app


@pytest.fixture
def win(qapp, scripts_root):
    w = MainWindow()
    w.project.source_roots = [scripts_root]
    w._reload_scripts()
    return w


def test_scripts_populate_and_filter(win):
    from PySide6.QtCore import Qt

    assert win.scripts_list.count() == 3
    win.hide_helpers.setChecked(True)
    win.search.setText("pair")
    visible = [
        win.scripts_list.item(i).data(Qt.UserRole + 1)
        for i in range(win.scripts_list.count())
        if not win.scripts_list.item(i).isHidden()
    ]
    assert visible == ["LP_pair"]


def test_add_scripts_and_reorder(win):
    win.project.add_toolbar("LP Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()
    win._add_selected_scripts()

    items = win._current_toolbar()["items"]
    assert [it["script"] for it in items] == ["LP_envonly", "LP_pair", "LP_solo"]

    win.items_tree.setCurrentItem(win.items_tree.topLevelItem(0))
    win._move_item(1)
    assert [it["script"] for it in win._current_toolbar()["items"]][:2] == ["LP_pair", "LP_envonly"]

    win._remove_item()  # removes current (now index 1)
    assert len(win._current_toolbar()["items"]) == 2


def test_inspector_edits_item(win):
    win.project.add_toolbar("Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.item(0).setSelected(True)
    win._add_selected_scripts()
    win.items_tree.setCurrentItem(win.items_tree.topLevelItem(0))
    win._refresh_inspector()

    win.f_label.setText("Custom Label")
    win.f_shortcut.setText("Alt+K")
    win.f_companions.setPlainText("LP_*.py\n")
    win._commit_item()

    it = win._current_toolbar()["items"][0]
    assert it["label"] == "Custom Label"
    assert it["shortcut"] == "Alt+K"
    assert it["companions"] == ["LP_*.py"]


def test_preview_runs_planner(win):
    win.project.add_toolbar("Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()
    win._add_selected_scripts()
    win._refresh_preview()
    text = win.preview.toPlainText()
    assert "buttons" in text and "shortcuts" in text
    # env_only script surfaces a warning in the preview
    assert "LP_envonly" in text


def test_build_produces_package(win, tmp_path):
    win.project.add_toolbar("LP Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()
    win._add_selected_scripts()

    report = win._run_build(tmp_path / "out")
    assert report is not None
    pkg = tmp_path / "out" / "Customize_Toolbars"
    assert (pkg / "configure.js").is_file()
    assert (pkg / "toolbars" / "lp_rig.json").is_file()
    assert (pkg / "icons" / "_title-lp_rig.svg").is_file()


def test_meta_edits_write_through(win):
    win.project.add_toolbar("Rig", abbr="RIG", menu="Windows")
    win._refresh_toolbars()
    win.tb_title.setText("Rigging Bar")
    win.tb_abbr.setText("RGB")
    win._on_meta_changed()
    tb = win._current_toolbar()
    assert tb["title"] == "Rigging Bar"
    assert tb["abbr"] == "RGB"
    assert tb["menu"] == "Windows"

    win.tb_menu.setText("")            # clearing removes the key -> toolbar only
    win._on_meta_changed()
    assert "menu" not in win._current_toolbar()


def test_build_and_install_to_multiple_versions(win, tmp_path, monkeypatch):
    win.project.add_toolbar("LP Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()
    win._add_selected_scripts()

    t25 = tmp_path / "h25" / "packages"
    t27 = tmp_path / "h27" / "packages"
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window._pick_locations",
                        lambda parent: [t25, t27])
    shown = {}
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window._show_report",
                        lambda parent, report, extra="": shown.update(text=report.text() + extra))

    win._build(mode="install")

    assert (t25 / "Customize_Toolbars" / "configure.js").is_file()
    assert (t27 / "Customize_Toolbars" / "configure.js").is_file()
    assert "2 location(s)" in shown["text"]
    assert "Restart Harmony" in shown["text"]


def test_no_separator_button():
    # Harmony has no toolbar separator API — the button must be gone.
    src = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "ui" / "main_window.py"
    ).read_text(encoding="utf-8")
    assert "+ Separator" not in src


def test_no_build_menu_in_menubar(win):
    titles = [win.menuBar().actions()[i].text() for i in range(len(win.menuBar().actions()))]
    assert "&Build" not in titles and "Build" not in titles
    assert any("File" in t for t in titles)


def test_primary_button_is_build_for_fresh_project(win):
    assert "install" in win._primary_action.text().lower()
    assert win.mode_label.text() == ""


def test_left_panel_is_widest(win):
    sizes = win._splitter.sizes()
    assert sizes[0] >= sizes[1] >= sizes[2]


def test_items_tree_shows_icons(win):
    win.project.add_toolbar("Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()          # LP_solo (has icon), LP_pair/LP_envonly (none)
    win._add_selected_scripts()
    n = win.items_tree.topLevelItemCount()
    assert n == 3
    # every row gets an icon — real file for LP_solo, monogram badge for the rest
    for i in range(n):
        assert not win.items_tree.topLevelItem(i).icon(0).isNull()


def test_edit_installed_then_uninstall(win, tmp_path, monkeypatch):
    from customize_toolbars_builder.services import installer, package_writer

    # build + "install" into a fake packages folder
    win.project.add_toolbar("Rig", abbr="RIG")
    win._refresh_toolbars()
    win.scripts_list.selectAll()
    win._add_selected_scripts()
    report = win._run_build(tmp_path / "dist")
    pkgs = tmp_path / "roaming" / "packages"
    installer.install(report.package_dir, pkgs)

    monkeypatch.setattr(
        "customize_toolbars_builder.ui.main_window.discover_locations",
        lambda repo_root=None: [type("L", (), {"label": "Fake", "path": pkgs})()],
    )
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window._show_report",
                        lambda *a, **k: None)

    # open it back
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window._choose_one",
                        lambda parent, title, options: options[0][1])
    win._open_installed_dialog()
    assert [t["id"] for t in win.project.toolbars] == ["rig"]
    assert "editing" in win.windowTitle()
    # the primary button switched to a "save changes" action
    assert "Save" in win._primary_action.text()
    assert win._editing_installed == pkgs

    # "Save changes to Harmony" rebuilds + reinstalls over the same folder
    win.project.toolbar("rig")["title"] = "Rig EDITED"
    win._save_to_installed()
    import json
    saved = json.loads((pkgs / "Customize_Toolbars" / "toolbars" / "rig.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Rig EDITED"

    # uninstall it
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window._choose_many",
                        lambda parent, title, options: [__import__("pathlib").Path(options[0][1])])
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window.QMessageBox.question",
                        staticmethod(lambda *a, **k: __import__(
                            "PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.Yes))
    monkeypatch.setattr("customize_toolbars_builder.ui.main_window.QMessageBox.information",
                        staticmethod(lambda *a, **k: None))
    win._uninstall()
    assert not installer.is_installed(pkgs, "Customize_Toolbars")
