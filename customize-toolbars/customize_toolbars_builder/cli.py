"""Command-line entry: build a package from a project file, scan scripts, or list
install targets. The PySide6 UI (app.py, Phase 3) wraps the same services.

    python -m customize_toolbars_builder build my_project.lptb.json --out dist
    python -m customize_toolbars_builder build my_project.lptb.json --install "%APPDATA%\\...\\packages"
    python -m customize_toolbars_builder scan E:/Scripts/GITHUB_REPO/TB_Harmony_DEV/harmony
    python -m customize_toolbars_builder locations
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models import harmony_locations
from .models.script_index import scan_scripts
from .models.toolbar_project import ToolbarProject
from .services import installer, package_writer


def _cmd_build(args) -> int:
    project = ToolbarProject.from_file(args.project)
    errors = project.validate()
    if errors:
        print("Config errors:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        if not args.force:
            return 2

    report = package_writer.write_package(project, args.out, harmony_version=args.harmony)
    print(report.text())

    if args.zip:
        archive = installer.make_zip(report.package_dir, args.zip)
        print("zip: " + str(archive))
    for target in args.install or []:
        result = installer.install(report.package_dir, target)
        verb = "replaced" if result.replaced_existing else "installed"
        print("{}: {}".format(verb, result.destination))
    if args.install:
        print("Restart Harmony to load the toolbars.")

    print("\nDone.")
    return 0


def _cmd_scan(args) -> int:
    infos = scan_scripts([Path(r) for r in args.roots], recursive=args.recursive)
    if not infos:
        print("no scripts found", file=sys.stderr)
        return 1
    width = max(len(i.name) for i in infos)
    for i in infos:
        flags = []
        if i.has_py:
            flags.append("py")
        if i.ui_files:
            flags.append("ui")
        flags.append("icon" if i.icon else "no-icon")
        flags.append(i.launcher_kind)
        print("{:<{w}}  {}".format(i.name, " ".join(flags), w=width))
        if i.sibling_refs:
            print("{}    refs: {}".format(" " * width, ", ".join(i.sibling_refs)))
    return 0


def _cmd_locations(args) -> int:
    repo = _find_repo_root()
    locs = harmony_locations.discover_locations(repo_root=repo)
    if not locs:
        print("no Harmony packages folders discovered")
        return 1
    for loc in locs:
        state = "ok" if loc.exists else "missing"
        if not loc.writable:
            state += ", read-only"
        print("{:<40}  {}  [{}]".format(loc.label, loc.path, state))
    return 0


def _find_repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "harmony" / "packages").is_dir():
            return parent
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="customize_toolbars_builder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="render a project file into a package")
    b.add_argument("project", type=Path)
    b.add_argument("--out", type=Path, default=Path("dist"))
    b.add_argument("--harmony", type=int, default=0, help="target Harmony major version")
    b.add_argument("--install", type=Path, metavar="PACKAGES_DIR", action="append",
                   help="a Harmony packages folder to install into (repeatable)")
    b.add_argument("--zip", type=Path, metavar="ZIP")
    b.add_argument("--force", action="store_true", help="write even with config errors")
    b.set_defaults(func=_cmd_build)

    s = sub.add_parser("scan", help="list launcher scripts under one or more roots")
    s.add_argument("roots", nargs="+", type=Path)
    s.add_argument("--recursive", action="store_true")
    s.set_defaults(func=_cmd_scan)

    lo = sub.add_parser("locations", help="discover Harmony packages folders")
    lo.set_defaults(func=_cmd_locations)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
