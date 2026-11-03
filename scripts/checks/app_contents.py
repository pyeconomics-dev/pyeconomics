# scripts/checks/app_contents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail if the pyeconomics-app wheel holds anything but the static site.

The web app's wheel (ADR-0002; ADR-0013 decision 16) carries the built site
that ``pyeconomics serve`` serves at ``/``, and nothing that could run or leak.
This check opens the one wheel in a directory (``dist-app/`` in CI and the
release) and fails on:

- a member outside ``pyeconomics_app/site/``, beside the package's
  ``__init__.py`` and ``py.typed`` and the dist-info's METADATA, WHEEL, RECORD,
  LICENSE and NOTICE (no entry points, no scripts);
- a site file whose kind the build does not write (the suffixes in
  ``SITE_SUFFIXES`` and the ``_headers`` and ``_redirects`` files), in a hidden
  directory or file (``.env``, a build cache such as ``.astro/`` or ``.vite/``),
  or under ``node_modules`` or ``__pycache__``;
- an executable: a member marked executable, or one that starts with a shebang
  or an ELF, PE or Mach-O header; and an archive: a ZIP inside the wheel;
- a source map that names a local path (an absolute ``sources`` entry or
  ``sourceRoot``, or a ``file:`` URL);
- a wheel without the site's ``index.html``, ``404.html``, ``_headers`` or
  ``version.json``, which is what a wheel built before
  ``scripts/web/package_site.py`` lacks;
- a version other than pyproject.toml's and the member's, in the file name, the
  METADATA or the site's ``version.json``; METADATA with any requirement, or a
  licence other than Apache-2.0; a wheel over PyPI's 100 MB file limit.

scripts/checks/dist_contents.py checks the pyeconomics wheel and sdist; this is
its counterpart for the second distribution, and a new kind of site file needs
an edit here in the same change that adds it.

Usage, from the repository root:

    uv build --package pyeconomics-app --wheel --out-dir dist-app
    python scripts/checks/app_contents.py [DIST_DIR]
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final

PACKAGE: Final = "pyeconomics_app"
NAME: Final = "pyeconomics-app"
SITE: Final = f"{PACKAGE}/site/"
#: The kinds of file the site's build writes.
SITE_SUFFIXES: Final = frozenset(
    {
        ".css",
        ".html",
        ".ico",
        ".js",
        ".json",
        ".map",
        ".mjs",
        ".pagefind",
        ".pf_fragment",
        ".pf_index",
        ".pf_meta",
        ".png",
        ".svg",
        ".txt",
        ".webmanifest",
        ".webp",
        ".woff2",
        ".xml",
    }
)
#: The site's configuration files, which have no suffix.
SITE_FILES: Final = frozenset({"_headers", "_redirects"})
#: What every site holds.
REQUIRED: Final = ("index.html", "404.html", "_headers", "version.json")
#: PyPI's default limit on one uploaded file.
MAX_BYTES: Final = 100 * 1024 * 1024
#: The first bytes of an executable or an archive.
MAGIC: Final = (
    (b"#!", "a script (shebang)"),
    (b"\x7fELF", "an ELF executable"),
    (b"MZ", "a PE executable"),
    (b"\xfe\xed\xfa\xce", "a Mach-O executable"),
    (b"\xfe\xed\xfa\xcf", "a Mach-O executable"),
    (b"\xce\xfa\xed\xfe", "a Mach-O executable"),
    (b"\xcf\xfa\xed\xfe", "a Mach-O executable"),
    (b"\xca\xfe\xba\xbe", "a Mach-O executable"),
    (b"PK\x03\x04", "a ZIP archive"),
)
_LOCAL_PATH: Final = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\|file:)", re.IGNORECASE)


def project_version(root: Path) -> str:
    """Return pyproject.toml's version."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = project["project"]["version"]
    return version


def allowed_outside_site(version: str) -> frozenset[str]:
    """Return the members a wheel may hold outside the site."""
    info = f"{PACKAGE}-{version}.dist-info"
    return frozenset(
        {
            f"{PACKAGE}/__init__.py",
            f"{PACKAGE}/py.typed",
            f"{info}/METADATA",
            f"{info}/WHEEL",
            f"{info}/RECORD",
            f"{info}/licenses/LICENSE",
            f"{info}/licenses/NOTICE",
        }
    )


def site_problem(relative: str) -> str | None:
    """Return why a path below the site may not ship, or ``None``."""
    parts = PurePosixPath(relative).parts
    if any(part.startswith(".") for part in parts):
        return "is hidden (a dotfile or a build cache)"
    if {"node_modules", "__pycache__"} & set(parts):
        return "is a dependency or bytecode directory"
    name = parts[-1]
    if name not in SITE_FILES and PurePosixPath(name).suffix.lower() not in (
        SITE_SUFFIXES
    ):
        return "is not a kind of file the site's build writes"
    return None


def source_map_problem(data: bytes) -> str | None:
    """Return why a source map may not ship (it names a local path), or ``None``."""
    try:
        document = json.loads(data)
    except ValueError:
        return "is not a source map"
    if not isinstance(document, dict):
        return "is not a source map"
    names = [document.get("sourceRoot") or "", *(document.get("sources") or [])]
    if any(isinstance(name, str) and _LOCAL_PATH.match(name) for name in names):
        return "is a source map that names a local path"
    return None


def content_problem(name: str, data: bytes, mode: int) -> str | None:
    """Return why a member's bytes may not ship, or ``None``."""
    if mode & 0o111:
        return "is marked executable"
    for magic, kind in MAGIC:
        if data.startswith(magic):
            return f"is {kind}"
    if name.endswith(".map"):
        return source_map_problem(data)
    return None


def metadata_problems(text: str, version: str) -> list[str]:
    """Return the problems with the wheel's METADATA."""
    fields: dict[str, list[str]] = {}
    for line in text.split("\n\n", 1)[0].splitlines():
        key, separator, value = line.partition(": ")
        if separator:
            fields.setdefault(key, []).append(value.strip())
    problems = []
    if fields.get("Name") != [NAME]:
        problems.append(f"METADATA names {fields.get('Name')}, not {NAME}")
    if fields.get("Version") != [version]:
        problems.append(f"METADATA version {fields.get('Version')}, expected {version}")
    if fields.get("License-Expression") != ["Apache-2.0"]:
        problems.append("METADATA's licence is not Apache-2.0")
    if "Requires-Dist" in fields:
        problems.append(f"METADATA requires {fields['Requires-Dist']}: it needs none")
    return problems


def member_problems(wheel: zipfile.ZipFile, version: str) -> tuple[set[str], list[str]]:
    """Return a wheel's file names, and why any member may not ship."""
    outside = allowed_outside_site(version)
    names: set[str] = set()
    problems = []
    for info in wheel.infolist():
        name = info.filename
        if name.endswith("/"):
            continue
        names.add(name)
        if name.startswith(SITE):
            why = site_problem(name.removeprefix(SITE))
        elif name in outside:
            why = None
        else:
            why = "is outside pyeconomics_app/site/"
        why = why or content_problem(name, wheel.read(info), info.external_attr >> 16)
        if why:
            problems.append(f"{name} {why}")
    return names, problems


def check_wheel(path: Path, version: str) -> list[str]:
    """Return the problems with the app wheel's name, members and metadata."""
    problems = []
    expected = f"{PACKAGE}-{version}-py3-none-any.whl"
    if path.name != expected:
        problems.append(f"{path.name}: expected {expected}")
    if path.stat().st_size > MAX_BYTES:
        problems.append(f"{path.name}: over PyPI's {MAX_BYTES} byte file limit")
    with zipfile.ZipFile(path) as wheel:
        names, found = member_problems(wheel, version)
        problems += [f"{path.name}: {problem}" for problem in found]
        problems += [
            f"{path.name}: {name} is missing"
            for name in (
                f"{PACKAGE}/__init__.py",
                *(f"{SITE}{required}" for required in REQUIRED),
            )
            if name not in names
        ]
        meta = f"{PACKAGE}-{version}.dist-info/METADATA"
        if meta in names:
            problems += [
                f"{path.name}: {problem}"
                for problem in metadata_problems(wheel.read(meta).decode(), version)
            ]
        else:
            problems.append(f"{path.name}: {meta} is missing")
        built = f"{SITE}version.json"
        if built in names:
            found = json.loads(wheel.read(built)).get("pyeconomics")
            if found != version:
                problems.append(
                    f"{path.name}: the site was built from {found!r}, not {version!r}"
                )
    return problems


def main(root: Path, dist: Path) -> int:
    """Check the app wheel in dist against root's versions; return the status."""
    version = project_version(root)
    member = project_version(root / "packages" / NAME)
    # uv build writes a .gitignore into an output directory it creates.
    files = sorted(p for p in dist.iterdir() if p.is_file() and p.name != ".gitignore")
    wheels = [path for path in files if path.suffix == ".whl"]
    problems = []
    if member != version:
        problems.append(f"pyeconomics-app is {member}, pyproject.toml {version}")
    if len(wheels) != 1 or len(files) != 1:
        names = ", ".join(path.name for path in files) or "nothing"
        problems.append(f"expected one pyeconomics-app wheel in {dist}, found {names}")
    else:
        problems += check_wheel(wheels[0], version)
    if problems:
        print("app-contents: the app wheel holds unexpected content:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"app-contents: {wheels[0].name} holds only the static site.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path.cwd(), Path(sys.argv[1] if len(sys.argv) > 1 else "dist-app")))
