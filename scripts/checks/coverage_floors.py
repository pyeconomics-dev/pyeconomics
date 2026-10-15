# scripts/checks/coverage_floors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail if a package's branch coverage is below its floor.

pyproject.toml's `fail_under = 95` holds the whole package to 95%. This check
holds the trees that matter most to their own floors (ROADMAP section 4 2.4,
"Model quality & governance"): `src/pyeconomics/core/` to 95%,
`src/pyeconomics/models/` to 90% and, from Phase 3 Step 2,
`src/pyeconomics/data/` to 95%, so a well-covered tree cannot hide an untested
one.

It reads the JSON report `coverage json` writes. Coverage is coverage.py's own
measure with branch coverage on: covered statements plus covered branches, over
all statements plus all branches, the figure `coverage report` prints and
`fail_under` compares. A package with no measured statements fails, because it
means the report's paths or coverage's `source_pkgs` no longer point at the
package, and a floor that measures nothing proves nothing. (`models/` was allowed
to be empty until Phase 2 Step 6 registered the first catalog models.)

Usage, from the repository root after `pytest --cov` (CI's tests job runs it):

    uv run coverage json -o coverage.json
    uv run python scripts/checks/coverage_floors.py coverage.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final

#: Each package, the path segments that identify its files, and its floor in percent.
FLOORS: Final = (
    ("core", "/pyeconomics/core/", 95.0),
    ("models", "/pyeconomics/models/", 90.0),
    ("data", "/pyeconomics/data/", 95.0),
)

DEFAULT_REPORT = "coverage.json"


def load(path: Path) -> dict[str, Any]:
    """Read a `coverage json` report, or raise `ValueError` saying what is wrong."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"cannot read {path}: {error.strerror or error}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"{path} is not a JSON report: {error}"
        raise ValueError(msg) from error
    if not isinstance(report, dict) or not isinstance(report.get("files"), dict):
        msg = f"{path} is not a `coverage json` report: it has no 'files' table"
        raise ValueError(msg)  # noqa: TRY004 - one error type for every bad report
    return report


def totals(report: dict[str, Any], marker: str) -> tuple[int, int, int]:
    """Return (files, covered, total) over a package's statements and branches.

    A path matches when it contains `marker` once separators are forward slashes,
    so a relative, an absolute and a Windows path all count.

    Raises
    ------
    ValueError
        If a matching file has no branch data (coverage ran without branches).
    """
    files = covered = total = 0
    for name, entry in report["files"].items():
        if marker not in "/" + str(name).replace("\\", "/"):
            continue
        summary = entry.get("summary", {})
        if "num_branches" not in summary:
            msg = f"{name} has no branch data; run coverage with `branch = true`"
            raise ValueError(msg)
        files += 1
        covered += summary["covered_lines"] + summary["covered_branches"]
        total += summary["num_statements"] + summary["num_branches"]
    return files, covered, total


def check(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return the report lines and the failures, one per package below its floor."""
    lines: list[str] = []
    failures: list[str] = []
    for name, marker, floor in FLOORS:
        files, covered, total = totals(report, marker)
        if total == 0:
            lines.append(f"{name}: no measured statements ({files} file(s))")
            failures.append(
                f"{name} has no measured statements, so its {floor:g}% floor "
                "measures nothing; check the report's paths and `source_pkgs`"
            )
            continue
        percent = 100.0 * covered / total
        verdict = "ok" if percent >= floor else "BELOW THE FLOOR"
        lines.append(f"{name}: {percent:.2f}% of {total} (floor {floor:g}%) {verdict}")
        if percent < floor:
            failures.append(
                f"{name} coverage is {percent:.2f}%, below its {floor:g}% floor"
            )
    return lines, failures


def main(argv: list[str]) -> int:
    """Run the check on the report named in `argv` (default: coverage.json)."""
    path = Path(argv[1] if len(argv) > 1 else DEFAULT_REPORT)
    try:
        lines, failures = check(load(path))
    except ValueError as error:
        print(f"coverage floors: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    for failure in failures:
        print(f"coverage floors: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
