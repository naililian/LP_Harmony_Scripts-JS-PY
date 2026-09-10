"""``python -m customize_toolbars_builder`` / ``python tools/customize_toolbars_builder``.

Default action is the GUI (that's what a double-click on the .bat wants). The
CLI runs only for an explicit ``build`` / ``scan`` / ``locations`` (or ``-h``).
"""

import sys
from pathlib import Path

# allow running as a bare path (python tools/customize_toolbars_builder) too
_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

_CLI_COMMANDS = {"build", "scan", "locations", "-h", "--help"}
_first = sys.argv[1] if len(sys.argv) > 1 else ""

if _first in _CLI_COMMANDS:
    from customize_toolbars_builder.cli import main

    raise SystemExit(main())

# GUI: no args, "gui", or a project path
_gui_args = [a for a in sys.argv[1:] if a != "gui"]
from customize_toolbars_builder.app import main as gui_main

raise SystemExit(gui_main(_gui_args))
