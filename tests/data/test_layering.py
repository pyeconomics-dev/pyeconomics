# tests/data/test_layering.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data layer's boundaries (ADR-0011 decision 1).

- No module under src/pyeconomics/core imports pyeconomics.data, statically
  or at run time: core, and so every model, stays free of the data layer.
- The value modules do no I/O: no socket, file, environment or clock, and no
  unsafe deserializer. The configuration and credential modules that read
  files and the environment (Step 3), the transport (Step 4), and later the
  cache, are the only ones allowed those (IO_MODULES); every module under
  src/pyeconomics/data is on exactly one of the two lists.
- Only the transport opens a socket (it alone imports urllib3, truststore,
  ssl and the like) and only the transport and the credential modules reveal a
  key (the `secret-reveal` semgrep rule, checked here too); importing the data
  layer imports neither urllib3 nor truststore (Step 4).
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
    CORE / "transforms.py",
    CORE / "binding.py",
    SRC / "data" / "api.py",
    SRC / "data" / "bindings.py",
    SRC / "data" / "resolver.py",
    SRC / "data" / "catalog" / "__init__.py",
    SRC / "data" / "catalog" / "checks.py",
    SRC / "data" / "catalog" / "definitions.py",
    SRC / "data" / "catalog" / "factors.py",
    SRC / "data" / "catalog" / "fiscal.py",
    SRC / "data" / "catalog" / "growth.py",
    SRC / "data" / "catalog" / "international.py",
    SRC / "data" / "catalog" / "labour.py",
    SRC / "data" / "catalog" / "markets.py",
    SRC / "data" / "catalog" / "output.py",
    SRC / "data" / "catalog" / "prices.py",
    SRC / "data" / "catalog" / "projections.py",
    SRC / "data" / "catalog" / "rates.py",
    SRC / "data" / "catalog" / "transforms.py",
    SRC / "data" / "providers" / "_finance.py",
    SRC / "data" / "providers" / "ken_french.py",
    SRC / "data" / "providers" / "shiller.py",
    SRC / "data" / "providers" / "aqr.py",
    SRC / "data" / "providers" / "hou_xue_zhang.py",
    SRC / "data" / "providers" / "jkp.py",
    SRC / "data" / "providers" / "open_source_asset_pricing.py",
    SRC / "data" / "providers" / "cboe.py",
    SRC / "data" / "providers" / "coin_metrics.py",
    SRC / "data" / "providers" / "damodaran.py",
    SRC / "data" / "providers" / "yfinance.py",
    SRC / "data" / "records.py",
    SRC / "data" / "providers" / "treasury.py",
    SRC / "data" / "providers" / "fed_board.py",
    SRC / "data" / "providers" / "nyfed.py",
    SRC / "data" / "providers" / "openfigi.py",
    SRC / "data" / "providers" / "sec_edgar.py",
    SRC / "data" / "providers" / "_research.py",
    SRC / "data" / "providers" / "philadelphia_fed.py",
    SRC / "data" / "providers" / "atlanta_fed.py",
    SRC / "data" / "providers" / "cleveland_fed.py",
    SRC / "data" / "providers" / "cbo.py",
    SRC / "data" / "providers" / "penn_world_table.py",
    CORE / "_fields.py",
    CORE / "provenance.py",
    SRC / "data" / "__init__.py",
    SRC / "data" / "_released.py",
    SRC / "data" / "credentials" / "__init__.py",
    SRC / "data" / "cache" / "policy.py",
    SRC / "data" / "credentials" / "dotenv.py",
    SRC / "data" / "credentials" / "secret.py",
    SRC / "data" / "errors.py",
    SRC / "data" / "modes.py",
    SRC / "data" / "providers" / "__init__.py",
    SRC / "data" / "providers" / "_shared.py",
    SRC / "data" / "providers" / "_international.py",
    SRC / "data" / "providers" / "_sdmx.py",
    SRC / "data" / "providers" / "bis.py",
    SRC / "data" / "providers" / "dbnomics.py",
    SRC / "data" / "providers" / "ecb.py",
    SRC / "data" / "providers" / "eurostat.py",
    SRC / "data" / "providers" / "imf.py",
    SRC / "data" / "providers" / "oecd.py",
    SRC / "data" / "providers" / "world_bank.py",
    SRC / "data" / "providers" / "base.py",
    SRC / "data" / "providers" / "bea.py",
    SRC / "data" / "providers" / "bls.py",
    SRC / "data" / "providers" / "census.py",
    SRC / "data" / "providers" / "fred.py",
    SRC / "data" / "providers" / "rules.py",
    SRC / "data" / "redaction.py",
    SRC / "data" / "registry.py",
    SRC / "data" / "terms.py",
    SRC / "data" / "transport" / "__init__.py",
    SRC / "data" / "transport" / "base.py",
    SRC / "data" / "transport" / "cassette.py",
    SRC / "data" / "transport" / "ratelimit.py",
    SRC / "data" / "types.py",
    SRC / "data" / "vintage.py",
)

#: The data layer's I/O modules: the only ones that read files, the
#: environment or the network (ADR-0011 decision 1).
IO_MODULES = (
    SRC / "data" / "transport" / "yahoo.py",
    SRC / "data" / "transport" / "recording.py",
    SRC / "data" / "transport" / "files.py",
    SRC / "data" / "cache" / "__init__.py",
    SRC / "data" / "cache" / "store.py",
    SRC / "data" / "config.py",
    SRC / "data" / "credentials" / "chain.py",
    SRC / "data" / "transport" / "http.py",
    SRC / "data" / "transport" / "sdmx.py",
    SRC / "data" / "transport" / "replay.py",
)

#: Imports that open a socket or speak a network protocol: the transport's alone.
NETWORK_IMPORTS = frozenset(
    {
        "ftplib",
        "http",
        "httpx",
        "imaplib",
        "poplib",
        "requests",
        "smtplib",
        "socket",
        "socketserver",
        "ssl",
        "truststore",
        "urllib.request",
        "urllib3",
        "xmlrpc",
    }
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


def test_every_data_module_is_pure_or_a_named_io_module() -> None:
    modules = set((SRC / "data").rglob("*.py"))
    assert set(PURE_MODULES) & set(IO_MODULES) == set()
    unlisted = sorted(
        path.relative_to(SRC).as_posix()
        for path in modules - set(PURE_MODULES) - set(IO_MODULES)
    )
    missing = sorted(
        path.relative_to(SRC).as_posix()
        for path in {*PURE_MODULES, *IO_MODULES}
        if not path.is_file()
    )
    assert (unlisted, missing) == ([], [])


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


def _is_network(name: str) -> bool:
    return any(name == n or name.startswith(n + ".") for n in NETWORK_IMPORTS)


def _reveals(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "reveal"
        for node in ast.walk(tree)
    )


def test_only_the_transport_imports_a_network_library() -> None:
    transport = SRC / "data" / "transport"
    offenders = {}
    for path in sorted(SRC.rglob("*.py")):
        if transport in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = sorted(
            n for n in _imports(tree) | _dynamic_imports(tree) if _is_network(n)
        )
        if found:
            offenders[path.relative_to(SRC).as_posix()] = found
    assert offenders == {}


def test_only_the_transport_and_the_credential_modules_reveal_a_key() -> None:
    allowed = (SRC / "data" / "transport", SRC / "data" / "credentials")
    offenders = [
        path.relative_to(SRC).as_posix()
        for path in sorted(SRC.rglob("*.py"))
        if not any(directory in path.parents for directory in allowed)
        and _reveals(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert offenders == []


def test_the_transport_is_where_a_key_is_revealed() -> None:
    http = ast.parse(
        (SRC / "data" / "transport" / "http.py").read_text(encoding="utf-8")
    )
    assert _reveals(http)
    for name in ("base.py", "cassette.py", "ratelimit.py", "replay.py", "__init__.py"):
        tree = ast.parse(
            (SRC / "data" / "transport" / name).read_text(encoding="utf-8")
        )
        assert not _reveals(tree), name


def test_the_network_scan_sees_what_it_bans() -> None:
    tree = ast.parse(
        "import urllib3\nfrom http.client import HTTPSConnection\nimport pandas"
    )
    found = {n for n in _imports(tree) if _is_network(n)}
    assert found == {"urllib3", "http.client", "http.client.HTTPSConnection"}
    assert _reveals(ast.parse("key.reveal()"))
    assert not _reveals(ast.parse("key.forget()"))


def test_importing_the_data_layer_imports_neither_urllib3_nor_truststore(
    tmp_path: Path,
) -> None:
    script = (
        "import sys\n"
        "import pyeconomics.data, pyeconomics.data.transport\n"
        "from pyeconomics.data import registry\n"
        "registry.validate()\n"
        "from pyeconomics.data.transport.http import HttpTransport\n"
        "HttpTransport()\n"
        "names = ('urllib3', 'truststore', 'ssl')\n"
        "hits = sorted(m for m in names if m in sys.modules)\n"
        "print(hits)\n"
    )
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    # ssl may arrive with other standard-library users; urllib3 and truststore never.
    assert "urllib3" not in result.stdout
    assert "truststore" not in result.stdout


def test_bind_is_exported_lazily_so_importing_pyeconomics_loads_no_data_module(
    tmp_path: Path,
) -> None:
    script = (
        "import sys\n"
        "import pyeconomics\n"
        "def data_modules():\n"
        "    return [m for m in sys.modules if m.startswith('pyeconomics.data')]\n"
        "print(len(data_modules()))\n"
        "function = pyeconomics.bind\n"
        "print(function.__module__, 'pyeconomics.data.bindings' in data_modules())\n"
        "print('bind' in pyeconomics.__all__, pyeconomics.bind is function)\n"
        "try:\n"
        "    pyeconomics.no_such_name\n"
        "except AttributeError as error:\n"
        "    print(error)\n"
    )
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stdout.splitlines() == [
        "0",
        "pyeconomics.data.bindings True",
        "True True",
        "module 'pyeconomics' has no attribute 'no_such_name'",
    ]
