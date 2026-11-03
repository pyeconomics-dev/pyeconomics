# scripts/checks/lock_index.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail if uv.lock or pylock.toml names a package source outside PyPI.

The maintainer's user-level uv configuration adds a private package-firewall
index. A `uv lock`, `uv add` or `uv export` run without `--no-config` writes
that index's URL into both lock files (Phase 1 Step 7): the URL would be
published, and CI cannot reach it. This check fails on any URL in either file
other than PyPI's simple index (https://pypi.org/simple) or a file under
https://files.pythonhosted.org/, and on any package source that is not that
index, apart from the project's own editable checkout and its workspace members
(the paths pyproject.toml lists in [tool.uv.workspace] members, such as
packages/pyeconomics-app). It prints a bad URL's scheme and host only, because a
private index's path can carry an organisation's name.

Usage, from the repository root (the `lock-index` prek hook runs it):

    python scripts/checks/lock_index.py

Change the lock files only with uv's `--no-config` flag:

    uv lock --no-config
    uv add --no-config <package>
    uv export --no-config --all-groups --format pylock.toml --output-file pylock.toml
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

INDEX_URL = "https://pypi.org/simple"
FILES_PREFIX = "https://files.pythonhosted.org/"
LOCK_FILES = ("uv.lock", "pylock.toml")
URL = re.compile(r"""[A-Za-z][A-Za-z0-9+.-]*://[^\s"'<>]+""")


def redact(url: str) -> str:
    """Return a URL's scheme and host only."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname or '?'}/..."


def is_pypi_index(value: object) -> bool:
    """Return whether a value is PyPI's simple index URL."""
    return isinstance(value, str) and value.rstrip("/") == INDEX_URL


def check_urls(name: str, text: str) -> list[str]:
    """Flag every URL in the file, comments included, that is not PyPI."""
    problems = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in URL.finditer(line):
            url = match.group()
            if not (is_pypi_index(url) or url.startswith(FILES_PREFIX)):
                problems.append(f"{name}:{lineno}: {redact(url)} is not PyPI")
    return problems


def workspace_members(root: Path) -> tuple[str, ...]:
    """Return the workspace members' paths pyproject.toml declares, if any."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return ()
    project = tomllib.loads(path.read_text(encoding="utf-8"))
    members = project.get("tool", {}).get("uv", {}).get("workspace", {})
    return tuple(m for m in members.get("members", []) if isinstance(m, str))


def is_project_checkout(source: dict[str, Any], members: tuple[str, ...] = ()) -> bool:
    """Return whether a lock source is the project's checkout or a workspace member."""
    return any(
        source in ({"editable": path}, {"virtual": path}) for path in (".", *members)
    )


def check_artifacts(name: str, package: str, entry: dict[str, Any]) -> list[str]:
    """Flag sdists and wheels named by a local path instead of a PyPI URL."""
    artifacts = [entry.get("sdist"), *entry.get("wheels", [])]
    return [
        f"{name}: {package} has a local file artifact, not a PyPI file"
        for artifact in artifacts
        if isinstance(artifact, dict) and "url" not in artifact
    ]


def check_uv_lock(data: dict[str, Any], members: tuple[str, ...] = ()) -> list[str]:
    """Flag uv.lock packages whose source is not the PyPI index."""
    problems = []
    for package in data.get("package", []):
        label = f"{package.get('name', '?')} {package.get('version', '')}".strip()
        source = package.get("source", {})
        if is_project_checkout(source, members):
            continue
        if set(source) != {"registry"} or not is_pypi_index(source["registry"]):
            kind = ", ".join(sorted(source)) or "no"
            problems.append(f"uv.lock: {label} has a {kind} source, not the PyPI index")
        problems += check_artifacts("uv.lock", label, package)
    return problems


def check_pylock(data: dict[str, Any], members: tuple[str, ...] = ()) -> list[str]:
    """Flag pylock.toml packages that do not come from the PyPI index."""
    problems = []
    for package in data.get("packages", []):
        label = f"{package.get('name', '?')} {package.get('version', '')}".strip()
        checkouts = [{"path": path, "editable": True} for path in (".", *members)]
        if package.get("directory") in checkouts:
            continue
        if not is_pypi_index(package.get("index")):
            problems.append(f"pylock.toml: {label} does not come from the PyPI index")
        problems.extend(
            f"pylock.toml: {label} has a {kind} source"
            for kind in ("vcs", "archive", "directory")
            if kind in package
        )
        problems += check_artifacts("pylock.toml", label, package)
    return problems


def main(root: Path) -> int:
    """Check both lock files under root; return the process exit status."""
    problems = []
    members = workspace_members(root)
    for name in LOCK_FILES:
        path = root / name
        if not path.is_file():
            problems.append(f"{name}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        problems += check_urls(name, text)
        data = tomllib.loads(text)
        if name == "uv.lock":
            problems += check_uv_lock(data, members)
        else:
            problems += check_pylock(data, members)
    if problems:
        print("Lock files name a package source outside PyPI:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "Re-lock with uv's --no-config flag (uv lock --no-config; uv export "
            "--no-config --all-groups --format pylock.toml --output-file pylock.toml).",
            file=sys.stderr,
        )
        return 1
    print(f"lock-index: {', '.join(LOCK_FILES)} name only PyPI sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path.cwd()))
