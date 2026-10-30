# scripts/checks/web_licences.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail on any package the web app ships to browsers outside the licence allowlist.

The Phase 5 Dependency rule: the packages the site ships to browsers pass a
permissive allowlist (MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC and
0BSD), while build and test tools sit outside it, as Python's dependency groups
do (ADR-0004). ``web/package.json`` lists what ships under ``dependencies`` and
the tools under ``devDependencies``. This check:

1. reads the production tree from ``web/package-lock.json``: every package it
   does not mark ``dev``, which is what ``npm ls --omit=dev --all`` lists and
   ``npm ci`` installs for production. The lockfile records each package's
   licence, so the check needs no install and runs in the prek gate;
2. checks the own licence of each build tool whose code the build writes into
   pages (:data:`BUILD_OUTPUT`), but not their trees, which are build tooling;
3. with ``--shipped FILE`` (ci.yml's web job, after a build), reads the npm
   packages the client bundle holds, as ``web/scripts/shipped-packages.ts``
   records them, and fails on one that is neither in the production tree nor
   in :data:`BUILD_OUTPUT`: a development dependency an island imported.

A licence is an SPDX expression: ``A OR B`` passes if either side does,
``A AND B`` only if both do, and ``A WITH B`` never without review. A missing
licence, or one such as ``SEE LICENSE IN ...``, fails.

Usage, from the repository root (the ``web-licences`` prek hook runs it):

    uv run --locked python scripts/checks/web_licences.py [--shipped FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Never

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ALLOWED: Final = ("MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "0BSD")
_ALLOWED: Final = {licence.casefold() for licence in ALLOWED}

#: Build tools whose own code reaches pages, and what of it does.
BUILD_OUTPUT: Final = {
    "astro": "the island runtime Astro inlines into pages",
    "@astrojs/react": "the React client renderer in the client bundle",
}

ROOT: Final = Path(__file__).resolve().parents[2]
LOCKFILE: Final = ROOT / "web" / "package-lock.json"
_TOKENS: Final = re.compile(r"\(|\)|[^\s()]+")
_SPDX_ID: Final = re.compile(r"[A-Za-z0-9.+:-]+")


class _SpdxParser:
    """Recursive-descent evaluator for one SPDX licence expression."""

    def __init__(self, expression: str) -> None:
        self.expression = expression
        self.words: list[str] = _TOKENS.findall(expression)
        self.position = 0

    def fail(self, problem: str) -> Never:
        message = f"{problem} in {self.expression!r}"
        raise ValueError(message)

    def peek(self) -> str | None:
        if self.position < len(self.words):
            return self.words[self.position].upper()
        return None

    def take(self) -> str:
        if self.position >= len(self.words):
            self.fail("unexpected end")
        self.position += 1
        return self.words[self.position - 1]

    def either(self) -> bool:
        allowed = self.both()
        while self.peek() == "OR":
            self.take()
            allowed = self.both() or allowed
        return allowed

    def both(self) -> bool:
        allowed = self.term()
        while self.peek() == "AND":
            self.take()
            allowed = self.term() and allowed
        return allowed

    def term(self) -> bool:
        word = self.take()
        if word == "(":
            allowed = self.either()
            if self.take() != ")":
                self.fail("unbalanced parentheses")
            return allowed
        if word.upper() in {"AND", "OR", "WITH", ")"} or not _SPDX_ID.fullmatch(word):
            self.fail(f"unexpected {word!r}")
        if self.peek() == "WITH":
            self.take()
            self.take()
            return False
        return word.casefold() in _ALLOWED

    def evaluate(self) -> bool:
        allowed = self.either()
        if self.position != len(self.words):
            self.fail(f"trailing {self.words[self.position]!r}")
        return allowed


def spdx_allowed(expression: str) -> bool:
    """Evaluate an SPDX licence expression against :data:`ALLOWED`.

    Raises ValueError when the expression does not parse.

    >>> spdx_allowed("(MIT OR GPL-3.0-only)"), spdx_allowed("MIT AND GPL-3.0-only")
    (True, False)
    """
    return _SpdxParser(expression).evaluate()


def package_name(path: str) -> str:
    """Return the package a lockfile path installs.

    >>> package_name("node_modules/a/node_modules/@scope/b")
    '@scope/b'
    """
    return path.rpartition("node_modules/")[2]


def licence_problem(entry: Mapping[str, Any]) -> str | None:
    """Return why a lockfile entry's licence fails, or None if it passes."""
    licence = entry.get("license")
    if not isinstance(licence, str) or not licence.strip():
        return "no licence in the lockfile"
    try:
        if spdx_allowed(licence):
            return None
    except ValueError:
        return f"{licence!r} is not an SPDX expression"
    return f"{licence} is outside the allowlist"


def production(lock: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Return the lockfile's production tree: every package not marked ``dev``."""
    if lock.get("lockfileVersion") not in {2, 3}:
        message = "web/package-lock.json is not lockfile version 2 or 3"
        raise ValueError(message)
    packages: Mapping[str, Mapping[str, Any]] = lock.get("packages", {})
    return {
        path: entry
        for path, entry in packages.items()
        if path and not entry.get("dev") and not entry.get("link")
    }


def check(
    lock: Mapping[str, Any], shipped: Sequence[str] | None = None
) -> tuple[list[str], list[str]]:
    """Return (report lines, failures) for the production tree and what ships."""
    tree = production(lock)
    report = [f"web licences: {len(tree)} production packages in web/package-lock.json"]
    failures: list[str] = []
    for path, entry in sorted(tree.items()):
        label = f"{package_name(path)} {entry.get('version', '?')}"
        problem = licence_problem(entry)
        if problem:
            failures.append(f"{label}: {problem}")
        else:
            report.append(f"  {label}: {entry['license']} ok")

    packages: Mapping[str, Mapping[str, Any]] = lock.get("packages", {})
    for name, reason in BUILD_OUTPUT.items():
        tool = packages.get(f"node_modules/{name}")
        if tool is None:
            failures.append(f"{name}: not in the lockfile, though {reason} ships")
            continue
        label = f"{name} {tool.get('version', '?')}"
        problem = licence_problem(tool)
        if problem:
            failures.append(f"{label} ({reason}): {problem}")
        else:
            report.append(f"  {label}: {tool['license']} ok ({reason})")

    if shipped is not None:
        names = {package_name(path) for path in tree}
        for name in sorted(set(shipped)):
            if name in names:
                report.append(f"  shipped {name}: in the production tree")
            elif name in BUILD_OUTPUT:
                report.append(f"  shipped {name}: build output, its licence checked")
            else:
                failures.append(
                    f"{name} ships in the client bundle but is a development "
                    "dependency: move it to dependencies in web/package.json"
                )
    return report, failures


def read_shipped(path: Path) -> list[str]:
    """Read the package names ``web/scripts/shipped-packages.ts`` recorded."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != 1 or not isinstance(document.get("packages"), list):
        message = f"{path} is not a shipped-packages document of format 1"
        raise ValueError(message)
    return [str(name) for name in document["packages"]]


def main(argv: Sequence[str] | None = None) -> int:
    """Check web/'s licences; return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", type=Path, default=LOCKFILE, help="the lockfile")
    parser.add_argument(
        "--shipped",
        type=Path,
        help="the client bundle's packages (web/.astro/shipped-packages.json)",
    )
    arguments = parser.parse_args(argv)
    lock = json.loads(arguments.lock.read_text(encoding="utf-8"))
    shipped = None if arguments.shipped is None else read_shipped(arguments.shipped)
    report, failures = check(lock, shipped)
    print("\n".join(report))
    if failures:
        print("Web licence check failed (Phase 5 Dependency rule):", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        print(
            f"Allowed for what ships to browsers: {', '.join(ALLOWED)}. Replace the "
            "package, or keep a build or test tool in devDependencies.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
