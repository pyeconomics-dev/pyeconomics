# scripts/web/package_site.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Copy the built site into the pyeconomics-app package (ADR-0013 decision 16).

The web app's wheel (``packages/pyeconomics-app``) carries the static site that
``pyeconomics serve`` serves at ``/``. This script copies a build, ``web/dist/``
by default, into ``packages/pyeconomics-app/src/pyeconomics_app/site/``, which
is git-ignored, so ``uv build --package pyeconomics-app --wheel`` then packages
it; ``scripts/checks/app_contents.py`` checks the wheel. It refuses:

- a build without ``index.html``, ``404.html``, ``_headers`` (the one source of
  the site's policy, which the local server applies) or ``version.json``;
- a build whose ``version.json`` names another pyeconomics version than the
  project's and the member's, which must be equal: a site built from other site
  data never ships under this version;
- a symbolic link or a Windows junction anywhere in the build, so nothing
  outside it is copied.

The site directory is replaced as a whole, so no stale page survives a new
build. It reads no network, key or setting.

Usage, from the repository root, after ``npm run data && npm run build`` in
``web/``:

    python scripts/web/package_site.py [--dist DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_DIST: Final = ROOT / "web" / "dist"
MEMBER: Final = ROOT / "packages" / "pyeconomics-app"
SITE: Final = MEMBER / "src" / "pyeconomics_app" / "site"
#: What every build holds, or the local server cannot serve it as production.
REQUIRED: Final = ("index.html", "404.html", "_headers", "version.json")


class PackageError(Exception):
    """The build cannot be packaged; the message says why."""


def _version(pyproject: Path) -> str:
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version: str = project["project"]["version"]
    return version


def check_build(dist: Path, root: Path = ROOT) -> list[Path]:
    """Return every file of a build that may be packaged, in order.

    Raises
    ------
    PackageError
        For a missing build or required file, a version that is not the
        project's, or a symbolic link or junction in the build.
    """
    if not dist.is_dir() or dist.is_symlink():
        msg = f"{dist} is not a build directory: run npm run build in web/"
        raise PackageError(msg)
    missing = [name for name in REQUIRED if not (dist / name).is_file()]
    if missing:
        msg = f"the build lacks {', '.join(missing)}: run npm run build in web/"
        raise PackageError(msg)
    project = _version(root / "pyproject.toml")
    member = _version(root / "packages" / "pyeconomics-app" / "pyproject.toml")
    built = json.loads((dist / "version.json").read_bytes()).get("pyeconomics")
    if not project == member == built:
        msg = (
            f"versions differ: pyproject.toml {project}, pyeconomics-app {member}, "
            f"the build's version.json {built}; run npm run data and npm run build "
            "again after a version bump"
        )
        raise PackageError(msg)
    files: list[Path] = []
    for path in sorted(dist.rglob("*")):
        if path.is_symlink() or path.is_junction():
            msg = f"{path.relative_to(dist).as_posix()} is a symbolic link or junction"
            raise PackageError(msg)
        if path.is_file():
            files.append(path)
    return files


def package(dist: Path, site: Path = SITE, root: Path = ROOT) -> int:
    """Replace the package's site with a build's files; return how many."""
    files = check_build(dist, root)
    if site.exists():
        shutil.rmtree(site)
    for source in files:
        target = site / source.relative_to(dist)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return len(files)


def main(argv: Sequence[str] | None = None) -> int:
    """Package the site; return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dist", type=Path, default=DEFAULT_DIST, help="the built site to package"
    )
    arguments = parser.parse_args(argv)
    try:
        count = package(arguments.dist.resolve())
    except PackageError as error:
        sys.stderr.write(f"package_site: {error}\n")
        return 1
    sys.stdout.write(f"package_site: {count} files copied into {SITE}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
