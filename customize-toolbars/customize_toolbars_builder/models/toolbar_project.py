"""In-memory model the builder edits: package metadata + source roots + a list of
toolbar configs (each config is exactly a ``toolbars/<id>.json`` document).

Round-trips three ways:
  * ``.lptb.json`` project file   (from_file / to_file)
  * a generated/installed package (from_package)
  * the package the writer emits  (services.package_writer)

Pure stdlib; jsonschema is optional (validate() is a no-op without it).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None

from ..services import engine_assets

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("_", str(text).lower()).strip("_")


@dataclass
class ToolbarProject:
    package_name: str = "Customize_Toolbars"
    version: str = "0.1.0"
    description: str = (
        "Declarative Harmony toolbars, built with customize_toolbars_builder."
    )
    author: str = ""
    source_roots: list[Path] = field(default_factory=list)
    toolbars: list[dict] = field(default_factory=list)

    # ---------------------------------------------------------------- load ---

    @classmethod
    def from_file(cls, path: str | Path) -> "ToolbarProject":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        pkg = data.get("package", {})
        roots = []
        for raw in data.get("sourceRoots", []):
            p = Path(raw)
            roots.append(p if p.is_absolute() else (path.parent / p).resolve())
        return cls(
            package_name=pkg.get("name", "Customize_Toolbars"),
            version=pkg.get("version", "0.1.0"),
            description=pkg.get("description", cls.description),
            author=pkg.get("author", ""),
            source_roots=roots,
            toolbars=list(data.get("toolbars", [])),
        )

    @classmethod
    def from_package(cls, package_dir: str | Path) -> "ToolbarProject":
        package_dir = Path(package_dir)
        meta = {}
        meta_path = package_dir / "tbpackage.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        toolbars = []
        tb_dir = package_dir / "toolbars"
        if tb_dir.is_dir():
            for cfg in sorted(tb_dir.glob("*.json")):
                doc = json.loads(cfg.read_text(encoding="utf-8"))
                doc.pop("$schema", None)
                toolbars.append(doc)
        return cls(
            package_name=meta.get("name", package_dir.name),
            version=meta.get("version", "0.1.0"),
            description=meta.get("description", cls.description),
            author=meta.get("author", ""),
            toolbars=toolbars,
        )

    # ---------------------------------------------------------------- save ---

    def to_dict(self) -> dict:
        return {
            "package": {
                "name": self.package_name,
                "version": self.version,
                "description": self.description,
                "author": self.author,
            },
            "sourceRoots": [str(p) for p in self.source_roots],
            "toolbars": self.toolbars,
        }

    def to_file(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------ editing ---

    def add_toolbar(
        self, title: str, abbr: str | None = None, id: str | None = None, menu: str | None = None
    ) -> dict:
        tb_id = id or slugify(title)
        if any(t.get("id") == tb_id for t in self.toolbars):
            raise ValueError("toolbar id already exists: " + tb_id)
        config: dict = {"id": tb_id, "title": title}
        if abbr:
            config["abbr"] = abbr[:3].upper()
        if menu:
            config["menu"] = menu
        config["items"] = []
        self.toolbars.append(config)
        return config

    def toolbar(self, tb_id: str) -> dict:
        for t in self.toolbars:
            if t.get("id") == tb_id:
                return t
        raise KeyError(tb_id)

    def remove_toolbar(self, tb_id: str) -> None:
        self.toolbars = [t for t in self.toolbars if t.get("id") != tb_id]

    # --------------------------------------------------------- inspection ---

    def script_names(self) -> set[str]:
        """Every script basename referenced anywhere, for the writer to bundle."""
        found: set[str] = set()

        def walk(items):
            for it in items or []:
                if isinstance(it, str):
                    if it != "---":
                        found.add(it)
                elif isinstance(it, dict):
                    if it.get("type") == "submenu":
                        walk(it.get("items"))
                    elif it.get("script"):
                        found.add(it["script"])

        for tb in self.toolbars:
            walk(tb.get("items"))
        return found

    def companion_globs(self) -> dict[str, list[str]]:
        """script basename -> extra file globs declared on its config item(s)."""
        out: dict[str, list[str]] = {}

        def walk(items):
            for it in items or []:
                if isinstance(it, dict):
                    if it.get("type") == "submenu":
                        walk(it.get("items"))
                    elif it.get("script") and it.get("companions"):
                        out.setdefault(it["script"], [])
                        for g in it["companions"]:
                            if g not in out[it["script"]]:
                                out[it["script"]].append(g)

        for tb in self.toolbars:
            walk(tb.get("items"))
        return out

    # -------------------------------------------------------- validation ---

    def validate(self) -> list[str]:
        """Schema errors across all toolbar configs ([] if clean or jsonschema
        unavailable)."""
        if jsonschema is None:
            return []
        schema = json.loads(engine_assets.schema_path().read_text(encoding="utf-8"))
        validator = jsonschema.validators.validator_for(schema)(schema)
        errors: list[str] = []
        seen_ids: set[str] = set()
        for tb in self.toolbars:
            label = tb.get("id") or tb.get("title") or "?"
            for err in validator.iter_errors(tb):
                errors.append("{}: {}".format(label, err.message))
            if tb.get("id") in seen_ids:
                errors.append("duplicate toolbar id: " + str(tb.get("id")))
            seen_ids.add(tb.get("id"))
        return errors
