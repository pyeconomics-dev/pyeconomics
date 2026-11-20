# tests/repo/test_public_api.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""docs/public-api.md: the public surface 1.0.0 promises, derived from the code.

ADR-0003 makes these public at 1.0.0 and ADR-0013 decision 17 freezes them in
Phase 5 Step 19. Each inventory in docs/public-api.md is a fenced ``text`` block
after a ``<!-- inventory: <key> -->`` line, and this module derives the same
block from the code:

- ``python <module>``: the module's ``__all__``, for every package of
  ``pyeconomics`` but the model packages (whose models are the permanent ids),
  ``pyeconomics.registry``, every module the user documentation imports from by
  path, and ``pyeconomics_app``;
- ``cli``: the Cyclopts command tree, each command's arguments and options and
  the choices an option takes, and the fixed options of ``models run ID``;
- ``rest``: the OpenAPI operations (method, path, operation id and query
  parameters), a model's two run operations as a rule every model follows, and
  the routes outside the document;
- ``mcp``: the tool names (the same in both modes) and the resource;
- ``problems``: ``problems.ROWS`` (slug, HTTP status, exit code) and the type URI;
- ``formats``: ``registry.json``'s format, the manifest schema, the export
  formats, the REST ``?format=`` values and a bundle's members;
- ``settings``: the settings keys, the files, every environment variable the
  package reads and every key variable;
- ``distribution``: the distributions, the extras, the console script and the
  entry-point groups;
- ``pages``: web/released-pages.json, each generated family counted and every
  other page by path;
- ``ids``: the permanent model, provider and concept ids, counted from their
  ledgers.

A difference fails with the block the code gives, so the change is reviewed and
pasted, never regenerated unseen. The inventory's fingerprint, a digest of every
block, is written in docs/public-api.md and must appear in CHANGELOG.md: a change
to the public surface is recorded in the inventory and the changelog together,
and after 1.0.0 follows ADR-0003. ``uv run python tests/repo/test_public_api.py``
prints every block and the fingerprint.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import io
import json
import re
import sys
import textwrap
import tomllib
import types
import typing
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from cyclopts import App

REPO: Final = Path(__file__).resolve().parents[2]
SRC: Final = REPO / "src" / "pyeconomics"
INVENTORY: Final = REPO / "docs" / "public-api.md"
CHANGELOG: Final = REPO / "CHANGELOG.md"
LEDGER: Final = REPO / "web" / "released-pages.json"
APP_INIT: Final = (
    REPO / "packages" / "pyeconomics-app" / "src" / "pyeconomics_app" / "__init__.py"
)

#: A marker, then the fenced block it names.
_BLOCK: Final = re.compile(
    r"^<!-- inventory: (?P<key>[a-z_.]+(?: [a-z_.]+)?) -->\n"
    r"```text\n(?P<body>.*?)^```$",
    re.MULTILINE | re.DOTALL,
)
_FINGERPRINT: Final = re.compile(r"Inventory fingerprint: `(sha256:[0-9a-f]{16})`")
#: The documentation a user reads, whose path imports become public modules; the
#: records of how the project was built (roadmaps, ADRs, release records, the
#: design record, operations) and generated pages are not part of it.
_DOCS_LEFT_OUT: Final = frozenset(
    {
        "roadmap",
        "adr",
        "releases",
        "design",
        "operations",
        "_ext",
        "_build",
        "gallery",
        "study-paths",
        "reference",
    }
)
_PATH_IMPORT: Final = re.compile(r"\b(?:from|import)\s+(pyeconomics(?:\.[a-z_0-9]+)+)")
_WIDTH: Final = 79


# --- the code's side ------------------------------------------------------------


def _documentation() -> Iterable[Path]:
    yield REPO / "README.md"
    yield REPO / "CONTRIBUTING.md"
    for path in sorted((REPO / "docs").rglob("*")):
        parts = path.relative_to(REPO / "docs").parts
        if (
            path.suffix in {".md", ".py"}
            and parts[0] not in _DOCS_LEFT_OUT
            and path != INVENTORY
            and not path.name.startswith("phase")
            and path.name != "conftest.py"
        ):
            yield path


def documented_modules() -> list[str]:
    """Every module (not package) the user documentation imports from by path."""
    found: set[str] = set()
    for path in _documentation():
        for name in _PATH_IMPORT.findall(path.read_text(encoding="utf-8")):
            try:
                module = importlib.import_module(name)
            except ImportError:  # an attribute written as a module path
                continue
            if not hasattr(module, "__path__"):
                found.add(name)
    return sorted(found)


def packages() -> list[str]:
    """Every package of pyeconomics with a non-empty ``__all__``, models aside."""
    names = []
    for init in sorted(SRC.rglob("__init__.py")):
        parts = init.parent.relative_to(SRC.parent).parts
        if len(parts) > 1 and parts[1] == "models":
            continue
        name = ".".join(parts)
        if getattr(importlib.import_module(name), "__all__", None):
            names.append(name)
    return names


def python_modules() -> list[str]:
    return sorted({*packages(), "pyeconomics.registry", *documented_modules()})


def python_names(module: str) -> list[str]:
    if module == "pyeconomics_app":
        tree = ast.parse(APP_INIT.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            ):
                return sorted(ast.literal_eval(node.value))
        return []
    exported = importlib.import_module(module).__all__
    assert len(set(exported)) == len(exported), f"{module}.__all__ repeats a name"
    return sorted(exported)


def _choices(hint: object) -> tuple[str, ...]:
    origin = typing.get_origin(hint)
    if origin is Literal:
        return tuple(sorted(str(value) for value in typing.get_args(hint)))
    if origin in {typing.Union, types.UnionType}:
        for member in typing.get_args(hint):
            found = _choices(member)
            if found:
                return found
    return ()


def _arguments(app: App, *, leave_out: Callable[[str], bool] = lambda _: False) -> str:
    positional: list[str] = []
    options: list[str] = []
    for argument in app.assemble_argument_collection(parse_docstring=False):
        if not argument.show or leave_out(argument.field_info.name):
            continue
        choices = _choices(argument.hint)
        suffix = f"={{{','.join(choices)}}}" if choices else ""
        names = [f"{name}{suffix}" for name in argument.names]
        if argument.field_info.kind in {
            argument.field_info.POSITIONAL_ONLY,
            argument.field_info.VAR_POSITIONAL,
        }:
            positional.extend(names)
        else:
            options.extend(names)
            options.extend(argument.negatives)
    # A flag's negative can be among its names too (--figures / --no-figures).
    return " ".join([*positional, *sorted(set(options))])


def _commands(app: App, path: list[str], flags: frozenset[str]) -> Iterable[str]:
    for name in app:
        if name in flags:
            continue
        sub = app[name]
        children = [child for child in sub if child not in flags]
        if children:
            yield from _commands(sub, [*path, name], flags)
        else:
            yield " ".join(["pyeconomics", *path, name, _arguments(sub)]).rstrip()


@cache
def cli_lines() -> tuple[str, ...]:
    from pyeconomics.cli import build_app  # noqa: PLC0415
    from pyeconomics.cli.model_commands import prepare_run  # noqa: PLC0415
    from pyeconomics.cli.output import Streams  # noqa: PLC0415

    app = build_app(
        Streams(stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())
    )
    flags = frozenset((*app.help_flags, *app.version_flags))
    meta = _arguments(app.meta)
    lines = [" ".join(["pyeconomics", meta, *sorted(flags)])]
    lines.extend(sorted(_commands(app, [], flags)))
    # A model's run command: its fixed options; each input field adds --<field>.
    model = "foundations.time_value"
    prepare_run(app, ["models", "run", model])
    fixed = _arguments(
        app["models"]["run"][model], leave_out=lambda name: name.startswith("field_")
    )
    lines.append(f"pyeconomics models run <model id> {fixed}")
    return tuple(lines)


@cache
def rest_lines() -> tuple[str, ...]:
    from pyeconomics import registry  # noqa: PLC0415
    from pyeconomics.server.app import create_app  # noqa: PLC0415
    from pyeconomics.server.settings import ServerSettings  # noqa: PLC0415

    app = create_app(mode="local", settings=ServerSettings(workers=0))
    document = app.openapi()
    fixed: list[str] = []
    runs: set[str] = set()
    model_paths = {
        f"/v1/models/{model_id}/run": model_id for model_id in registry.ids()
    }
    for path, item in document["paths"].items():
        for method, operation in item.items():
            query = ",".join(
                sorted(
                    parameter["name"]
                    for parameter in operation.get("parameters", [])
                    if parameter.get("in") == "query"
                )
            )
            operation_id = operation["operationId"]
            model_id = model_paths.get(path)
            if model_id is None:
                fixed.append(f"{method.upper()} {path} {operation_id} {query}".rstrip())
                continue
            stem = "run_" + model_id.replace(".", "_")
            rule = operation_id.replace(stem, "run_<model id>", 1)
            runs.add(
                f"{method.upper()} /v1/models/<model id>/run {rule} {query}".rstrip()
            )
    run_paths = {path for path in document["paths"] if path in model_paths}
    assert run_paths == set(model_paths), "a model has no run route"
    outside = []
    for route in app.router.routes:
        path = getattr(route, "path", "")
        if type(route).__name__ == "_McpRoute":
            outside.append(f"POST {path} (MCP Streamable HTTP)")
        elif getattr(route, "include_in_schema", True) is False:
            outside.extend(
                f"{method} {path} (outside the OpenAPI document)"
                for method in sorted(getattr(route, "methods", None) or ())
                if method != "HEAD"
            )
    return (*sorted(fixed), *sorted(runs), *sorted(outside))


@cache
def mcp_lines() -> tuple[str, ...]:
    from pyeconomics.mcp import apps  # noqa: PLC0415
    from pyeconomics.mcp.tools import build_tools  # noqa: PLC0415

    local = [tool.name for tool in build_tools()]
    hosted = [tool.name for tool in build_tools(hosted=True)]
    lines = [f"tool {name}" for name in local]
    lines.extend(
        f"tool {name} (hosted mode only)" for name in hosted if name not in local
    )
    lines.extend(
        f"tool {name} (local mode only)" for name in local if name not in hosted
    )
    lines.append(f"resource {apps.CHART_URI} {apps.MIME_TYPE}")
    return tuple(lines)


@cache
def problems_lines() -> tuple[str, ...]:
    from pyeconomics.cli.app import USAGE_EXIT_CODE  # noqa: PLC0415
    from pyeconomics.surfaces import problems  # noqa: PLC0415

    lines = [f"type {problems.TYPE_BASE}<slug>"]
    lines.extend(f"{row.slug} {row.status} {row.exit_code}" for row in problems.ROWS)
    lines.append(f"usage-error - {USAGE_EXIT_CODE}")
    return tuple(lines)


@cache
def formats_lines() -> tuple[str, ...]:
    from pyeconomics import exports  # noqa: PLC0415
    from pyeconomics.core.manifest import MANIFEST_SCHEMA_VERSION  # noqa: PLC0415
    from pyeconomics.exports.bundle import BUNDLE_MEMBERS  # noqa: PLC0415
    from pyeconomics.server import formats  # noqa: PLC0415
    from pyeconomics.surfaces.registry_schema import (  # noqa: PLC0415
        REGISTRY_FORMAT,
        REGISTRY_SCHEMA_ID,
    )

    return (
        f"registry.json format {REGISTRY_FORMAT} {REGISTRY_SCHEMA_ID}",
        f"manifest schema_version {MANIFEST_SCHEMA_VERSION}",
        f"exports {' '.join(sorted(exports.FORMATS))}",
        f"rest run ?format= {' '.join(sorted(formats.RUN_FORMATS))}",
        f"rest series ?format= {' '.join(sorted(formats.SERIES_FORMATS))}",
        f"bundle members {' '.join(BUNDLE_MEMBERS)}",
    )


def environment_variables() -> list[str]:
    """Every ``PYECONOMICS_*`` name the package's source reads or names."""
    from pyeconomics.data import config  # noqa: PLC0415

    names: set[str] = set()
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        names.update(re.findall(r"\bPYECONOMICS_[A-Z0-9_]*[A-Z0-9]\b", text))
        names.update(
            config.ENV_PREFIX + name
            for name in re.findall(r"\{ENV_PREFIX\}([A-Z][A-Z0-9_]*[A-Z0-9])", text)
        )
    names.update(config.ENV_PREFIX + name for name in config._ENVIRONMENT)  # noqa: SLF001
    names.update(config.ENV_PREFIX + name for name in config._SERVER_SECRETS)  # noqa: SLF001
    # A provider's time-to-live, PYECONOMICS_TTL_<PROVIDER>, is one family.
    names = {name for name in names if not name.startswith(f"{config.ENV_PREFIX}TTL_")}
    names.add(f"{config.ENV_PREFIX}TTL_<PROVIDER>")
    return sorted(names)


@cache
def settings_lines() -> tuple[str, ...]:
    from pyeconomics.ai import PROVIDERS  # noqa: PLC0415
    from pyeconomics.data import config, registry  # noqa: PLC0415

    lines = [f"setting {name}" for name in sorted(config.Settings.model_fields)]
    lines.extend((f"file {config.CONFIG_FILE}", f"file {config.DOTENV_FILE}"))
    lines.extend(f"env {name}" for name in environment_variables())
    keys = {registry.get(provider).info.key_variable for provider in registry.ids()} | {
        provider.info.key_variable for provider in PROVIDERS.values()
    }
    lines.extend(f"key {name}" for name in sorted(key for key in keys if key))
    return tuple(lines)


@cache
def distribution_lines() -> tuple[str, ...]:
    from pyeconomics.core import registry as models  # noqa: PLC0415
    from pyeconomics.data import registry as providers  # noqa: PLC0415

    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    member = tomllib.loads(
        (REPO / "packages" / "pyeconomics-app" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    lines = [
        f"distribution {project['project']['name']}",
        f"distribution {member['project']['name']}",
    ]
    lines.extend(
        f"extra {name}" for name in sorted(project["project"]["optional-dependencies"])
    )
    lines.extend(
        f"script {name} {target}"
        for name, target in sorted(project["project"]["scripts"].items())
    )
    groups = set(project["project"].get("entry-points", {}))
    read = {models.ENTRY_POINT_GROUP, providers.ENTRY_POINT_GROUP}
    assert read >= groups, "an entry-point group the code does not read"
    lines.extend(f"entry-point group {group}" for group in sorted(read))
    return tuple(lines)


#: A page path's generated family, by its first segment and depth.
_FAMILIES: Final = (
    (re.compile(r"/models/[a-z0-9-]+/[a-z0-9-]+/"), "/models/<domain>/<model>/"),
    (re.compile(r"/models/[a-z0-9-]+/"), "/models/<domain>/"),
    (re.compile(r"/data/(?:[a-z0-9-]+/){3,}"), "/data/<concept>/"),
    (re.compile(r"/problems/[a-z0-9-]+/"), "/problems/<slug>/"),
)


@cache
def pages_lines() -> tuple[str, ...]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["format"] == 1
    counts: dict[str, int] = {}
    single: list[str] = []
    for page in ledger["pages"]:
        family = next(
            (name for pattern, name in _FAMILIES if pattern.fullmatch(page)), None
        )
        if family is None:
            single.append(page)
        else:
            counts[family] = counts.get(family, 0) + 1
    lines = [f"family {name} {counts[name]}" for _, name in _FAMILIES if name in counts]
    lines.extend(f"page {page}" for page in single)
    return tuple(lines)


@cache
def ids_lines() -> tuple[str, ...]:
    from pyeconomics.core._released import RELEASED  # noqa: PLC0415
    from pyeconomics.data._released import CONCEPTS, PROVIDERS  # noqa: PLC0415

    return (
        f"models {len(RELEASED)} src/pyeconomics/core/_released.py",
        f"providers {len(PROVIDERS)} src/pyeconomics/data/_released.py",
        f"concepts {len(CONCEPTS)} src/pyeconomics/data/_released.py",
    )


_SECTIONS: Final[dict[str, Callable[[], tuple[str, ...]]]] = {
    "cli": cli_lines,
    "rest": rest_lines,
    "mcp": mcp_lines,
    "problems": problems_lines,
    "formats": formats_lines,
    "settings": settings_lines,
    "distribution": distribution_lines,
    "pages": pages_lines,
    "ids": ids_lines,
}


@cache
def derived() -> dict[str, tuple[str, ...]]:
    """Every block the code gives: a Python module's names, or a section's lines."""
    blocks = {
        f"python {module}": tuple(python_names(module))
        for module in [*python_modules(), "pyeconomics_app"]
    }
    blocks.update((key, section()) for key, section in _SECTIONS.items())
    return blocks


def fingerprint(blocks: dict[str, tuple[str, ...]]) -> str:
    text = json.dumps(blocks, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def render(key: str, values: Iterable[str]) -> str:
    """The block as docs/public-api.md writes it, marker and fence included."""
    if key.startswith("python "):
        body = (
            textwrap.fill(" ".join(values), _WIDTH, break_on_hyphens=False) or "(none)"
        )
    else:
        body = "\n".join(values)
    return f"<!-- inventory: {key} -->\n```text\n{body}\n```"


# --- the inventory's side ---------------------------------------------------------


def recorded() -> dict[str, tuple[str, ...]]:
    text = INVENTORY.read_text(encoding="utf-8")
    blocks: dict[str, tuple[str, ...]] = {}
    for match in _BLOCK.finditer(text):
        key, body = match["key"], match["body"]
        assert key not in blocks, f"docs/public-api.md has two {key!r} blocks"
        if key.startswith("python "):
            values = tuple(body.split()) if body.strip() != "(none)" else ()
        else:
            values = tuple(line.strip() for line in body.splitlines() if line.strip())
        blocks[key] = values
    return blocks


# --- the tests -----------------------------------------------------------------------


def test_the_inventory_has_exactly_the_blocks_the_code_gives() -> None:
    written, code = set(recorded()), set(derived())
    missing = "\n\n".join(render(key, derived()[key]) for key in sorted(code - written))
    assert not code - written, f"docs/public-api.md lacks these blocks:\n\n{missing}"
    assert not written - code, (
        f"docs/public-api.md has blocks no code gives: {sorted(written - code)}"
    )


@pytest.mark.parametrize("key", sorted(derived()))
def test_each_block_matches_the_code(key: str) -> None:
    written = recorded().get(key)
    code = derived()[key]
    assert written == code, (
        f"the public surface changed: {key!r} in docs/public-api.md differs from "
        f"the code. Record the change in the inventory, its fingerprint and "
        f"CHANGELOG.md (after 1.0.0, under ADR-0003). The code gives:\n\n"
        f"{render(key, code)}"
    )


def test_the_fingerprint_is_recorded_in_the_inventory_and_the_changelog() -> None:
    expected = fingerprint(derived())
    written = _FINGERPRINT.findall(INVENTORY.read_text(encoding="utf-8"))
    assert written == [expected], (
        f"docs/public-api.md must state 'Inventory fingerprint: `{expected}`' once"
    )
    assert expected in CHANGELOG.read_text(encoding="utf-8"), (
        f"CHANGELOG.md must record the change that gives the public API {expected}"
    )


def test_a_model_package_is_not_inventoried_by_its_modules() -> None:
    # Models are public by their permanent ids, not by their module paths.
    assert not any(key.startswith("python pyeconomics.models") for key in derived())


def test_every_documented_import_path_is_inventoried() -> None:
    blocks = derived()
    for module in documented_modules():
        assert f"python {module}" in blocks


def test_the_cli_derivation_reads_choices_and_arguments() -> None:
    lines = cli_lines()
    assert lines[0].startswith("pyeconomics --debug")
    assert any(line.startswith("pyeconomics data get TARGET ") for line in lines)
    assert any("--format={arrow,csv,json,parquet,table,xlsx}" in line for line in lines)
    assert lines[-1].startswith("pyeconomics models run <model id> --as-of ")
    assert not any("--context" in line or "--field" in line for line in lines)


def test_the_rest_derivation_covers_every_model_by_one_rule() -> None:
    lines = rest_lines()
    rules = [line for line in lines if "<model id>" in line]
    assert [line.split()[0] for line in rules] == ["GET", "POST"]
    assert any(line.startswith("POST /mcp ") for line in lines)


def test_pages_fall_into_families_or_are_named() -> None:
    lines = pages_lines()
    assert lines[0].startswith("family /models/<domain>/<model>/ ")
    assert "page /" in lines


if __name__ == "__main__":  # pragma: no cover - prints the blocks to paste
    blocks = derived()
    for key, values in blocks.items():
        sys.stdout.write(render(key, values) + "\n\n")
    sys.stdout.write(f"Inventory fingerprint: `{fingerprint(blocks)}`\n")
