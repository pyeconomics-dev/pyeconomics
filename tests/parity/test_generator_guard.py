# tests/parity/test_generator_guard.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Generator rule as a check: no surface hand-writes a model (Phase 4 Step 10).

ROADMAP §3 and ADR-0012 decision 2: every command, route and tool is generated
from the registry. Two checks hold the command line, the REST API and the MCP
server to it:

- **statically**, no string literal in ``src/pyeconomics/cli/``, ``server/`` or
  ``mcp/`` equals or names a registered model id, docstrings aside (their
  examples are documentation); ``mcp/headline.py``, the declared list of
  headline tools, is the one exception;
- **by construction**, a toy model registered only in a toy registry reaches
  every surface with no code change: the command line generates its run
  options, ``create_app`` its OpenAPI operation and route, and the MCP server
  runs it through ``run_model``, each answering the Python API's bytes.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import toy_models as toys
from parity_support import (
    CliSession,
    McpSession,
    Run,
    assert_same,
    cli_answer,
    mcp_answers,
    python_answer,
    rest_answer,
)
from pydantic import Field
from server_support import LOOPBACK_ONLY, client, openapi_of

from pyeconomics import registry
from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    ModelInputs,
    ModelOutputs,
    Rate,
    Registry,
    model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.mcp import build_server
from pyeconomics.server import openapi

pytestmark = LOOPBACK_ONLY

SOURCE = Path(__file__).resolve().parents[2] / "src" / "pyeconomics"
#: The generated surfaces.
SURFACES = ("cli", "server", "mcp")
#: The declared list of headline tools: data, reviewed when it changes.
DECLARED = SOURCE / "mcp" / "headline.py"

MODULES = sorted(
    path
    for surface in SURFACES
    for path in (SOURCE / surface).rglob("*.py")
    if path != DECLARED
)


def _docstrings(tree: ast.Module) -> set[int]:
    """Return the ids of the docstrings of a module, its classes and functions."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def _literals(path: Path) -> list[tuple[int, str]]:
    """Return every string literal of a module but its docstrings, with its line."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skipped = _docstrings(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skipped
    ]


def _naming(text: str, ids: frozenset[str]) -> list[str]:
    """Return the model ids a literal equals or names as a whole word."""
    if text in ids:
        return [text]
    return sorted(
        model_id
        for model_id in ids
        if re.search(rf"(?<![\w.]){re.escape(model_id)}(?![\w])", text)
    )


def test_the_scan_reads_every_surface_module() -> None:
    surfaces = {path.relative_to(SOURCE).parts[0] for path in MODULES}
    assert surfaces == set(SURFACES)
    assert len(MODULES) > 20


def test_the_scan_finds_a_hand_written_model_id() -> None:
    ids = frozenset(registry.ids())
    tree = ast.parse('"""Runs foundations.time_value."""\nX = "foundations.time_value"')
    skipped = _docstrings(tree)
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skipped
    ]
    assert [_naming(text, ids) for text in literals] == [["foundations.time_value"]]
    assert _naming("/v1/models/foundations.time_value/run", ids) == [
        "foundations.time_value"
    ]
    assert _naming("fixed_income", ids) == []


@pytest.mark.parametrize(
    "path", MODULES, ids=lambda path: path.relative_to(SOURCE).as_posix()
)
def test_no_surface_module_names_a_model(path: Path) -> None:
    ids = frozenset(registry.ids())
    named = [
        (line, model_id)
        for line, text in _literals(path)
        for model_id in _naming(text, ids)
    ]
    assert named == []


def test_the_declared_headline_list_names_only_registered_models() -> None:
    from pyeconomics.mcp.headline import HEADLINE  # noqa: PLC0415

    assert set(HEADLINE) <= set(registry.ids())


# --- a model only a toy registry holds ---------------------------------------------


class GeneratedInputs(ModelInputs):
    toy_rate: Rate = Field(ge=-1, le=1, description="A rate")


class GeneratedOutputs(ModelOutputs):
    doubled: Rate = Field(ge=-2, le=2, description="Twice the rate")


@model(
    id="foundations.toy_generated",
    version=1,
    title="Toy generated model",
    summary="Doubles a rate; only a toy registry holds it.",
    formula=(r"y = 2 r",),
    assumptions=("A toy.",),
    limitations=("It models nothing.",),
    references=(toys.FISHER,),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    no_invariants_reason="A toy for the generator guard.",
    examples=(Example(name="five_percent", inputs={"toy_rate": 0.05}),),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def generated(inputs: GeneratedInputs) -> GeneratedOutputs:
    return GeneratedOutputs(doubled=2 * inputs.toy_rate)


TOY = Run(generated.id, {"toy_rate": 0.05})


@pytest.fixture
def toy_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a registry holding only the toy the installed one, for one test."""
    toy = Registry.from_models(generated, distribution="toy-dist")
    monkeypatch.setattr(core_registry._CACHE, "registry", toy)  # noqa: SLF001
    assert generated.id not in toy.aliases()


@pytest.mark.usefixtures("toy_registry")
def test_a_toy_registry_model_reaches_every_surface_with_no_code_change() -> None:
    assert registry.ids() == (generated.id,)
    expected = python_answer(TOY)
    assert expected.body is not None

    cli = CliSession()
    shown = cli("models", "run", generated.id, "--help")
    assert shown.code == 0, shown.stderr
    assert "--toy-rate" in shown.text

    with client() as api:
        operations = {
            operation["operationId"]
            for item in openapi_of(api)["paths"].values()
            for operation in item.values()
        }
        assert openapi.operation_id(generated, "POST") in operations
        assert openapi.operation_id(generated, "GET") in operations
        rest = rest_answer(api, TOY)

    mcp = McpSession(build_server())
    try:
        listed = mcp.call("search_models", {"query": "toy generated"})
        assert [e["id"] for e in (listed.structured_content or {})["models"]] == [
            generated.id
        ]
        text, structured = mcp_answers(mcp, TOY)
    finally:
        mcp.close()

    assert_same(
        {
            "python": expected,
            "cli": cli_answer(cli, TOY),
            "rest": rest,
            "mcp text": text,
            "mcp structured": structured,
        }
    )
