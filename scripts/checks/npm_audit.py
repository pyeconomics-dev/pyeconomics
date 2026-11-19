# scripts/checks/npm_audit.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Audit a Node project's lockfile, with reviewed and dated exceptions.

`npm audit --audit-level=high` fails on any advisory of High severity or above
in a lockfile, and has no way to accept one. An advisory with no patched
release then fails every commit and every pull request until its maintainers
publish one: picomatch's GHSA-fc5q-39xc-vjpf did from 2026-11-17 until it was
withdrawn the next day (issue #360).
This check runs the same audit and applies
scripts/checks/audit_exceptions.toml, the audit's only escape hatch:

- an advisory of High or above that no exception names fails, as before;
- an exception covers build and test tools only. The audit runs a second time
  without development dependencies (`--omit=dev`), and an advisory found there
  fails whatever the file says: nothing that ships is ever excepted;
- an exception fails after its `expires` date, which is at most 45 days after
  the day it was added, so it is read again or removed;
- an exception that matches nothing in a project it names fails: remove it
  once the fix is in the lockfile.

A failure to run npm, or an answer this check cannot read, fails too.

Usage, from the repository root (the `npm-audit` and `npm-audit-web` prek hooks
run it):

    python scripts/checks/npm_audit.py tools/node
    python scripts/checks/npm_audit.py web
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess  # nosec B404 # runs the npm CLI with a fixed argument list
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
EXCEPTIONS = REPO / "scripts" / "checks" / "audit_exceptions.toml"

#: The Node projects the gate audits, as the hooks name them.
PROJECTS = ("tools/node", "web")
#: The severities that fail the gate: npm's `--audit-level=high`.
FAILING = frozenset({"high", "critical"})
#: The longest an exception may run before it is read again.
MAX_DAYS = 45
#: A GitHub advisory id: three groups of four from GitHub's own alphabet.
ADVISORY_ID = re.compile(r"GHSA(-[23456789cfghjmpqrvwx]{4}){3}")
KEYS = frozenset(
    {"advisory", "package", "projects", "added", "expires", "issue", "reason"}
)


class AuditError(Exception):
    """The audit could not be run or read: the check fails closed."""


@dataclass(frozen=True, slots=True)
class Advisory:
    """One advisory of a failing severity, as `npm audit` reports it."""

    id: str
    package: str
    severity: str
    title: str


@dataclass(frozen=True, slots=True)
class AuditException:
    """One reviewed entry of audit_exceptions.toml."""

    advisory: str
    package: str
    projects: tuple[str, ...]
    added: dt.date
    expires: dt.date
    issue: int
    reason: str


def advisories(document: dict[str, Any]) -> dict[str, Advisory]:
    """Return the advisories of a failing severity in an `npm audit --json` answer.

    A package that is vulnerable only through another names that package as
    text in its `via` list; the advisory itself is an object there, once for
    each package it was filed against.
    """
    packages = document.get("vulnerabilities")
    counts = document.get("metadata", {}).get("vulnerabilities")
    if not isinstance(packages, dict) or not isinstance(counts, dict):
        msg = "the answer holds no `vulnerabilities` and `metadata` to read"
        raise AuditError(msg)
    found: dict[str, Advisory] = {}
    for entry in packages.values():
        for via in entry.get("via", []):
            if not isinstance(via, dict) or via.get("severity") not in FAILING:
                continue
            url = str(via.get("url", ""))
            identifier = url.rsplit("/", 1)[-1] or str(via.get("source", "?"))
            found[identifier] = Advisory(
                id=identifier,
                package=str(via.get("name", "?")),
                severity=str(via["severity"]),
                title=str(via.get("title", "")),
            )
    counted = sum(int(counts.get(severity, 0)) for severity in FAILING)
    if counted and not found:
        msg = f"{counted} findings of High or above, and no advisory to name"
        raise AuditError(msg)
    return found


def read_exceptions(text: str) -> list[AuditException]:
    """Parse and check audit_exceptions.toml; raise AuditError on a bad entry."""
    try:
        entries = tomllib.loads(text).get("exception", [])
    except tomllib.TOMLDecodeError as error:
        msg = f"audit_exceptions.toml does not parse: {error}"
        raise AuditError(msg) from error
    result: list[AuditException] = []
    for number, entry in enumerate(entries, start=1):
        where = f"audit_exceptions.toml, exception {number}"
        if not isinstance(entry, dict) or set(entry) != KEYS:
            msg = f"{where}: the keys are {', '.join(sorted(KEYS))}, all of them"
            raise AuditError(msg)
        advisory, projects = entry["advisory"], entry["projects"]
        added, expires = entry["added"], entry["expires"]
        problems = [
            (
                not isinstance(advisory, str) or not ADVISORY_ID.fullmatch(advisory),
                "`advisory` is a GitHub advisory id (GHSA-xxxx-xxxx-xxxx)",
            ),
            (
                not isinstance(entry["package"], str) or not entry["package"],
                "`package` names the package the advisory is filed against",
            ),
            (
                not isinstance(projects, list)
                or not projects
                or any(project not in PROJECTS for project in projects),
                f"`projects` lists one or more of {', '.join(PROJECTS)}",
            ),
            (
                type(added) is not dt.date or type(expires) is not dt.date,
                "`added` and `expires` are dates (2026-11-17, unquoted)",
            ),
            (
                type(entry["issue"]) is not int or entry["issue"] < 1,
                "`issue` is the number of the issue that tracks the advisory",
            ),
            (
                not isinstance(entry["reason"], str) or not entry["reason"].strip(),
                "`reason` says why the advisory cannot be fixed yet",
            ),
        ]
        for failed, rule in problems:
            if failed:
                msg = f"{where}: {rule}"
                raise AuditError(msg)
        if not 0 < (expires - added).days <= MAX_DAYS:
            msg = f"{where}: `expires` is 1 to {MAX_DAYS} days after `added`"
            raise AuditError(msg)
        result.append(
            AuditException(
                advisory=advisory,
                package=entry["package"],
                projects=tuple(projects),
                added=added,
                expires=expires,
                issue=entry["issue"],
                reason=entry["reason"],
            )
        )
    names = [(item.advisory, project) for item in result for project in item.projects]
    if len(names) != len(set(names)):
        msg = "audit_exceptions.toml names an advisory twice for one project"
        raise AuditError(msg)
    return result


def check(
    project: str,
    full: dict[str, Advisory],
    production: dict[str, Advisory],
    exceptions: list[AuditException],
    today: dt.date,
) -> tuple[list[str], list[str]]:
    """Return the problems that fail the audit, and the exceptions it applied."""
    problems: list[str] = []
    applied: list[str] = []
    mine = {item.advisory: item for item in exceptions if project in item.projects}
    for identifier, advisory in sorted(full.items()):
        described = (
            f"{identifier} ({advisory.severity}, {advisory.package}): {advisory.title}"
        )
        excepted = mine.get(identifier)
        if excepted is None:
            problems.append(f"{described}. No exception names it")
        elif excepted.package != advisory.package:
            problems.append(
                f"{described}. Its exception names the package {excepted.package!r}"
            )
        elif identifier in production:
            problems.append(
                f"{described}. It is in what ships (`npm audit --omit=dev`), "
                "which no exception covers"
            )
        elif today > excepted.expires:
            problems.append(
                f"{described}. Its exception expired on {excepted.expires}: read "
                f"issue #{excepted.issue}, then renew it in a reviewed pull request "
                "or remove what holds the package"
            )
        else:
            applied.append(
                f"{identifier} ({advisory.package}) until {excepted.expires}, "
                f"issue #{excepted.issue}"
            )
    for identifier, advisory in sorted(production.items()):
        if identifier not in full:
            problems.append(
                f"{identifier} ({advisory.severity}, {advisory.package}) is in what "
                "ships and not in the whole tree: the two audits disagree"
            )
    problems += [
        f"the exception for {identifier} matches nothing in {project}: remove it "
        "from scripts/checks/audit_exceptions.toml"
        for identifier in sorted(set(mine) - set(full))
    ]
    return problems, applied


def audit(npm: str, project: str, *, production: bool) -> dict[str, Any]:
    """Run `npm audit --json` for a project and return its parsed answer."""
    command = [npm, "audit", "--prefix", project, "--json"]
    if production:
        command.append("--omit=dev")
    # bandit B603 / ruff S603: the arguments are fixed, the project is one of
    # PROJECTS, npm is resolved by shutil.which, and no shell is involved. npm
    # exits 1 when it finds anything, so its status is not the result.
    result = subprocess.run(  # nosec B603  # noqa: S603
        command, capture_output=True, text=True, encoding="utf-8", check=False, cwd=REPO
    )
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        msg = f"`npm audit` printed no JSON (exit {result.returncode})"
        raise AuditError(msg) from error
    if not isinstance(document, dict) or "error" in document:
        summary = document.get("error", {}) if isinstance(document, dict) else {}
        code = summary.get("code", "?") if isinstance(summary, dict) else "?"
        msg = f"`npm audit` answered an error ({code})"
        raise AuditError(msg)
    return document


def main(arguments: list[str]) -> int:
    """Audit one project; return the process exit status."""
    if len(arguments) != 1 or arguments[0] not in PROJECTS:
        print(f"usage: npm_audit.py <{'|'.join(PROJECTS)}>", file=sys.stderr)
        return 2
    project = arguments[0]
    label = f"npm-audit ({project})"
    npm = shutil.which("npm")
    if npm is None:
        print(f"{label}: npm is not on PATH", file=sys.stderr)
        return 1
    try:
        exceptions = read_exceptions(EXCEPTIONS.read_text(encoding="utf-8"))
        full = advisories(audit(npm, project, production=False))
        production = advisories(audit(npm, project, production=True))
    except (AuditError, OSError) as error:
        print(f"{label}: {error}", file=sys.stderr)
        return 1
    today = dt.datetime.now(tz=dt.UTC).date()
    problems, applied = check(project, full, production, exceptions, today)
    for line in applied:
        print(f"{label}: excepted: {line}")
    if problems:
        for line in problems:
            print(f"{label}: {line}", file=sys.stderr)
        return 1
    print(f"{label}: no advisory of High or above outside the exceptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
