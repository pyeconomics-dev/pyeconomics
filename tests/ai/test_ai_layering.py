# tests/ai/test_ai_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Where the narrative may be reached, and what it may import (ADR-0012 decision 17).

- No MCP tool and no hosted route narrates: neither ``pyeconomics.mcp`` nor
  ``pyeconomics.server`` imports ``pyeconomics.ai``.
- ``pyeconomics.ai`` imports the standard library and pyeconomics only, so no AI
  client library arrives, and the ``[ai]`` extra installs nothing.
- ``import pyeconomics`` loads no part of it.
- No module of ``pyeconomics.ai`` reveals a key: only ``data/credentials/`` and
  ``data/transport/`` do (the ``secret-reveal`` rule).
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
import tomllib
from pathlib import Path

import pyeconomics

PACKAGE = Path(pyeconomics.__file__).parent
ROOT = PACKAGE.parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            if node.module == "pyeconomics":
                names.update(f"pyeconomics.{alias.name}" for alias in node.names)
    return names


def test_no_mcp_tool_or_hosted_route_reaches_the_narrative() -> None:
    reaching = sorted(
        str(path.relative_to(PACKAGE))
        for surface in ("mcp", "server")
        for path in (PACKAGE / surface).rglob("*.py")
        if any(
            name == "pyeconomics.ai" or name.startswith("pyeconomics.ai.")
            for name in _imports(path)
        )
    )
    assert reaching == []


def test_the_narrative_imports_the_standard_library_and_pyeconomics_only() -> None:
    allowed = set(sys.stdlib_module_names) | {"pyeconomics"}
    foreign = sorted(
        f"{path.name}: {name}"
        for path in (PACKAGE / "ai").glob("*.py")
        for name in _imports(path)
        if name.partition(".")[0] not in allowed
    )
    assert foreign == []


def test_the_ai_extra_installs_nothing() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["optional-dependencies"]["ai"] == []


def test_the_narrative_reveals_no_key() -> None:
    revealing = sorted(
        path.name
        for path in (PACKAGE / "ai").glob("*.py")
        if ".reveal(" in path.read_text(encoding="utf-8")
    )
    assert revealing == []


def test_importing_pyeconomics_loads_no_part_of_the_narrative() -> None:
    code = (
        "import sys, pyeconomics\n"
        "print(sorted(m for m in sys.modules if m.startswith('pyeconomics.ai')))\n"
    )
    shown = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert shown.stdout.strip() == "[]"
