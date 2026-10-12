# scripts/checks/python_floor.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Re-check ADR-0010's Python floor against the latest NumPy and SciPy.

Run by hand (or the phase verifier's live checks), never on import. PyPI's
unversioned JSON endpoint names the latest stable release. Network, malformed
metadata and unsupported lower bounds fail closed rather than assuming a floor.
Usage: ``uv run python scripts/checks/python_floor.py``.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from packaging.specifiers import SpecifierSet
from packaging.version import Version

PACKAGES = ("numpy", "scipy")
TIMEOUT = 30
ROOT = Path(__file__).resolve().parents[2]


def floor(expression: str) -> Version:
    """Return a demonstrable inclusive lower bound, rejecting ambiguous specs.

    Scientific-stack metadata uses ``>=``; compatible-release bounds are also
    inclusive. Upper bounds and exclusions are allowed only when they do not
    exclude that minimum. Unsupported forms require human review, not a guess.
    """
    spec = SpecifierSet(expression)
    bounds = [Version(s.version) for s in spec if s.operator in {">=", "~="}]
    if not bounds or any(s.operator in {">", "==", "===", "<="} for s in spec):
        msg = f"cannot establish an inclusive Python floor from {expression!r}"
        raise ValueError(msg)
    minimum = max(bounds)
    if minimum.is_prerelease or minimum.is_postrelease or minimum not in spec:
        msg = f"Python lower bound is excluded or non-final: {expression!r}"
        raise ValueError(msg)
    return minimum


def latest(package: str) -> tuple[str, str]:
    """Fetch version and Requires-Python from a fixed public HTTPS endpoint."""
    if package not in PACKAGES:
        msg = f"unsupported floor dependency: {package}"
        raise ValueError(msg)
    url = f"https://pypi.org/pypi/{package}/json"
    # URL components are restricted to PACKAGES above; no user-supplied scheme.
    with urlopen(url, timeout=TIMEOUT) as response:  # nosec B310 - fixed HTTPS PyPI URL
        data = json.load(response)
    info = data["info"]
    version, requirement = info["version"], info["requires_python"]
    if not isinstance(version, str) or not isinstance(requirement, str):
        msg = f"{package}: missing version or requires_python in PyPI metadata"
        raise TypeError(msg)
    parsed = Version(version)
    if parsed.is_prerelease or parsed.is_devrelease:
        msg = f"{package}: latest endpoint returned a pre-release: {version}"
        raise ValueError(msg)
    return version, requirement


def main(root: Path = ROOT) -> int:
    """Print the observed floors and any required change; return 0 or 1."""
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        requirement = project["project"]["requires-python"]
        current = floor(requirement)
        floors = []
        for package in PACKAGES:
            version, expression = latest(package)
            minimum = floor(expression)
            floors.append(minimum)
            print(f"python-floor: {package} {version}: {expression} (floor {minimum})")
        required = max(floors)
    except (OSError, URLError, ValueError, KeyError, TypeError) as error:
        print(f"python-floor: unable to verify: {error}", file=sys.stderr)
        return 1
    if current < required:
        print(
            f"python-floor: raise requires-python from {requirement} to >={required}; "
            "update the CI matrix, Python classifiers and phase verification "
            "checks (ADR-0010).",
            file=sys.stderr,
        )
        return 1
    print(f"python-floor: PASS: project {requirement}; stack floor {required}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
