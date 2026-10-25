# tests/server/test_fuzz_gap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The fuzz group's CPython 3.15 gap, asserted (Phase 4 Step 7; the Wheel rule).

Schemathesis needs PyYAML, which publishes no CPython 3.15 wheel, so the
``fuzz`` dependency group gates it with ``python_full_version < '3.15'`` (approved
by the maintainer in Phase 4 Step 7; issue #182 tracks the wheels)
and ci.yml's ``api-fuzz`` job runs on Python 3.14. On every cell this test
asserts the gap rather than skipping: the marker is present, the lock holds
Schemathesis only under it, the group installs nothing on 3.15 and the
Schemathesis package on every earlier version. When PyYAML ships 3.15 wheels,
the marker and this test go together.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

from packaging.markers import Marker
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]
MARKER = "python_full_version < '3.15'"


def _fuzz_group() -> list[Requirement]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return [Requirement(text) for text in project["dependency-groups"]["fuzz"]]


def _locked(name: str) -> list[dict[str, Any]]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return [package for package in lock["package"] if package["name"] == name]


def test_the_fuzz_group_gates_schemathesis_below_cpython_3_15() -> None:
    (requirement,) = _fuzz_group()
    assert requirement.name == "schemathesis"
    assert requirement.marker == Marker(MARKER)
    (locked,) = _locked("schemathesis")
    markers = [
        str(dependency.get("marker", ""))
        for dependency in _locked_group("fuzz")
        if dependency["name"] == "schemathesis"
    ]
    assert markers == [MARKER]
    assert locked["version"]


def _locked_group(group: str) -> list[dict[str, Any]]:
    (project,) = _locked("pyeconomics")
    groups: dict[str, list[dict[str, Any]]] = project["dev-dependencies"]
    return groups[group]


def test_this_cell_installs_the_group_exactly_where_the_marker_says() -> None:
    (requirement,) = _fuzz_group()
    assert requirement.marker is not None
    installs = requirement.marker.evaluate()
    if sys.version_info >= (3, 15):
        assert not installs  # the gap: the fuzz group installs nothing here
    else:
        assert installs


def test_pyyaml_still_has_no_cpython_3_15_wheel_in_the_lock() -> None:
    (pyyaml,) = _locked("pyyaml")
    wheels = [str(wheel["url"]) for wheel in pyyaml["wheels"]]
    assert wheels
    # When this fails, PyYAML ships 3.15 wheels: drop the marker and this file.
    assert not [url for url in wheels if "-cp315-" in url or "-abi3-" in url]
