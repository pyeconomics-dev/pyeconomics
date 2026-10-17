# scripts/checks/licences.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail on any runtime dependency whose licence ADR-0004 does not allow.

ADR-0004 admits seven licences for runtime dependencies, meaning everything a
user installs with the package or any of its extras: MIT, BSD-2-Clause,
BSD-3-Clause, Apache-2.0, ISC, NCSA and PSF-2.0. This check:

1. reads the runtime closure from uv.lock: the project's dependencies and
   every extra's, followed transitively, never its dependency groups;
2. fails on any package ADR-0004 excludes by name, whatever its metadata says,
   on every platform the lock covers;
3. reads each closure package's licence from the synced environment's
   installed metadata (License-Expression, else a short License field, else
   the licence classifiers), and fails on a licence outside the allowlist, on
   missing or ambiguous licence metadata, and on a package the environment
   does not hold at its locked version.

A package that the lock installs only on other platforms (its markers exclude
this one) is listed and skipped; a run on that platform checks it.

The only escape hatch is a reviewed entry in licence_exceptions.toml beside
this script, naming the package, its licence exactly as this check reports
it, and why it is acceptable. An exception never overrides an exclusion by
name. Development and test tools (dependency groups) are outside the
allowlist, as ADR-0004 decides.

Usage, from the repository root (the `licences` prek hook runs it):

    uv run --locked --all-extras python scripts/checks/licences.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from collections import deque
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from packaging.markers import Marker
    from packaging.utils import canonicalize_name
    from packaging.version import Version
except ImportError:  # pragma: no cover - only outside the project environment
    sys.exit("licences: run through `uv run`; the dev group provides packaging.")

ALLOWED = (
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "NCSA",
    "PSF-2.0",
)
_ALLOWED = {licence.casefold() for licence in ALLOWED}

# ADR-0004 "Excluded by name": rejected whatever their metadata says.
EXCLUDED = {
    "financepy": "GPL-3.0-or-later",
    "rateslib": "source-available, non-commercial",
    "getfactormodels": "AGPL-3.0 on GitHub, no PyPI licence metadata",
    "dbnomics": "AGPL-3.0",
    "full-fred": "conflicting licence metadata",
}

# Short, unambiguous License-field spellings that are not SPDX identifiers.
LICENCE_ALIASES = {
    "mit license": "MIT",
    "the mit license": "MIT",
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license 2.0": "Apache-2.0",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "isc license": "ISC",
    "psf license": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
}

# Classifiers that name exactly one licence. "BSD License" (2, 3 or 4
# clauses?) and "Apache Software License" (which version?) are ambiguous, so
# a package that relies on them needs a reviewed exception.
CLASSIFIERS = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: University of Illinois/NCSA Open Source License": (
        "NCSA"
    ),
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
}

UNKNOWN_LICENCE = {"", "unknown", "none", "n/a"}
# A License field longer than this is the licence's full text, not its name.
MAX_LICENCE_NAME = 100
SPDX_ID = re.compile(r"[A-Za-z0-9.+:-]+")
PROJECT_CHECKOUT = ({"editable": "."}, {"virtual": "."})

ROOT = Path(__file__).resolve().parents[2]
EXCEPTIONS_FILE = Path(__file__).with_name("licence_exceptions.toml")

Key = tuple[str, str | None]


class _SpdxParser:
    """Recursive-descent evaluator for one SPDX licence expression."""

    def __init__(self, expression: str) -> None:
        self.expression = expression
        self.words: list[str] = re.findall(r"\(|\)|[^\s()]+", expression)
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
        if word.upper() in {"AND", "OR", "WITH", ")"} or not SPDX_ID.fullmatch(word):
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
    """Evaluate an SPDX licence expression against the allowlist.

    `A OR B` passes if either side passes, `A AND B` only if both do. A licence
    exception (`A WITH B`) never passes without review. Raises ValueError when
    the expression does not parse.
    """
    return _SpdxParser(expression).evaluate()


class Metadata(Protocol):
    """The part of a distribution's core metadata this check reads."""

    def get(self, name: str) -> str | None:
        """Return the first value of a field, or None."""
        ...

    def get_all(self, name: str) -> list[str] | None:
        """Return every value of a repeatable field, or None."""
        ...


@dataclass(frozen=True)
class Licence:
    """A package's licence as its metadata states it, and the verdict."""

    text: str  # what the metadata says; exceptions match on it exactly
    source: str  # which metadata field said it
    allowed: bool


def licence_of(meta: Metadata) -> Licence:
    """Read a distribution's licence from its core metadata."""
    expression = (meta.get("License-Expression") or "").strip()
    if expression:
        try:
            return Licence(expression, "License-Expression", spdx_allowed(expression))
        except ValueError:
            return Licence(
                expression, "License-Expression (unparseable)", allowed=False
            )

    field = (meta.get("License") or "").strip()
    if (
        field.casefold() not in UNKNOWN_LICENCE
        and "\n" not in field
        and len(field) <= MAX_LICENCE_NAME
    ):
        alias = LICENCE_ALIASES.get(field.casefold())
        if alias:
            return Licence(field, "License", alias.casefold() in _ALLOWED)
        try:
            return Licence(field, "License", spdx_allowed(field))
        except ValueError:
            pass  # free text; the classifiers may still say it precisely

    classifiers = sorted(
        c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")
    )
    if classifiers:
        text = " AND ".join(c.rsplit(" :: ", 1)[-1] for c in classifiers)
        mapped = [CLASSIFIERS.get(c) for c in classifiers]
        allowed = all(m is not None and m.casefold() in _ALLOWED for m in mapped)
        return Licence(text, "Classifier", allowed)

    return Licence("<missing>", "no licence metadata", allowed=False)


def project_name(root: Path) -> str:
    """Return the normalized project name from pyproject.toml."""
    with (root / "pyproject.toml").open("rb") as handle:
        return canonicalize_name(tomllib.load(handle)["project"]["name"])


def marker_applies(marker: str | None, environment: dict[str, str] | None) -> bool:
    """Return whether an edge's environment marker holds (no marker always does)."""
    return marker is None or Marker(marker).evaluate(environment)


def resolve(
    by_name: dict[str, list[dict[str, Any]]], edge: dict[str, Any]
) -> dict[str, Any]:
    """Return the one locked package a dependency edge points at."""
    candidates = [
        p
        for p in by_name.get(canonicalize_name(edge["name"]), [])
        if edge.get("version", p.get("version")) == p.get("version")
        and edge.get("source", p.get("source")) == p.get("source")
    ]
    if len(candidates) != 1:
        message = f"uv.lock: cannot resolve the dependency on {edge['name']!r}"
        raise LookupError(message)
    return candidates[0]


def runtime_closure(
    lock: dict[str, Any],
    project: str,
    *,
    follow_markers: bool,
    environment: dict[str, str] | None = None,
) -> dict[Key, dict[str, Any]]:
    """Return the locked packages a user can install with the project and its extras.

    With follow_markers, only edges whose markers hold in `environment` (by
    default this interpreter's) are followed; without it, every platform's.
    """
    by_name: dict[str, list[dict[str, Any]]] = {}
    for package in lock.get("package", []):
        by_name.setdefault(canonicalize_name(package["name"]), []).append(package)

    roots = [p for p in by_name.get(project, []) if p.get("source") in PROJECT_CHECKOUT]
    if len(roots) != 1:
        message = f"uv.lock holds no editable or virtual {project!r} package"
        raise LookupError(message)
    root = roots[0]
    root_key: Key = (project, root.get("version"))
    extras = root.get("optional-dependencies", {})

    queue: deque[dict[str, Any]] = deque(root.get("dependencies", []))
    for edges in extras.values():
        queue.extend(edges)
    expanded = {(root_key, None)} | {(root_key, extra) for extra in extras}
    closure: dict[Key, dict[str, Any]] = {}

    while queue:
        edge = queue.popleft()
        if follow_markers and not marker_applies(edge.get("marker"), environment):
            continue
        package = resolve(by_name, edge)
        key: Key = (canonicalize_name(edge["name"]), package.get("version"))
        if key != root_key:
            closure[key] = package
        for part in (None, *edge.get("extra", [])):
            if (key, part) in expanded:
                continue
            expanded.add((key, part))
            if part is None:
                queue.extend(package.get("dependencies", []))
            else:
                queue.extend(package.get("optional-dependencies", {}).get(part, []))
    return closure


def load_exceptions(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Read and validate the reviewed exceptions file."""
    if not path.is_file():
        return {}, []
    with path.open("rb") as handle:
        entries = tomllib.load(handle).get("exception", [])
    exceptions: dict[str, dict[str, str]] = {}
    problems = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != {
            "package",
            "licence",
            "reason",
        }:
            problems.append(
                f"{path.name}: exception {index} needs exactly package, licence "
                "and reason"
            )
            continue
        if not all(isinstance(v, str) and v.strip() for v in entry.values()):
            problems.append(f"{path.name}: exception {index} has an empty field")
            continue
        name = canonicalize_name(entry["package"])
        if name in exceptions:
            problems.append(f"{path.name}: {name} has more than one exception")
        exceptions[name] = entry
    return exceptions, problems


def check(
    lock: dict[str, Any],
    project: str,
    exceptions: dict[str, dict[str, str]],
    *,
    distribution: Callable[[str], Any] = metadata.distribution,
    environment: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (report lines, failures) for the runtime closure."""
    everywhere = runtime_closure(lock, project, follow_markers=False)
    here = runtime_closure(lock, project, follow_markers=True, environment=environment)
    report: list[str] = []
    failures: list[str] = []

    for name, version in sorted(everywhere):
        label = f"{name} {version}"
        if name in EXCLUDED:
            failures.append(f"{label}: excluded by name in ADR-0004 ({EXCLUDED[name]})")
            continue
        if (name, version) not in here:
            report.append(
                f"  {label}: not installed on this platform (markers); skipped"
            )
            continue
        try:
            dist = distribution(name)
        except metadata.PackageNotFoundError:
            failures.append(
                f"{label}: not installed; run `uv sync --locked --all-extras`"
            )
            continue
        if version is not None and Version(dist.version) != Version(version):
            failures.append(
                f"{label}: {dist.version} is installed; run `uv sync --locked`"
            )
            continue
        licence = licence_of(dist.metadata)
        shown = f"{licence.text or '-'} [{licence.source}]"
        if licence.allowed:
            report.append(f"  {label}: {shown} ok")
            continue
        exception = exceptions.get(name)
        if exception and exception["licence"] == licence.text:
            report.append(f"  {label}: {shown} allowed by a reviewed exception")
        elif exception:
            failures.append(
                f"{label}: {shown}, but its exception records "
                f"{exception['licence']!r}; review it again"
            )
        else:
            failures.append(f"{label}: {shown} is outside the ADR-0004 allowlist")

    unused = sorted(set(exceptions) - {name for name, _ in everywhere})
    report += [
        f"  note: the exception for {name} matches no runtime package"
        for name in unused
    ]
    header = (
        f"licences: {len(everywhere)} runtime packages in uv.lock, "
        f"{len(here)} on this one"
    )
    return [header, *report], failures


def main() -> int:
    """Check the runtime closure; return the process exit status."""
    with (ROOT / "uv.lock").open("rb") as handle:
        lock = tomllib.load(handle)
    exceptions, problems = load_exceptions(EXCEPTIONS_FILE)
    report, failures = check(lock, project_name(ROOT), exceptions)
    print("\n".join(report))
    failures = problems + failures
    if failures:
        print("Runtime licence check failed (ADR-0004):", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        print(
            f"Allowed: {', '.join(ALLOWED)}. Replace the dependency, or record a "
            f"reviewed exception in {EXCEPTIONS_FILE.relative_to(ROOT).as_posix()}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
