"""The builder window: pick scripts (left) -> arrange toolbars (centre) ->
edit the selected item + preview what Harmony will register (right).

State lives in one ``ToolbarProject``; widgets read and write its dicts directly
so it is always current. Heavy work (scan, plan, write) is synchronous — the data
sets are small.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QSplitter, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..models.harmony_locations import discover_locations
from ..models.script_index import ScriptInfo, scan_scripts
from ..models.toolbar_project import ToolbarProject, slugify
from ..services import icon_badges, installer, package_writer, planner

_ITEM_ROLE = Qt.UserRole + 1


def _repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "harmony" / "packages").is_dir():
            return parent
    return None


class MainWindow(QMainWindow):
    def __init__(self, project_path: str | None = None):
        super().__init__()
        self.setWindowTitle("Customize Toolbars Builder")
        self.resize(1400, 880)

        self.project = ToolbarProject()
        self.project_path: Path | None = None
        self._editing_installed: Path | None = None  # packages folder we loaded from
        self.script_index: dict[str, ScriptInfo] = {}
        self._preview_timer = QTimer(self, singleShot=True, interval=180)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self._build_menu()
        self._build_ui()

        if project_path:
            self._load_project(Path(project_path))
        else:
            repo = _repo_root()
            if repo:
                self.project.source_roots = [repo / "harmony"]
            self._reload_scripts()
            self._refresh_toolbars()

    # ------------------------------------------------------------- chrome ---

    def _build_menu(self) -> None:
        m = self.menuBar().addMenu("&File")
        self._act("New project", m, self._new_project, "Ctrl+N")
        self._act("Open project…  (.lptb.json)", m, self._open_project_dialog, "Ctrl+O")
        self._act("Edit an installed toolbar package…", m, self._open_installed_dialog)
        self._act("Open a package folder…", m, self._open_package_dialog)
        m.addSeparator()
        self._act("Save project", m, self._save_project, "Ctrl+S")
        self._act("Save project as…", m, self._save_project_as)

    def _act(self, text, menu, slot, shortcut=None) -> QAction:
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        menu.addAction(a)
        return a

    def _build_ui(self) -> None:
        split = QSplitter(Qt.Horizontal)
        split.addWidget(self._scripts_panel())
        split.addWidget(self._toolbars_panel())
        split.addWidget(self._inspector_panel())
        split.setStretchFactor(0, 6)
        split.setStretchFactor(1, 5)
        split.setStretchFactor(2, 3)
        split.setSizes([580, 500, 300])
        self._splitter = split

        central = QWidget()
        col = QVBoxLayout(central)
        col.setContentsMargins(8, 8, 8, 6)
        col.addWidget(split, 1)

        footer = QHBoxLayout()
        self.mode_label = QLabel("")
        self.mode_label.setProperty("role", "hint")
        footer.addWidget(self.mode_label)
        footer.addStretch(1)

        self.build_btn = QToolButton()
        self.build_btn.setProperty("accent", "true")
        self.build_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self.build_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.build_btn.setMinimumWidth(190)
        self.build_btn.setMinimumHeight(30)
        self._primary_action = QAction("Build…", self)
        self.build_btn.setDefaultAction(self._primary_action)

        menu = QMenu(self.build_btn)
        menu.addAction("Build to folder…", lambda: self._build(mode="folder"))
        menu.addAction("Build && install…", lambda: self._build(mode="install"))
        menu.addAction("Export .zip…", lambda: self._build(mode="zip"))
        menu.addSeparator()
        menu.addAction("Uninstall from Harmony…", self._uninstall)
        self.build_btn.setMenu(menu)
        footer.addWidget(self.build_btn)
        col.addLayout(footer)
        self._update_primary_button()

        self.setCentralWidget(central)

        credit = QLabel("Created by Lilian Penzo")
        credit.setProperty("role", "hint")
        credit.setContentsMargins(0, 0, 8, 0)
        self.statusBar().addPermanentWidget(credit)
        self.statusBar().showMessage("New project")

    # --------------------------------------------------------- left panel ---

    def _scripts_panel(self) -> QWidget:
        box = QGroupBox("Scripts")
        box.setMinimumWidth(360)
        v = QVBoxLayout(box)

        self.roots_list = QListWidget()
        self.roots_list.setMaximumHeight(70)
        v.addWidget(self.roots_list)
        row = QHBoxLayout()
        add_root = QPushButton("Add folder…")
        add_root.clicked.connect(self._add_root)
        rm_root = QPushButton("Remove")
        rm_root.clicked.connect(self._remove_root)
        row.addWidget(add_root)
        row.addWidget(rm_root)
        row.addStretch()
        v.addLayout(row)

        self.search = QLineEdit(placeholderText="filter…")
        self.search.textChanged.connect(self._filter_scripts)
        v.addWidget(self.search)

        self.hide_helpers = QCheckBox("hide non-launchers")
        self.hide_helpers.setChecked(True)
        self.hide_helpers.toggled.connect(self._filter_scripts)
        v.addWidget(self.hide_helpers)

        self.scripts_list = QListWidget()
        self.scripts_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.scripts_list.itemDoubleClicked.connect(lambda *_: self._add_selected_scripts())
        v.addWidget(self.scripts_list, 1)

        self.add_btn = QPushButton("Add to toolbar  ▶")
        self.add_btn.setProperty("accent", "true")
        self.add_btn.clicked.connect(self._add_selected_scripts)
        v.addWidget(self.add_btn)
        return box

    def _reload_scripts(self) -> None:
        self.roots_list.clear()
        for r in self.project.source_roots:
            self.roots_list.addItem(str(r))
        infos = scan_scripts(self.project.source_roots) if self.project.source_roots else []
        self.script_index = {i.name: i for i in infos}
        self._populate_scripts()

    def _populate_scripts(self) -> None:
        self.scripts_list.clear()
        for info in sorted(self.script_index.values(), key=lambda i: i.name.lower()):
            launcher = info.launcher_kind in ("file_fallback", "env_only", "plain", "require_run")
            tags = []
            if not info.icon:
                tags.append("no-icon")
            if info.launcher_kind == "env_only":
                tags.append("env-only")
            if not launcher:
                tags.append(info.launcher_kind)
            label = info.name + ("   " + " · ".join(tags) if tags else "")
            it = QListWidgetItem(label)
            it.setData(_ITEM_ROLE, info.name)
            it.setData(Qt.UserRole + 2, launcher)
            if info.icon:
                it.setIcon(QIcon(str(info.icon)))  # QtSvg handles .svg too
            self.scripts_list.addItem(it)
        self._filter_scripts()

    def _filter_scripts(self) -> None:
        needle = self.search.text().lower()
        hide = self.hide_helpers.isChecked()
        for i in range(self.scripts_list.count()):
            it = self.scripts_list.item(i)
            launcher = it.data(Qt.UserRole + 2)
            it.setHidden((needle and needle not in it.text().lower()) or (hide and not launcher))

    def _add_root(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Scripts folder")
        if d:
            self.project.source_roots.append(Path(d))
            self._reload_scripts()

    def _remove_root(self) -> None:
        row = self.roots_list.currentRow()
        if 0 <= row < len(self.project.source_roots):
            self.project.source_roots.pop(row)
            self._reload_scripts()

    def _add_selected_scripts(self) -> None:
        tb = self._current_toolbar()
        if tb is None:
            QMessageBox.information(self, "No toolbar", "Create a toolbar first.")
            return
        names = [it.data(_ITEM_ROLE) for it in self.scripts_list.selectedItems()]
        for name in names:
            info = self.script_index.get(name)
            item = {"type": "script", "script": name, "label": _nice_label(name)}
            if info and info.entry != name:
                item["entry"] = info.entry
            tb.setdefault("items", []).append(item)
        self._refresh_items()
        self._queue_preview()

    # ------------------------------------------------------- centre panel ---

    def _toolbars_panel(self) -> QWidget:
        box = QGroupBox("Toolbars")
        v = QVBoxLayout(box)

        row = QHBoxLayout()
        self.toolbar_combo = QComboBox()
        self.toolbar_combo.currentIndexChanged.connect(self._on_toolbar_selected)
        row.addWidget(self.toolbar_combo, 1)
        new_tb = QPushButton("New")
        new_tb.clicked.connect(self._new_toolbar)
        del_tb = QPushButton("Delete")
        del_tb.clicked.connect(self._delete_toolbar)
        row.addWidget(new_tb)
        row.addWidget(del_tb)
        v.addLayout(row)

        meta = QFormLayout()
        self.tb_title = QLineEdit()
        self.tb_abbr = QLineEdit(maxLength=3)
        self.tb_menu = QLineEdit(placeholderText="blank = toolbar only  ·  e.g. Windows to add a menu group")
        self.tb_shortcat = QLineEdit(placeholderText="defaults to title")
        for w in (self.tb_title, self.tb_abbr, self.tb_menu, self.tb_shortcat):
            w.editingFinished.connect(self._on_meta_changed)
        meta.addRow("Title", self.tb_title)
        meta.addRow("Abbr (badge)", self.tb_abbr)
        meta.addRow("Menu", self.tb_menu)
        meta.addRow("Shortcut cat.", self.tb_shortcat)
        v.addLayout(meta)

        self.items_tree = QTreeWidget()
        self.items_tree.setHeaderLabels(["item", "kind"])
        self.items_tree.setRootIsDecorated(False)
        self.items_tree.setIconSize(QSize(22, 22))
        self.items_tree.currentItemChanged.connect(lambda *_: self._refresh_inspector())
        v.addWidget(self.items_tree, 1)

        btns = QHBoxLayout()
        for text, slot in [
            ("▲", lambda: self._move_item(-1)),
            ("▼", lambda: self._move_item(1)),
            ("Remove", self._remove_item),
            ("+ Submenu", self._add_submenu),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        v.addLayout(btns)
        return box

    def _refresh_toolbars(self) -> None:
        self.toolbar_combo.blockSignals(True)
        self.toolbar_combo.clear()
        for tb in self.project.toolbars:
            self.toolbar_combo.addItem("{}  ({})".format(tb.get("title", tb["id"]), tb["id"]))
        self.toolbar_combo.blockSignals(False)
        self._on_toolbar_selected()

    def _current_toolbar(self) -> dict | None:
        i = self.toolbar_combo.currentIndex()
        if 0 <= i < len(self.project.toolbars):
            return self.project.toolbars[i]
        return None

    def _on_toolbar_selected(self) -> None:
        tb = self._current_toolbar()
        for w in (self.tb_title, self.tb_abbr, self.tb_menu, self.tb_shortcat):
            w.blockSignals(True)
        if tb:
            self.tb_title.setText(tb.get("title", ""))
            self.tb_abbr.setText(tb.get("abbr", ""))
            self.tb_menu.setText(tb.get("menu") or "")
            self.tb_shortcat.setText(tb.get("shortcutCategory", ""))
        else:
            for w in (self.tb_title, self.tb_abbr, self.tb_menu, self.tb_shortcat):
                w.clear()
        for w in (self.tb_title, self.tb_abbr, self.tb_menu, self.tb_shortcat):
            w.blockSignals(False)
        self._refresh_items()
        self._queue_preview()

    def _on_meta_changed(self) -> None:
        tb = self._current_toolbar()
        if tb is None:
            return
        tb["title"] = self.tb_title.text().strip() or tb["id"]
        abbr = self.tb_abbr.text().strip().upper()
        if abbr:
            tb["abbr"] = abbr
        else:
            tb.pop("abbr", None)
        menu = self.tb_menu.text().strip()
        if menu:
            tb["menu"] = menu
        else:
            tb.pop("menu", None)
        cat = self.tb_shortcat.text().strip()
        if cat:
            tb["shortcutCategory"] = cat
        else:
            tb.pop("shortcutCategory", None)
        idx = self.toolbar_combo.currentIndex()
        self.toolbar_combo.setItemText(idx, "{}  ({})".format(tb["title"], tb["id"]))
        self._queue_preview()

    def _new_toolbar(self) -> None:
        title, ok = _prompt(self, "New toolbar", "Title:")
        if not ok or not title.strip():
            return
        abbr, _ = _prompt(self, "New toolbar", "Abbr (1–3 letters):", (title.strip()[:3]).upper())
        try:
            self.project.add_toolbar(title.strip(), abbr=abbr.strip() or None)
        except ValueError as e:
            QMessageBox.warning(self, "Cannot add", str(e))
            return
        self._refresh_toolbars()
        self.toolbar_combo.setCurrentIndex(len(self.project.toolbars) - 1)

    def _delete_toolbar(self) -> None:
        tb = self._current_toolbar()
        if tb and QMessageBox.question(self, "Delete", "Delete toolbar '%s'?" % tb["id"]) == QMessageBox.Yes:
            self.project.remove_toolbar(tb["id"])
            self._refresh_toolbars()

    def _refresh_items(self) -> None:
        self.items_tree.clear()
        tb = self._current_toolbar()
        if tb is None:
            return
        for it in tb.get("items", []):
            row = _tree_row(it)
            icon = self._icon_for_item(it, tb)
            if icon is not None:
                row.setIcon(0, icon)
            self.items_tree.addTopLevelItem(row)
        self.items_tree.resizeColumnToContents(0)

    def _icon_for_item(self, item, toolbar) -> "QIcon | None":
        """The icon Harmony will actually show for this item — real file or the
        generated monogram badge."""
        if not isinstance(item, dict) or item.get("type") != "script":
            return None
        script = item.get("script")
        explicit = item.get("icon")
        if explicit:
            for root in self.project.source_roots:
                for sub in ("script-icons", "icons"):
                    p = Path(root) / sub / explicit
                    if p.is_file():
                        return QIcon(str(p))
        info = self.script_index.get(script)
        if info is not None and info.icon is not None:
            return QIcon(str(info.icon))
        if (toolbar or {}).get("iconFallback") == "none":
            return None
        svg = icon_badges.badge_svg(
            icon_badges.abbreviate(item.get("label") or script or "?", 3), border=False
        )
        return _svg_icon(svg)

    def _selected_item_index(self) -> int:
        return self.items_tree.indexOfTopLevelItem(self.items_tree.currentItem()) if self.items_tree.currentItem() else -1

    def _append_item(self, item: dict) -> None:
        tb = self._current_toolbar()
        if tb is None:
            return
        tb.setdefault("items", []).append(item)
        self._refresh_items()
        self._queue_preview()

    def _add_submenu(self) -> None:
        label, ok = _prompt(self, "Submenu", "Label:")
        if ok and label.strip():
            self._append_item({"type": "submenu", "label": label.strip(), "items": []})

    def _move_item(self, delta: int) -> None:
        tb = self._current_toolbar()
        i = self._selected_item_index()
        if tb is None or i < 0:
            return
        items = tb["items"]
        j = i + delta
        if 0 <= j < len(items):
            items[i], items[j] = items[j], items[i]
            self._refresh_items()
            self.items_tree.setCurrentItem(self.items_tree.topLevelItem(j))
            self._queue_preview()

    def _remove_item(self) -> None:
        tb = self._current_toolbar()
        i = self._selected_item_index()
        if tb is not None and 0 <= i < len(tb["items"]):
            tb["items"].pop(i)
            self._refresh_items()
            self._queue_preview()

    # -------------------------------------------------------- right panel ---

    def _inspector_panel(self) -> QWidget:
        wrap = QWidget()
        wrap.setMinimumWidth(260)
        wrap.setMaximumWidth(400)
        v = QVBoxLayout(wrap)

        self.item_box = QGroupBox("Item")
        form = QFormLayout(self.item_box)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.f_label = QLineEdit()
        self.f_icon = QLineEdit(placeholderText="blank = auto")
        self.f_shortcut = QLineEdit(placeholderText="e.g. Alt+D")
        self.f_toolbar = QCheckBox("show on toolbar")
        self.f_menu = QCheckBox("show in menu")
        self.f_companions = QPlainTextEdit(placeholderText="extra file globs,\none per line")
        self.f_companions.setMaximumHeight(70)
        for w in (self.f_label, self.f_icon, self.f_shortcut):
            w.editingFinished.connect(self._commit_item)
        self.f_toolbar.toggled.connect(self._commit_item)
        self.f_menu.toggled.connect(self._commit_item)
        self.f_companions.textChanged.connect(self._commit_item)
        form.addRow("Label", self.f_label)
        form.addRow("Icon", self.f_icon)
        form.addRow("Shortcut", self.f_shortcut)
        form.addRow("", self.f_toolbar)
        form.addRow("", self.f_menu)
        form.addRow("Companions", self.f_companions)
        self.icon_hint = QLabel()
        self.icon_hint.setProperty("role", "hint")
        self.icon_hint.setWordWrap(True)
        form.addRow("", self.icon_hint)
        v.addWidget(self.item_box)

        prev = QGroupBox("Registers in Harmony")
        pv = QVBoxLayout(prev)
        self.preview = QPlainTextEdit(readOnly=True)
        pv.addWidget(self.preview)
        v.addWidget(prev, 1)
        return wrap

    def _current_item(self) -> dict | None:
        tb = self._current_toolbar()
        i = self._selected_item_index()
        if tb is not None and 0 <= i < len(tb.get("items", [])):
            return tb["items"][i]
        return None

    def _refresh_inspector(self) -> None:
        it = self._current_item()
        editable = isinstance(it, dict) and it.get("type") == "script"
        self.item_box.setEnabled(editable)
        for w in (self.f_label, self.f_icon, self.f_shortcut, self.f_companions):
            w.blockSignals(True)
        self.f_toolbar.blockSignals(True)
        self.f_menu.blockSignals(True)
        if editable:
            self.f_label.setText(it.get("label", ""))
            self.f_icon.setText(it.get("icon", ""))
            self.f_shortcut.setText(it.get("shortcut", ""))
            self.f_toolbar.setChecked(it.get("toolbar", True))
            self.f_menu.setChecked(it.get("menu", True))
            self.f_companions.setPlainText("\n".join(it.get("companions", [])))
            info = self.script_index.get(it.get("script"))
            if it.get("icon"):
                self.icon_hint.setText("using: icons/" + it["icon"])
            elif info and info.icon:
                self.icon_hint.setText("auto: " + info.icon.name + "  (from " + info.icon.parent.name + "/)")
            else:
                self.icon_hint.setText("auto: generated letter badge (no icon found for this script)")
        else:
            for w in (self.f_label, self.f_icon, self.f_shortcut):
                w.clear()
            self.f_companions.clear()
            self.icon_hint.setText("")
        for w in (self.f_label, self.f_icon, self.f_shortcut, self.f_companions):
            w.blockSignals(False)
        self.f_toolbar.blockSignals(False)
        self.f_menu.blockSignals(False)

    def _commit_item(self) -> None:
        it = self._current_item()
        if not isinstance(it, dict) or it.get("type") != "script":
            return
        _set_or_drop(it, "label", self.f_label.text().strip())
        _set_or_drop(it, "icon", self.f_icon.text().strip())
        _set_or_drop(it, "shortcut", self.f_shortcut.text().strip())
        it["toolbar"] = self.f_toolbar.isChecked()
        it["menu"] = self.f_menu.isChecked()
        if it["toolbar"]:
            it.pop("toolbar", None)
        if it["menu"]:
            it.pop("menu", None)
        globs = [g.strip() for g in self.f_companions.toPlainText().splitlines() if g.strip()]
        if globs:
            it["companions"] = globs
        else:
            it.pop("companions", None)
        row = self.items_tree.currentItem()
        if row:
            row.setText(0, it.get("label") or it["script"])
            icon = self._icon_for_item(it, self._current_toolbar())
            row.setIcon(0, icon if icon is not None else QIcon())
        self._queue_preview()

    def _queue_preview(self) -> None:
        self._preview_timer.start()

    def _refresh_preview(self) -> None:
        tb = self._current_toolbar()
        if tb is None:
            self.preview.setPlainText("")
            return
        cfg = {k: v for k, v in tb.items() if k != "$schema"}
        have = set(self.script_index)
        icons = {(i.icon.name) for i in self.script_index.values() if i.icon}
        try:
            plan = planner.run_plan(cfg, scripts=have, icons=icons)
        except Exception as e:  # pragma: no cover - defensive
            self.preview.setPlainText("planner error: %s" % e)
            return
        lines = []
        if not plan.get("ok", True):
            lines.append("!! config produced no plan")
        buttons = plan["toolbar"]["buttons"]
        lines.append("toolbar '%s' — %d buttons, %d shortcuts, %d menu items" % (
            plan["title"], len(buttons), len(plan["shortcuts"]), len(plan["menuItems"])))
        lines.append("")
        for b in buttons:
            lines.append("  [%s] %s" % (b.get("icon", ""), b["text"]))
        warns = [w for w in plan.get("warnings", []) if w.split(":")[0] != "ICON_MISSING"]
        for it in _scripts_in(tb):
            info = self.script_index.get(it)
            if info is None:
                warns.append("%s: not found in source roots" % it)
            elif info.launcher_kind == "env_only":
                warns.append("%s: reads TOONBOOM_GLOBAL_SCRIPT_LOCATION directly — "
                             "not portable without that env var / a shim" % it)
        if warns:
            lines.append("")
            lines += ["! " + w for w in warns]
        self.preview.setPlainText("\n".join(lines))

        errors = self.project.validate()
        self.statusBar().showMessage(
            "%d toolbar(s), %d script(s)" % (len(self.project.toolbars), len(self.project.script_names()))
            + ("   —   %d config error(s)" % len(errors) if errors else "   —   ok")
        )

    # ------------------------------------------------------------- files ---

    def _new_project(self) -> None:
        self.project = ToolbarProject()
        repo = _repo_root()
        if repo:
            self.project.source_roots = [repo / "harmony"]
        self.project_path = None
        self._editing_installed = None
        self.setWindowTitle("Customize Toolbars Builder")
        self._reload_scripts()
        self._refresh_toolbars()
        self._update_primary_button()

    def _open_project_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Open project", "", "Project (*.lptb.json *.json)")
        if f:
            self._load_project(Path(f))

    def _load_project(self, path: Path) -> None:
        try:
            self.project = ToolbarProject.from_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return
        self.project_path = path
        self._editing_installed = None
        self.setWindowTitle("Customize Toolbars Builder — " + path.name)
        self._reload_scripts()
        self._refresh_toolbars()
        self._update_primary_button()

    def _load_package(self, folder: str | Path) -> None:
        folder = Path(folder)
        try:
            self.project = ToolbarProject.from_package(folder)
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return
        self.project_path = None
        # folder is <packages_dir>/<PackageName> — remember the packages_dir
        self._editing_installed = folder.parent
        self.setWindowTitle("Customize Toolbars Builder — editing %s" % folder.name)
        repo = _repo_root()
        if repo and not self.project.source_roots:
            self.project.source_roots = [repo / "harmony"]
        self._reload_scripts()
        self._refresh_toolbars()
        self._update_primary_button()

    def _open_package_dialog(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Open a package folder (contains configure.js)")
        if d:
            self._load_package(d)

    def _installed_packages(self) -> list[tuple[str, Path]]:
        """(label, packages_folder) for every discovered location that already
        holds this package."""
        name = self.project.package_name
        return [
            (loc.label, loc.path)
            for loc in discover_locations(repo_root=_repo_root())
            if installer.is_installed(loc.path, name)
        ]

    def _open_installed_dialog(self) -> None:
        found = self._installed_packages()
        if not found:
            QMessageBox.information(
                self, "Nothing installed",
                "No '%s' package found in any Harmony version.\n\n"
                "Use File ▸ Open a package folder… to browse to one." % self.project.package_name,
            )
            return
        pick = _choose_one(self, "Edit which installed package?",
                           [(lbl, str(path)) for lbl, path in found])
        if pick:
            self._load_package(Path(pick) / self.project.package_name)

    def _save_project(self) -> None:
        if self.project_path is None:
            self._save_project_as()
            return
        self.project.to_file(self.project_path)
        self.statusBar().showMessage("saved " + self.project_path.name, 3000)

    def _save_project_as(self) -> None:
        f, _ = QFileDialog.getSaveFileName(self, "Save project", "Customize_Toolbars.lptb.json", "Project (*.lptb.json)")
        if f:
            self.project_path = Path(f)
            self.setWindowTitle("Customize Toolbars Builder — " + self.project_path.name)
            self._save_project()

    # ------------------------------------------------------------- build ---

    def _update_primary_button(self) -> None:
        """The bottom-right button reflects the mode: fresh project builds, an
        opened installed package updates itself."""
        try:
            self._primary_action.triggered.disconnect()
        except (RuntimeError, TypeError):
            pass
        if self._editing_installed is not None:
            self._primary_action.setText("Save changes to Harmony")
            self._primary_action.setToolTip("Rebuild and reinstall over " + str(self._editing_installed))
            self._primary_action.triggered.connect(self._save_to_installed)
            self.mode_label.setText("● editing installed package")
        else:
            self._primary_action.setText("Build && install…")
            self._primary_action.setToolTip("")
            self._primary_action.triggered.connect(lambda: self._build(mode="install"))
            self.mode_label.setText("")

    def _save_to_installed(self) -> None:
        """Rebuild and reinstall over the package the project was opened from."""
        target = self._editing_installed
        if target is None:
            return self._build(mode="install")
        errors = self.project.validate()
        if errors and QMessageBox.warning(
            self, "Config errors", "\n".join(errors) + "\n\nSave anyway?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.No:
            return
        if not self.project.toolbars:
            QMessageBox.information(self, "Nothing to save", "The package has no toolbars.")
            return
        report = self._run_build(Path(tempfile.mkdtemp()))
        if not report:
            return
        res = installer.install(report.package_dir, target)
        _show_report(self, report,
                     "Saved to %s\nRestart Harmony to see the changes." % res.destination)
        self.statusBar().showMessage("Saved to " + str(target), 6000)

    def _build(self, mode: str) -> None:
        errors = self.project.validate()
        if errors and QMessageBox.warning(
            self, "Config errors", "\n".join(errors) + "\n\nBuild anyway?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.No:
            return
        if not self.project.toolbars:
            QMessageBox.information(self, "Nothing to build", "Add a toolbar first.")
            return

        if mode == "folder":
            out = QFileDialog.getExistingDirectory(self, "Build into folder")
            if not out:
                return
            report = self._run_build(Path(out))
            if report:
                _show_report(self, report, "Built at %s" % report.package_dir)
                self.statusBar().showMessage("Build complete", 6000)
        elif mode == "zip":
            f, _ = QFileDialog.getSaveFileName(self, "Export zip", self.project.package_name + ".zip", "Zip (*.zip)")
            if not f:
                return
            report = self._run_build(Path(tempfile.mkdtemp()))
            if report:
                archive = installer.make_zip(report.package_dir, Path(f))
                _show_report(self, report, "Exported to " + str(archive))
                self.statusBar().showMessage("Exported " + Path(f).name, 6000)
        elif mode == "install":
            targets = _pick_locations(self)
            if not targets:
                return
            report = self._run_build(Path(tempfile.mkdtemp()))
            if not report:
                return
            done = []
            for t in targets:
                try:
                    res = installer.install(report.package_dir, t)
                    done.append(str(res.destination))
                except Exception as e:
                    done.append("FAILED %s — %s" % (t, e))
            _show_report(
                self, report,
                "Installed to %d location(s):\n  %s\n\nRestart Harmony to load the toolbars."
                % (len(done), "\n  ".join(done)),
            )
            self.statusBar().showMessage("Installed to %d location(s)" % len(done), 6000)

    def _run_build(self, out: Path):
        """Write the package; return the WriteReport (or None on failure).
        Caller is responsible for showing it — keeps this testable."""
        try:
            return package_writer.write_package(self.project, out, script_index=self.script_index)
        except Exception as e:
            QMessageBox.critical(self, "Build failed", str(e))
            return None

    def _uninstall(self) -> None:
        found = self._installed_packages()
        if not found:
            QMessageBox.information(
                self, "Nothing to uninstall",
                "No '%s' package found in any Harmony version." % self.project.package_name,
            )
            return
        picked = _choose_many(
            self, "Uninstall '%s' from which version(s)?" % self.project.package_name,
            [(lbl, str(path)) for lbl, path in found],
        )
        if not picked:
            return
        if QMessageBox.question(
            self, "Confirm uninstall",
            "Delete the '%s' package (folder + toolbars) from %d location(s)?"
            % (self.project.package_name, len(picked)),
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        removed = []
        for folder in picked:
            try:
                if installer.uninstall(folder, self.project.package_name):
                    removed.append(folder)
            except Exception as e:
                QMessageBox.critical(self, "Uninstall failed", str(e))
        QMessageBox.information(
            self, "Done",
            "Removed from %d location(s):\n  %s\n\nRestart Harmony."
            % (len(removed), "\n  ".join(str(f) for f in removed)),
        )
        self.statusBar().showMessage("Uninstalled from %d location(s)" % len(removed), 6000)


# --------------------------------------------------------------- helpers ---


def _choose_one(parent, title, options):
    """options: [(label, value)]. Returns the picked value or None."""
    from PySide6.QtWidgets import QRadioButton

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    v = QVBoxLayout(dlg)
    v.addWidget(QLabel(title))
    btns = []
    for label, value in options:
        rb = QRadioButton("%s\n%s" % (label, value))
        rb.setProperty("value", value)
        v.addWidget(rb)
        btns.append(rb)
    if btns:
        btns[0].setChecked(True)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    if dlg.exec() != QDialog.Accepted:
        return None
    return next((rb.property("value") for rb in btns if rb.isChecked()), None)


def _choose_many(parent, title, options):
    """options: [(label, value)]. Returns the list of picked values."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    v = QVBoxLayout(dlg)
    v.addWidget(QLabel(title))
    boxes = []
    for label, value in options:
        cb = QCheckBox("%s\n%s" % (label, value))
        cb.setProperty("value", value)
        v.addWidget(cb)
        boxes.append(cb)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    if dlg.exec() != QDialog.Accepted:
        return []
    return [Path(cb.property("value")) for cb in boxes if cb.isChecked()]


def _svg_icon(svg: str, size: int = 22) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(img))


def _nice_label(name: str) -> str:
    base = name.split("_", 1)[1] if "_" in name else name
    return base.replace("_", " ").strip().title()


def _scripts_in(toolbar: dict) -> list[str]:
    out: list[str] = []

    def walk(items):
        for it in items or []:
            if isinstance(it, str) and it != "---":
                out.append(it)
            elif isinstance(it, dict):
                if it.get("type") == "submenu":
                    walk(it.get("items"))
                elif it.get("script"):
                    out.append(it["script"])

    walk(toolbar.get("items"))
    return out


def _set_or_drop(d: dict, key: str, value: str) -> None:
    if value:
        d[key] = value
    else:
        d.pop(key, None)


def _tree_row(item) -> QTreeWidgetItem:
    if isinstance(item, str):
        row = QTreeWidgetItem([item, "script"])
    elif item.get("type") == "submenu":
        row = QTreeWidgetItem([item.get("label", "Submenu"), "submenu (%d)" % len(item.get("items", []))])
    else:
        row = QTreeWidgetItem([item.get("label") or item.get("script", "?"), "script"])
    row.setData(0, _ITEM_ROLE, item)
    return row


def _prompt(parent, title, label, default=""):
    from PySide6.QtWidgets import QInputDialog

    return QInputDialog.getText(parent, title, label, text=default)


def _show_report(parent, report, extra: str = "") -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("Done")
    box.setText("✓ Finished")
    box.setInformativeText(report.text() + (("\n\n" + extra) if extra else ""))
    box.exec()


def _pick_locations(parent) -> list[Path]:
    """Multi-select: a machine can have several Harmony versions, each with its
    own roaming packages/ folder."""
    repo = _repo_root()
    locs = discover_locations(repo_root=repo)
    dlg = QDialog(parent)
    dlg.setWindowTitle("Install to which Toon Boom version(s)?")
    v = QVBoxLayout(dlg)
    v.addWidget(QLabel("Tick every Harmony version's packages folder to install into:"))

    boxes: list[QCheckBox] = []
    for loc in locs:
        state = "" if loc.exists else "  (will be created)"
        if not loc.writable:
            state = "  — read-only, cannot install"
        cb = QCheckBox("%s\n%s%s" % (loc.label, loc.path, state))
        cb.setEnabled(loc.writable)
        cb.setProperty("path", str(loc.path))
        if loc.writable and loc.kind == "roaming":
            cb.setChecked(True)
        v.addWidget(cb)
        boxes.append(cb)

    extra_paths: list[str] = []

    def add_custom():
        d = QFileDialog.getExistingDirectory(dlg, "Custom packages folder")
        if d:
            cb = QCheckBox(d)
            cb.setChecked(True)
            cb.setProperty("path", d)
            v.insertWidget(v.count() - 2, cb)
            boxes.append(cb)
            extra_paths.append(d)

    add_btn = QPushButton("Add folder…")
    add_btn.clicked.connect(add_custom)
    v.addWidget(add_btn)

    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    if dlg.exec() != QDialog.Accepted:
        return []
    return [Path(cb.property("path")) for cb in boxes if cb.isChecked()]
