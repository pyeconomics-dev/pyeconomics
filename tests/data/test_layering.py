# tests/data/test_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data layer's boundaries (ADR-0011 decision 1).

- No module under src/pyeconomics/core imports pyeconomics.data, statically
  or at run time: core, and so every model, stays free of the data layer.
- The value modules do no I/O: no socket, file, environment or clock, and no
  unsafe deserializer. Later steps' transport, cache, configuration and
  credential modules are the only ones allowed those, and stay off this list.
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "pyeconomics"
CORE = SRC / "core"

#: Modules that must stay pure: the value types and the provenance record.
PURE_MODULES = (
    CORE / "_fields.py",
    CORE / "provenance.py",
    SRC / "data" / "__init__.py",
    SRC / "data" / "errors.py",
    SRC / "data" / "terms.py",
    SRC / "data" / "types.py",
    SRC / "data" / "vintage.py",
)

#: Imports that reach the network, files, the environment, the clock, other
#: processes or an unsafe deserializer.
BANNED_IMPORTS = frozenset(
    {
        "asyncio",
        "ftplib",
        "glob",
        "http",
        "httpx",
        "io",
        "marshal",
        "os",
        "pathlib",
        "pickle",
        "requests",
        "selectors",
        "shelve",
        "shutil",
        "socket",
        "sqlite3",
        "ssl",
        "subprocess",
        "tempfile",
        "time",
        "urllib.request",
        "urllib3",
        "yaml",
    }
)
#: Calls that read the clock, the console or a file, or run code.
BANNED_CALLS = frozenset(
    {"open", "input", "eval", "exec", "now", "today", "utcnow", "getenv", "read_pickle"}
)


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _dynamic_imports(tree: ast.AST) -> set[str]:
    """String targets of importlib.import_module(...) and __import__(...)."""
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else getattr(func, "id", "")
            )
            first = node.args[0]
            if name in {
                "import_module",
                "__import__",
                "import_optional",
            } and isinstance(first, ast.Constant):
                targets.add(str(first.value))
    return targets


def _is_data(name: str) -> bool:
    return name == "pyeconomics.data" or name.startswith("pyeconomics.data.")


@pytest.mark.parametrize("path", sorted(CORE.rglob("*.py")), ids=lambda path: path.name)
def test_no_core_module_imports_the_data_layer(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [n for n in _imports(tree) | _dynamic_imports(tree) if _is_data(n)]
    assert found == [], f"{path.name} imports {found}"


def test_importing_core_and_every_model_loads_no_data_module(tmp_path: Path) -> None:
    # A fresh, isolated interpreter outside the checkout, so neither this
    # session's imports nor a stale tree at the repository root count.
    script = (
        "import sys, pyeconomics, pyeconomics.core\n"
        "from pyeconomics import registry\n"
        "registry.validate()\n"
        "loaded = sorted(m for m in sys.modules if m == 'pyeconomics.data' "
        "or m.startswith('pyeconomics.data.'))\n"
        "print(len(registry.ids()), loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    count, loaded = result.stdout.split(" ", 1)
    assert int(count) >= 32
    assert loaded.strip() == "[]"


@pytest.mark.parametrize("path", PURE_MODULES, ids=lambda path: path.name)
def test_the_value_modules_do_no_io(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = _imports(tree)
    banned = sorted(
        name
        for name in imported
        if name in BANNED_IMPORTS or name.split(".", 1)[0] in BANNED_IMPORTS
    )
    calls = sorted(
        {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute | ast.Name)
            and (
                node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            )
            in BANNED_CALLS
        }
    )
    assert (banned, calls) == ([], [])


def test_the_purity_scan_sees_what_it_bans() -> None:
    tree = ast.parse(
        "import os\nfrom urllib.request import urlopen\nimport datetime as dt\n"
        "dt.datetime.now()\nopen('x')\n"
    )
    assert {"os", "urllib.request"} <= _imports(tree)
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute | ast.Name)
    }
    assert {"now", "open"} <= calls & BANNED_CALLS
    dynamic = ast.parse("import importlib\nimportlib.import_module('pyeconomics.data')")
    assert _dynamic_imports(dynamic) == {"pyeconomics.data"}
