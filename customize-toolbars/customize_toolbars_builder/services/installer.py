"""Deliver a built package: copy it into a Harmony packages folder, or zip it.

Pure stdlib. No Qt.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InstallResult:
    destination: Path
    replaced_existing: bool


def install(package_dir: str | Path, packages_folder: str | Path, overwrite: bool = True) -> InstallResult:
    package_dir = Path(package_dir)
    packages_folder = Path(packages_folder)
    if not (package_dir / "configure.js").is_file():
        raise ValueError("not a package folder (no configure.js): " + str(package_dir))

    packages_folder.mkdir(parents=True, exist_ok=True)
    dst = packages_folder / package_dir.name
    replaced = dst.exists()
    if replaced:
        if not overwrite:
            raise FileExistsError(str(dst))
        shutil.rmtree(dst)
    shutil.copytree(package_dir, dst)
    return InstallResult(destination=dst, replaced_existing=replaced)


def is_installed(packages_folder: str | Path, package_name: str) -> bool:
    return (Path(packages_folder) / package_name / "configure.js").is_file()


def uninstall(packages_folder: str | Path, package_name: str) -> bool:
    """Remove ``<packages_folder>/<package_name>``. Returns True if it existed."""
    target = Path(packages_folder) / package_name
    if not target.is_dir():
        return False
    if not (target / "configure.js").is_file():
        raise ValueError("refusing to delete (not a package folder): " + str(target))
    shutil.rmtree(target)
    return True


def make_zip(package_dir: str | Path, out_zip: str | Path) -> Path:
    package_dir = Path(package_dir)
    out_zip = Path(out_zip)
    base = out_zip.with_suffix("") if out_zip.suffix == ".zip" else out_zip
    archive = shutil.make_archive(
        str(base), "zip", root_dir=str(package_dir.parent), base_dir=package_dir.name
    )
    return Path(archive)


def set_user_env_var(name: str, value: str) -> bool:
    """Persist a user-level environment variable (Windows ``setx``). Returns
    success; the change only affects processes started afterwards."""
    if sys.platform != "win32":
        return False
    try:
        subprocess.run(["setx", name, value], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
