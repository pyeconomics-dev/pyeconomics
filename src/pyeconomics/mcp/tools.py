# src/pyeconomics/mcp/tools.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server's tools, generated from the registry (ADR-0012 decision 13).

:func:`build_tools` returns every tool the server offers, sorted by name:

- the five discovery tools of ROADMAP §4 4.5: ``search_models``,
  ``describe_model``, ``run_model``, ``get_series`` and ``list_sources``;
- one headline tool per id in :data:`~pyeconomics.mcp.headline.HEADLINE`, named
  ``<domain>_<name>`` from the id (:func:`tool_name`), whose input schema is the
  model's own and whose output schema is its result envelope.

A name matches ``^[a-z0-9_]{1,64}$``, stricter than the specification's 1 to 128
characters, so it survives a client that maps tools onto a function-calling API
with no dots or a 64-character limit; a name that does not, or two tools with one
name, fail the build with :class:`~pyeconomics.core.errors.RegistryError`.

Every description says what a tool does and returns, as a statement: none
addresses the assistant or tells it what to do, so nothing the server sends reads
as an instruction (ROADMAP §5 threat 7). In hosted mode a run's output schema
also admits a large result's notice (:func:`~pyeconomics.mcp.schemas.with_notice`)
and ``list_sources`` says nothing about keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, Literal

from pyeconomics import registry
from pyeconomics.core.errors import RegistryError
from pyeconomics.mcp import schemas
from pyeconomics.mcp.headline import HEADLINE

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyeconomics.core.model import Model

__all__ = [
    "DISCOVERY_TOOLS",
    "TOOL_NAME",
    "ToolKind",
    "ToolSpec",
    "build_tools",
    "tool_name",
]

#: What a tool does when called.
ToolKind = Literal["search", "describe", "run", "series", "sources", "headline"]
#: Every tool name matches this.
TOOL_NAME: Final = re.compile(r"[a-z0-9_]{1,64}")
#: The discovery tools, by name (ROADMAP §4 4.5).
DISCOVERY_TOOLS: Final = (
    "search_models",
    "describe_model",
    "run_model",
    "get_series",
    "list_sources",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolSpec:
    """One tool: its name, title, description, schemas and what it runs.

    ``open_world`` says whether a call may read a data source (a run that binds
    data, a series); ``model_id`` names a headline tool's model.
    """

    name: str
    title: str
    description: str
    kind: ToolKind
    input_schema: dict[str, Any] = field(repr=False)
    output_schema: dict[str, Any] = field(repr=False)
    open_world: bool = False
    model_id: str | None = None


def tool_name(model_id: str) -> str:
    """Return a headline tool's name: the model id with each dot an underscore.

    Raises
    ------
    RegistryError
        If the name does not match :data:`TOOL_NAME`.
    """
    name = model_id.replace(".", "_")
    if not TOOL_NAME.fullmatch(name):
        msg = f"the MCP tool name of {model_id!r} does not match {TOOL_NAME.pattern}"
        raise RegistryError(msg, problems=(msg,))
    return name


def _discovery(hosted: bool) -> list[ToolSpec]:  # noqa: FBT001 - one mode switch
    run_output = schemas.run_output()
    return [
        ToolSpec(
            name="search_models",
            title="Model search",
            description=(
                "Searches the registered economics and finance models by words in "
                "their ids, titles, tags, domains and summaries, best match first, "
                "or lists every model of a domain. Each entry gives the model's "
                "id, title, summary, domain, cost class and whether it can bind "
                "its inputs to data."
            ),
            kind="search",
            input_schema=schemas.search_input(registry.domains()),
            output_schema=schemas.search_output(),
        ),
        ToolSpec(
            name="describe_model",
            title="Model description",
            description=(
                "Describes one model: its formula, assumptions, limitations, "
                "references, examples, data bindings, input and output schemas "
                "(JSON Schema 2020-12, every number with its unit; rates are "
                "decimals) and its model card."
            ),
            kind="describe",
            input_schema=schemas.describe_input(),
            output_schema=schemas.describe_output(),
        ),
        ToolSpec(
            name="run_model",
            title="Model run",
            description=(
                "Runs any registered model on its inputs, or binds its inputs to "
                "the data catalog first (as of a date, or the latest), and returns "
                "the canonical result: the validated inputs, the outputs, the "
                "warnings and the manifest of every source read. Data whose terms "
                "do not let it reach an AI assistant is never used."
            ),
            kind="run",
            input_schema=schemas.run_input(),
            output_schema=schemas.with_notice(run_output) if hosted else run_output,
            open_world=True,
        ),
        ToolSpec(
            name="get_series",
            title="Series",
            description=(
                "Reads a series from the data catalog (a concept id) or from one "
                "provider (provider:series), with its source records and the "
                "attributions it must be shown with: at most the server's limit "
                "of observations, the most recent ones. Data whose terms do not "
                "let it reach an AI assistant is never returned."
            ),
            kind="series",
            input_schema=schemas.series_input(),
            output_schema=schemas.series_output(),
            open_world=True,
        ),
        ToolSpec(
            name="list_sources",
            title="Data sources",
            description=(
                "Lists every data provider with its licence class, whether its "
                "terms let its data reach an AI assistant (llm_use) and whether "
                "this server's policy permits it, its attribution and its terms "
                "page" + ("" if hosted else ", and whether a key is configured") + "."
            ),
            kind="sources",
            input_schema=schemas.sources_input(),
            output_schema=schemas.sources_output(local=not hosted),
        ),
    ]


def _headline(model: Model[Any, Any], hosted: bool) -> ToolSpec:  # noqa: FBT001
    spec = model.spec
    output = schemas.result_output(model)
    return ToolSpec(
        name=tool_name(model.id),
        title=spec.title,
        description=(
            f"{spec.summary} Runs {spec.title} ({model.id}, version {spec.version}) "
            "on the given inputs and returns its canonical result: the validated "
            "inputs, the outputs, the warnings and the manifest. Every number "
            "carries its unit in the input schema; rates are decimals."
        ),
        kind="headline",
        input_schema=schemas.tool_input(model),
        output_schema=schemas.with_notice(output) if hosted else output,
        model_id=model.id,
    )


def build_tools(
    *, hosted: bool = False, headline: Iterable[str] = HEADLINE
) -> tuple[ToolSpec, ...]:
    """Return every tool, sorted by name.

    Parameters
    ----------
    hosted
        Build the hosted server's tools: a run may answer a large result's
        notice, and ``list_sources`` says nothing about keys.
    headline
        The ids of the models with a tool of their own. An id the installed
        registry does not hold is left out, as every surface serves the registry
        it finds; the shipped registry holds every id of
        :data:`~pyeconomics.mcp.headline.HEADLINE` (a test checks it).

    Raises
    ------
    RegistryError
        For a headline id that is an alias, a name that does not match
        :data:`TOOL_NAME`, or two tools with one name.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - as run() does

    found = installed()
    aliases = found.aliases()
    held = {model.id for model in found.models()}
    tools = _discovery(hosted)
    for model_id in headline:
        if model_id in aliases:
            msg = f"the headline id {model_id!r} is an alias of {aliases[model_id]!r}"
            raise RegistryError(msg, problems=(msg,))
        if model_id in held:
            tools.append(_headline(registry.get(model_id), hosted))
    names = [tool.name for tool in tools]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        msg = f"two MCP tools are named {repeated[0]!r}"
        raise RegistryError(msg, problems=(msg,))
    return tuple(sorted(tools, key=lambda tool: tool.name))
