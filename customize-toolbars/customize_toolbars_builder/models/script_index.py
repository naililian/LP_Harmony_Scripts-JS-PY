"""Scan folders for Harmony launcher scripts (``*.js``) and describe each one:
the sibling files it needs, its convention icon, and how it resolves its own
folder (which tells us whether it survives being bundled without
``TOONBOOM_GLOBAL_SCRIPT_LOCATION``).

Pure stdlib. No Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# String literals a launcher uses to reach a sibling file, e.g.
#   scriptFolder + "/" + "LP_foo.py"      scriptFolder + "/LP_foo.py"
#   require(scriptFolder + "/helper.js")  include(root + "/thing.js")
_SIBLING_RE = re.compile(
    r"""["']([A-Za-z0-9_./-]+\.(?:py|js|json|ui|png|svg))["']"""
)
_FOLDER_TOKEN_RE = re.compile(
    r"\b(scriptFolder|scriptPath|packageFolder|root|folder|scriptDir)\b"
)

_ICON_EXTS = (".png", ".svg")


@dataclass
class ScriptInfo:
    name: str                      # basename without .js
    path: Path                     # the .js file
    root: Path                     # source root it was found under
    entry: str                     # best guess at the main function (usually == name)
    has_py: bool = False
    ui_files: list[Path] = field(default_factory=list)
    icon: Path | None = None       # script-icons/<name>.<ext> or a sibling
    launcher_kind: str = "unknown" # file_fallback | env_only | require_run | plain | unknown
    sibling_refs: list[str] = field(default_factory=list)  # filenames it string-references

    @property
    def portable(self) -> bool:
        """True if bundling the script into a package can't break its own path
        resolution (it prefers __file__, or references nothing external)."""
        if self.launcher_kind == "env_only":
            return False
        return True


def _classify(text: str, name: str) -> tuple[str, str]:
    has_file = "__file__" in text
    has_env = "TOONBOOM_GLOBAL_SCRIPT_LOCATION" in text
    has_run = bool(re.search(r"exports\.run\b|\.run\s*\(", text))

    if has_env and not has_file:
        kind = "env_only"
    elif has_file and has_env:
        kind = "file_fallback"
    elif has_run and "require(" in text:
        kind = "require_run"
    elif re.search(r"^\s*function\s+" + re.escape(name) + r"\s*\(", text, re.MULTILINE):
        kind = "plain"
    else:
        kind = "unknown"

    m = re.search(r"exports\.(\w+)\s*=\s*\1\b", text)
    if m:
        entry = m.group(1)
    elif re.search(r"^\s*function\s+" + re.escape(name) + r"\s*\(", text, re.MULTILINE):
        entry = name
    elif "exports.run" in text:
        entry = "run"
    else:
        entry = name
    return kind, entry


def _sibling_refs(text: str, self_name: str) -> list[str]:
    refs: list[str] = []
    for line in text.splitlines():
        if not _FOLDER_TOKEN_RE.search(line) and "require(" not in line and "include(" not in line:
            continue
        for match in _SIBLING_RE.findall(line):
            fname = match.split("/")[-1]
            if fname and fname != self_name + ".js" and fname not in refs:
                refs.append(fname)
    return refs


def _find_icon(name: str, root: Path, js_path: Path) -> Path | None:
    for base in (root / "script-icons", js_path.parent, js_path.parent / "icons"):
        for ext in _ICON_EXTS:
            candidate = base / (name + ext)
            if candidate.is_file():
                return candidate
    return None


def describe_script(js_path: Path, root: Path) -> ScriptInfo:
    name = js_path.stem
    text = js_path.read_text(encoding="utf-8", errors="replace")
    kind, entry = _classify(text, name)
    info = ScriptInfo(
        name=name,
        path=js_path,
        root=root,
        entry=entry,
        has_py=(js_path.with_suffix(".py")).is_file(),
        ui_files=sorted(js_path.parent.glob(name + "*.ui")),
        icon=_find_icon(name, root, js_path),
        launcher_kind=kind,
        sibling_refs=_sibling_refs(text, name),
    )
    return info


def scan_scripts(roots: Iterable[Path], recursive: bool = False) -> list[ScriptInfo]:
    """All ``*.js`` directly in each root (or recursively). Later roots win on
    name collisions, mirroring the old ``getScriptFolder`` behaviour."""
    by_name: dict[str, ScriptInfo] = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        pattern = "**/*.js" if recursive else "*.js"
        for js_path in sorted(root.glob(pattern)):
            if js_path.name.startswith("_") or "/packages/" in js_path.as_posix():
                continue
            info = describe_script(js_path, root)
            by_name[info.name] = info
    return sorted(by_name.values(), key=lambda s: s.name.lower())
