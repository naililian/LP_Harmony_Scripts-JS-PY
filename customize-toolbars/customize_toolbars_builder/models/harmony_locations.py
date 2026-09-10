"""Find the folders Harmony scans for script packages, so the builder can offer
"Install here" targets — one per installed Toon Boom version.

Harmony (Windows) reads packages from:
  * ``%APPDATA%\\Toon Boom Animation\\<edition>\\<NNNN>-scripts\\packages``
  * the folder named by ``TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER``
  * ``<TOONBOOM_GLOBAL_SCRIPT_LOCATION>\\packages``
  * (dev) ``<repo>\\harmony\\packages``

A version's ``<NNNN>-scripts`` folder only exists once its scripting has been
used, so versions are also inferred from sibling ``<NNNN>-*`` folders
(``2700-layouts-xml``, ``full-2700-pref``, …) and offered as
"will be created" targets.

Pure stdlib. No Qt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_VERSION_RE = re.compile(r"(?:^|full-)(\d{4})-")


@dataclass
class PackageLocation:
    path: Path
    label: str
    kind: str          # "roaming" | "env" | "global" | "repo"
    exists: bool
    writable: bool

    def as_dict(self) -> dict:
        return {
            "path": str(self.path),
            "label": self.label,
            "kind": self.kind,
            "exists": self.exists,
            "writable": self.writable,
        }


def _writable(path: Path) -> bool:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return os.access(probe, os.W_OK)


def _make(path: Path, label: str, kind: str) -> PackageLocation:
    path = Path(path)
    return PackageLocation(
        path=path,
        label=label,
        kind=kind,
        exists=path.is_dir(),
        writable=_writable(path),
    )


def _version_label(edition_dir: str, nnnn: str) -> str:
    # 2500 -> "25", 2700 -> "27"
    major = str(int(nnnn) // 100)
    edition = edition_dir.replace("Toon Boom Harmony", "").replace("Toon Boom", "").strip()
    return "Harmony {} {} (roaming)".format(major, edition).replace("  ", " ").strip()


def _roaming_versions(tba: Path) -> list[tuple[str, str, Path]]:
    """(edition_dir_name, NNNN, packages_path) for every version found under a
    Toon Boom Animation folder."""
    found: dict[tuple[str, str], Path] = {}
    for edition_dir in sorted(p for p in tba.iterdir() if p.is_dir()):
        for child in edition_dir.iterdir():
            m = _VERSION_RE.match(child.name)
            if m:
                nnnn = m.group(1)
                found.setdefault(
                    (edition_dir.name, nnnn),
                    edition_dir / (nnnn + "-scripts") / "packages",
                )
    return [(ed, nnnn, path) for (ed, nnnn), path in sorted(found.items())]


def discover_locations(
    appdata: str | os.PathLike | None = None,
    env: dict | None = None,
    repo_root: str | os.PathLike | None = None,
) -> list[PackageLocation]:
    env = os.environ if env is None else env
    appdata = appdata or env.get("APPDATA")
    out: list[PackageLocation] = []
    seen: set[str] = set()

    def add(loc: PackageLocation) -> None:
        key = os.path.normcase(os.path.normpath(str(loc.path)))
        if key not in seen:
            seen.add(key)
            out.append(loc)

    if appdata:
        tba = Path(appdata) / "Toon Boom Animation"
        if tba.is_dir():
            for edition_name, nnnn, pkg_path in _roaming_versions(tba):
                add(_make(pkg_path, _version_label(edition_name, nnnn), "roaming"))

    ext = env.get("TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER")
    if ext:
        add(_make(Path(ext), "TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER", "env"))

    tgsl = env.get("TOONBOOM_GLOBAL_SCRIPT_LOCATION")
    if tgsl:
        add(_make(Path(tgsl) / "packages", "TOONBOOM_GLOBAL_SCRIPT_LOCATION/packages", "global"))

    if repo_root:
        add(_make(Path(repo_root) / "harmony" / "packages", "repo (harmony/packages)", "repo"))

    return out
