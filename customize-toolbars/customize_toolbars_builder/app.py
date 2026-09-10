"""PySide6 desktop UI for customize_toolbars_builder.

    bin\\customize_toolbars_builder.bat gui
    python -m customize_toolbars_builder gui [project.lptb.json]
"""

from __future__ import annotations

import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is not installed:\n"
              "  .venv39\\Scripts\\python.exe -m pip install -r tools/customize_toolbars_builder/requirements.txt")
        return 1

    from .ui.main_window import MainWindow
    from .ui.theme import BUILDER_QSS

    app = QApplication.instance() or QApplication(["customize_toolbars_builder"])
    app.setApplicationName("Customize Toolbars Builder")
    app.setStyleSheet(BUILDER_QSS)

    project = next((a for a in argv if a.endswith(".json")), None)
    win = MainWindow(project_path=project)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
