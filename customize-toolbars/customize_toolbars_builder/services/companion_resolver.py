"""Given a launcher script, work out every file that must travel with it into a
self-contained package.

Three sources, in order:
  1. same-basename siblings — ``<name>.py``, ``<name>*.ui``
  2. filenames the ``.js`` string-references (``ScriptInfo.sibling_refs``)
  3. extra globs the user declared on the config item (``companions``)

Icons are reported separately (they go to ``icons/``, not ``scripts/``).

Pure stdlib. No Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models.script_index import ScriptInfo

_CODE_EXTS = {".js", ".py", ".json", ".ui"}
_ICON_EXTS = {".png", ".svg"}


@dataclass
class CompanionSet:
    js: Path
    scripts: list[Path] = field(default_factory=list)   # -> package scripts/
    icons: list[Path] = field(default_factory=list)     # -> package icons/
    unresolved: list[str] = field(default_factory=list)  # refs/globs that matched nothing

    @property
    def all_files(self) -> list[Path]:
        return [*self.scripts, *self.icons]

    def summary(self) -> str:
        parts = ["{} file(s)".format(len(self.scripts))]
        if self.icons:
            parts.append("{} icon(s)".format(len(self.icons)))
        if self.unresolved:
            parts.append("{} unresolved".format(len(self.unresolved)))
        return ", ".join(parts)


def _dedupe(paths) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve()).lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _resolve_ref(ref: str, *folders: Path) -> Path | None:
    rel = ref.replace("\\", "/").lstrip("/")
    for folder in folders:
        candidate = folder / rel
        if candidate.is_file():
            return candidate
    return None


def resolve(info: ScriptInfo, extra_globs: list[str] | None = None) -> CompanionSet:
    folder = info.path.parent
    result = CompanionSet(js=info.path, scripts=[info.path])

    py = info.path.with_suffix(".py")
    if py.is_file():
        result.scripts.append(py)
    result.scripts.extend(sorted(folder.glob(info.name + "*.ui")))

    for ref in info.sibling_refs:
        hit = _resolve_ref(ref, folder, info.root)
        if hit is None:
            result.unresolved.append(ref)
        elif hit.suffix.lower() in _ICON_EXTS:
            result.icons.append(hit)
        else:
            result.scripts.append(hit)

    for glob in extra_globs or []:
        hits = sorted(folder.glob(glob))
        if not hits and folder != info.root:
            hits = sorted(info.root.glob(glob))
        if not hits:
            result.unresolved.append(glob)
            continue
        for hit in hits:
            if not hit.is_file():
                continue
            if hit.suffix.lower() in _ICON_EXTS:
                result.icons.append(hit)
            elif hit.suffix.lower() in _CODE_EXTS:
                result.scripts.append(hit)

    if info.icon is not None:
        result.icons.append(info.icon)

    result.scripts = _dedupe(p for p in result.scripts if p.suffix.lower() in _CODE_EXTS)
    result.icons = _dedupe(result.icons)
    return result


def resolve_all(
    infos: list[ScriptInfo], globs_by_name: dict[str, list[str]] | None = None
) -> dict[str, CompanionSet]:
    globs_by_name = globs_by_name or {}
    return {
        info.name: resolve(info, globs_by_name.get(info.name))
        for info in infos
    }
