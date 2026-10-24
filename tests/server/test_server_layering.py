# tests/server/test_server_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The server's boundaries (ADR-0012 decisions 1 and 10; Phase 4 Step 6).

- A worker process imports :mod:`pyeconomics.server.pool` and what it needs to
  run a task, and must load no web framework: those modules import none, and a
  fresh interpreter that imports them has none loaded.
- No server module accepts a URL from a caller or names a host: no route calls
  ``urllib`` or a socket; the only network access is the data layer's.
- No server module runs a model but through ``invoke`` (the surface layering
  test's scan covers ``server/``), and none calls a key-writing function.
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2] / "src" / "pyeconomics" / "server"
#: The modules a worker process loads.
WORKER_MODULES = ("formats", "logs", "pool", "settings", "work")
FRAMEWORKS = ("fastapi", "starlette", "uvicorn", "httpx", "httpx2")
#: What no server module may import or call.
BANNED = ("urllib", "socket", "http.client", "store_key", "delete_key", "reveal")


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


@pytest.mark.parametrize("module", WORKER_MODULES)
def test_no_worker_module_imports_a_framework(module: str) -> None:
    found = sorted(
        name
        for name in _imports(SERVER / f"{module}.py")
        if name.split(".", 1)[0] in FRAMEWORKS
    )
    assert found == []


@pytest.mark.parametrize("path", sorted(SERVER.glob("*.py")), ids=lambda p: p.name)
def test_no_server_module_reaches_the_network_or_a_key(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    found = sorted(
        name
        for name in _imports(path)
        if any(name == b or name.startswith(f"{b}.") for b in BANNED[:3])
    )
    assert found == []
    assert not any(f"{call}(" in source for call in BANNED[3:])


def test_a_worker_loads_no_framework(tmp_path: Path) -> None:
    script = (
        "import sys\n"
        "import pyeconomics.server.pool, pyeconomics.server.work\n"
        "from pyeconomics.server.work import Task, execute\n"
        "outcome = execute(Task(kind='run', target='foundations.time_value',\n"
        '    payload=b\'{"calculation": "future_value", "present_value": 1,\'\n'
        '            b\' "rate": 0.1, "periods": 1}\'))\n'
        "print(outcome.problem is None)\n"
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {FRAMEWORKS!r}))\n"
    )
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stdout.splitlines() == ["True", "[]"]
