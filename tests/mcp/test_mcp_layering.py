# tests/mcp/test_mcp_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP package's boundaries (ADR-0012 decisions 1 and 13; Phase 4 Step 8).

- ``import pyeconomics`` and ``import pyeconomics.surfaces`` load neither the
  MCP package nor the SDK, and reading the headline tuple loads no SDK.
- The MCP package imports no FastAPI (the ``mcp`` extra does not bring it), and
  a worker process of the REST server loads no MCP code.
- No MCP module reaches the network, a file, a key or the cache itself: the
  data layer does that, under its own rules. No module but ``headline.py``
  names a model id (the Generator rule), and no module runs a model but through
  ``invoke``.
"""

from __future__ import annotations

import ast
import re
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from pathlib import Path

import pytest

from pyeconomics import registry

MCP = Path(__file__).resolve().parents[2] / "src" / "pyeconomics" / "mcp"
#: What no MCP module may import (``urllib.parse`` reads an Origin, and is fine).
BANNED_IMPORTS = (
    "urllib.request",
    "socket",
    "http.client",
    "fastapi",
    "pathlib",
    "os",
    "shutil",
)
#: What no MCP module may call.
BANNED_CALLS = (
    "store_key(",
    "delete_key(",
    "resolve_key(",
    ".reveal(",
    "open(",
    "run_model(",
    "pyeconomics.run(",
    "bind_model(",
    "cache.clear(",
)


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _loaded(script: str, tmp_path: Path) -> list[str]:
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split()


@pytest.mark.parametrize(
    "imports",
    [
        "import pyeconomics",
        "import pyeconomics.surfaces",
        "import pyeconomics.mcp.headline",
    ],
)
def test_importing_loads_no_sdk(imports: str, tmp_path: Path) -> None:
    script = (
        f"import sys\n{imports}\n"
        "print(*sorted(m for m in sys.modules if m == 'mcp' or m.startswith('mcp.')))\n"
    )
    assert _loaded(script, tmp_path) == []


def test_import_pyeconomics_loads_no_mcp_package(tmp_path: Path) -> None:
    script = (
        "import sys, pyeconomics\n"
        "print(*sorted(m for m in sys.modules if m.startswith('pyeconomics.mcp')))\n"
    )
    assert _loaded(script, tmp_path) == []


def test_the_server_and_its_transports_load_no_fastapi(tmp_path: Path) -> None:
    script = (
        "import sys\n"
        "import pyeconomics.mcp.server, pyeconomics.mcp.transport\n"
        "pyeconomics.mcp.server.build_server()\n"
        "print(*sorted(m for m in sys.modules if m.split('.')[0] == 'fastapi'))\n"
    )
    assert _loaded(script, tmp_path) == []


def test_a_rest_worker_loads_no_mcp_code(tmp_path: Path) -> None:
    script = (
        "import sys\n"
        "import pyeconomics.server.pool, pyeconomics.server.work\n"
        "print(*sorted(m for m in sys.modules if m == 'mcp' or "
        "m.startswith(('mcp.', 'pyeconomics.mcp'))))\n"
    )
    assert _loaded(script, tmp_path) == []


@pytest.mark.parametrize("path", sorted(MCP.glob("*.py")), ids=lambda p: p.name)
def test_no_mcp_module_reaches_the_network_a_file_or_a_key(path: Path) -> None:
    found = sorted(
        name
        for name in _imports(path)
        if any(name == b or name.startswith(f"{b}.") for b in BANNED_IMPORTS)
    )
    assert found == []
    source = path.read_text(encoding="utf-8")
    assert [call for call in BANNED_CALLS if call in source] == []


@pytest.mark.parametrize(
    "path",
    sorted(p for p in MCP.glob("*.py") if p.name != "headline.py"),
    ids=lambda p: p.name,
)
def test_only_the_headline_tuple_names_a_model(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    named = [
        model_id
        for model_id in registry.ids()
        if re.search(rf"(?<![\w.]){re.escape(model_id)}(?![\w])", source)
    ]
    assert named == []
