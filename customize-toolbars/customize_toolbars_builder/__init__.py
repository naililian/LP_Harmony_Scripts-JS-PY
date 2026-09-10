"""customize_toolbars_builder — build Customize_Toolbars packages for Harmony without hand-writing
configure.js.

Pick scripts, arrange them into toolbars, and emit a self-contained package
(engine + scripts + icons + toolbars/*.json) ready to drop into Harmony's
roaming ``packages/`` folder.

Layout:
  models/    pure data — script index, Harmony install locations, project model
  services/  companion resolution, package writing, install / zip
  cli.py     ``python -m customize_toolbars_builder build <project.json>``
  app.py     PySide6 desktop UI (Phase 3)

models/ and services/ are stdlib-only and unit-tested; Qt lives only in the UI.
"""

__version__ = "0.1.0"
