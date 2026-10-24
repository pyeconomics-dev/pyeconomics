# tests/surfaces/test_surface_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The surfaces' boundaries (ADR-0012 decisions 1 and 2).

- No module under src/pyeconomics/core or data imports a surface package:
  surfaces, exports, cli, server, mcp or ai.
- No module under src/pyeconomics/surfaces imports a framework: fastapi,
  starlette, uvicorn, mcp, cyclopts or rich.
- A fresh interpreter's ``import pyeconomics`` loads no framework and no surface,
  and ``import pyeconomics.surfaces`` loads no data module, even after a run that
  reads no data: the data layer arrives with the first bind.
- ``import pyeconomics.cli`` loads neither Cyclopts nor rich (they load when the
  command line is built), and ``pyeconomics --version`` and ``--help`` discover
  no model and load no data module, which keeps them fast (Step 4).
- No surface module runs a model but through ``invoke``: none imports
  ``core.runner`` or calls ``run``, ``run_model``, ``bind`` or ``bind_model``.
  The scan covers each surface package as a later step adds it (Step 4's cli/
  first).
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "pyeconomics"

#: The packages ADR-0012 puts above core and data.
SURFACE_PACKAGES = ("surfaces", "exports", "cli", "server", "mcp", "ai")
#: The frameworks the surface core never imports.
FRAMEWORKS = ("fastapi", "starlette", "uvicorn", "mcp", "cyclopts", "rich")
#: The surface packages that must run a model through invoke.
INVOKING_PACKAGES = ("exports", "cli", "server", "mcp", "ai")
#: What only invoke may call to run or bind a model.
RUNNERS = frozenset({"run", "run_model", "run_batch", "bind", "bind_model"})


def _imports(tree: ast.AST) -> set[str]:
    """Every module a tree imports, statically or by a constant dynamic import."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", "")
            )
            in {"import_module", "__import__", "import_optional"}
        ):
            names.add(str(node.args[0].value))
    return names


def _is_surface(name: str) -> bool:
    return any(
        name == f"pyeconomics.{package}" or name.startswith(f"pyeconomics.{package}.")
        for package in SURFACE_PACKAGES
    )


def _is_framework(name: str) -> bool:
    return name.split(".", 1)[0] in FRAMEWORKS


def _runner_uses(tree: ast.AST) -> set[str]:
    """The ways a tree runs or binds a model itself."""
    found = {name for name in _imports(tree) if name == "pyeconomics.core.runner"}
    found |= {
        name
        for name in _imports(tree)
        if name.startswith("pyeconomics.") and name.rpartition(".")[2] in RUNNERS
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in RUNNERS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"pyeconomics", "runner", "bindings"}
        ):
            found.add(f"{node.func.value.id}.{node.func.attr}()")
    return found


def _sources(*directories: str) -> list[Path]:
    return sorted(
        path for directory in directories for path in (SRC / directory).rglob("*.py")
    )


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", _sources("core", "data"), ids=lambda path: path.name)
def test_no_core_or_data_module_imports_a_surface(path: Path) -> None:
    found = sorted(name for name in _imports(_parse(path)) if _is_surface(name))
    assert found == [], f"{path.relative_to(SRC)} imports {found}"


@pytest.mark.parametrize("path", _sources("surfaces"), ids=lambda path: path.name)
def test_no_surfaces_module_imports_a_framework(path: Path) -> None:
    found = sorted(name for name in _imports(_parse(path)) if _is_framework(name))
    assert found == [], f"{path.relative_to(SRC)} imports {found}"


def test_no_surface_module_runs_a_model_but_through_invoke() -> None:
    offenders = {
        path.relative_to(SRC).as_posix(): sorted(_runner_uses(_parse(path)))
        for path in _sources(*INVOKING_PACKAGES)
    }
    assert {name: uses for name, uses in offenders.items() if uses} == {}


def test_the_scans_see_what_they_ban() -> None:
    tree = ast.parse(
        "import fastapi.routing\nfrom rich import print\n"
        "from pyeconomics.surfaces import invoke\n"
        "import importlib\nimportlib.import_module('cyclopts')\n"
        "from pyeconomics.core.runner import run_model\n"
        "from pyeconomics import run\nimport pyeconomics\npyeconomics.bind('x')\n"
    )
    names = _imports(tree)
    assert {n for n in names if _is_framework(n)} == {
        "fastapi.routing",
        "rich",
        "rich.print",
        "cyclopts",
    }
    assert {n for n in names if _is_surface(n)} == {
        "pyeconomics.surfaces",
        "pyeconomics.surfaces.invoke",
    }
    assert _runner_uses(tree) == {
        "pyeconomics.core.runner",
        "pyeconomics.core.runner.run_model",
        "pyeconomics.run",
        "pyeconomics.bind()",
    }
    assert not _is_framework("pyeconomics.mcp")
    assert _is_surface("pyeconomics.mcp.tools")


def _fresh(script: str, tmp_path: Path) -> list[str]:
    # A fresh, isolated interpreter outside the checkout, so neither this
    # session's imports nor a stale tree at the repository root count.
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.splitlines()


_LOADED = (
    "def loaded(prefixes):\n"
    "    return sorted(m for m in sys.modules if any(\n"
    "        m == p or m.startswith(p + '.') for p in prefixes))\n"
)


def test_importing_pyeconomics_loads_no_framework_and_no_surface(
    tmp_path: Path,
) -> None:
    script = (
        "import sys\nimport pyeconomics\n"
        + _LOADED
        + f"print(loaded({FRAMEWORKS!r}))\n"
        + f"print(loaded({tuple(f'pyeconomics.{p}' for p in SURFACE_PACKAGES)!r}))\n"
    )
    assert _fresh(script, tmp_path) == ["[]", "[]"]


def test_importing_the_cli_loads_neither_cyclopts_nor_rich(tmp_path: Path) -> None:
    script = (
        "import sys\nimport pyeconomics\nimport pyeconomics.cli\n"
        + _LOADED
        + "print(loaded(('cyclopts', 'rich')))\n"
    )
    assert _fresh(script, tmp_path) == ["[]"]


def test_version_and_help_discover_no_model_and_load_no_data(tmp_path: Path) -> None:
    script = (
        "import io, sys\nfrom pyeconomics.cli import main\n"
        "from pyeconomics.cli.output import Streams\n"
        + _LOADED
        + "for argv in (['--version'], ['--help'], ['models', '--help']):\n"
        "    out = io.BytesIO()\n"
        "    streams = Streams(stdin=io.BytesIO(), stdout=out, stderr=io.BytesIO())\n"
        "    print(main(argv, streams=streams), bool(out.getvalue()))\n"
        "print(loaded(('pyeconomics.data', 'pyeconomics.models')))\n"
        "print(loaded(('cyclopts',)) != [])\n"
    )
    assert _fresh(script, tmp_path) == ["0 True", "0 True", "0 True", "[]", "True"]


def test_the_surfaces_load_no_data_module_until_a_bind(tmp_path: Path) -> None:
    script = (
        "import sys\nimport pyeconomics.surfaces as s\n"
        + _LOADED
        + "print(loaded(('pyeconomics.data',)))\n"
        "inputs = {'calculation': 'future_value', 'present_value': 100,\n"
        "          'rate': 0.05, 'periods': 2}\n"
        "result = s.invoke('foundations.time_value', inputs)\n"
        "print(result.model_id, loaded(('pyeconomics.data',)))\n"
        + f"print(loaded({FRAMEWORKS!r}))\n"
    )
    assert _fresh(script, tmp_path) == ["[]", "foundations.time_value []", "[]"]
