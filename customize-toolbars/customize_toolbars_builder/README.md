# customize_toolbars_builder

The Python package behind Customize Toolbars. Start from
[`../README.md`](../README.md).

```
models/     script index, Harmony install locations, project model  (stdlib)
services/   companion resolver, planner (runs the JS engine via dukpy),
            icon badges, package writer, installer, engine_assets     (stdlib + dukpy)
ui/         PySide6 window + theme
cli.py      build / scan / locations
_bundled_package/   the Customize_Toolbars Harmony package — its engine/ is
                    copied verbatim into every build; edit it here to change
                    runtime behaviour
```

`models/` and `services/` are Qt-free and unit-tested; the UI is smoke-tested
offscreen.

```
set PYTHONPATH=%CD%\..
..\.venv\Scripts\python -m pytest customize_toolbars_builder/tests -q
```
