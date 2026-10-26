# src/pyeconomics/mcp/server.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server: the registry's tools on the official SDK (ADR-0012 13 and 14).

:func:`build_server` returns an ``mcp`` 2.x low-level
:class:`~mcp.server.lowlevel.Server` that serves specification 2026-07-28
statelessly (``server/discover``, no handshake) and, through the same handlers,
the SDK's earlier handshake revisions. It is built on the low-level server
because every tool's schemas are generated from the registry rather than from a
Python signature, which is the case the SDK documents that server for. Its tools
come from :func:`~pyeconomics.mcp.tools.build_tools`, sorted by name, and the
tool list carries a public cache hint: it changes only with the installation.

What a tool call returns:

- a run (``run_model`` or a headline tool) goes through the server's
  :class:`~pyeconomics.mcp.execution.Executor` with the server's ``llm_use``
  policy, and answers the canonical result as structured content, the same
  ``Result.to_json()`` text as a text block, and a one-line summary
  (:func:`~pyeconomics.surfaces.envelope.summary_of`) as a second block, with
  the model's chart as a Plotly figure in its ``_meta`` when the ``plot`` extra
  is installed (:mod:`~pyeconomics.mcp.apps`); in hosted mode a result larger
  than the server's limit answers a notice instead: its summary, size and hash,
  and the REST API's download of it;
- ``get_series`` returns at most the server's limit of observations, with the
  attributions and notices the data must be shown with;
- ``search_models``, ``describe_model`` and ``list_sources`` return the
  listing entries, ``registry.describe``'s document and the sources, as the
  command line and the REST API do; ``list_sources`` says, in local mode only,
  whether each key is configured (``has_key``), never its value.

Every run tool names the chart page, ``ui://pyeconomics/chart``, in its
``_meta.ui.resourceUri``, and the server lists and reads that one resource: a
client that supports MCP Apps draws the figure beside the answer, and any other
client ignores both.

Every answer passes the final check before it is sent
(:func:`~pyeconomics.surfaces.gate.check_document`): one still carrying a
``forbidden`` source, or an ``unclear`` one without the opt-in, is withheld with
the ``llm-use-forbidden`` problem. Every failure answers a tool error whose text
is its problem from the error table (:mod:`~pyeconomics.surfaces.problems`),
logged as one scrubbed record; an unknown tool is a protocol error.

What no tool does: execute code, fetch a URL, read or write a file, read or
store a key, or change the cache. Targets are ids the registry or the catalog
validates; the ``llm_use`` opt-in is the user's configuration, read when the
server is built, and no argument of any tool can change it.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode

from mcp import types
from mcp.server import CacheHint, Server
from mcp.shared.exceptions import MCPError

from pyeconomics import __version__, registry
from pyeconomics.core import _fields as f
from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import LlmUsePolicy
from pyeconomics.mcp import apps
from pyeconomics.mcp.execution import Executor, LocalExecutor, Refused
from pyeconomics.mcp.headline import HEADLINE
from pyeconomics.mcp.schemas import DEFAULT_SEARCH_LIMIT
from pyeconomics.mcp.tools import ToolSpec, build_tools
from pyeconomics.surfaces import codec, gate, listing
from pyeconomics.surfaces.budgets import GET_INPUTS_LIMIT
from pyeconomics.surfaces.envelope import summary_of
from pyeconomics.surfaces.invoke import BindRequest
from pyeconomics.surfaces.problems import Problem, report

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from mcp.server import ServerRequestContext

    from pyeconomics.core.model import Model

__all__ = [
    "DEFAULT_RESULT_LIMIT",
    "DEFAULT_SERIES_LIMIT",
    "LOGGER",
    "SERVER_NAME",
    "McpMode",
    "build_server",
]

#: Where the server is local (stdio, or HTTP on this machine) or hosted.
McpMode = Literal["local", "hosted"]
#: The name the server gives itself.
SERVER_NAME: Final = "pyeconomics"
#: The largest canonical result a hosted run returns whole, in bytes: 256 KiB.
DEFAULT_RESULT_LIMIT: Final = 256 * 1024
#: The most observations ``get_series`` returns per fetch.
DEFAULT_SERIES_LIMIT: Final = 1_000
#: The logger every problem is recorded on.
LOGGER: Final = "pyeconomics.mcp"
#: How long a client may keep the tool list and the discovery answer: an hour.
_LIST_TTL_MS: Final = 3_600_000
_BIND_FIELDS: Final = ("as_of", "vintage", "profile", "concepts", "parameters")
_SERIES_OPTIONS: Final = ("start", "end", "as_of", "vintage", "provider")
_LOG: Final = logging.getLogger(LOGGER)


def _annotations(spec: ToolSpec) -> types.ToolAnnotations:
    return types.ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=spec.open_world,
    )


def _tool(spec: ToolSpec) -> types.Tool:
    return types.Tool(
        name=spec.name,
        title=spec.title,
        description=spec.description,
        input_schema=spec.input_schema,
        output_schema=spec.output_schema,
        annotations=_annotations(spec),
        meta=apps.TOOL_META if spec.kind in {"run", "headline"} else None,
    )


# --- arguments ---------------------------------------------------------------------


def _arguments(
    given: Mapping[str, Any] | None, allowed: Iterable[str]
) -> dict[str, Any]:
    """Return a tool's arguments, refusing a name it does not take."""
    found = dict(given or {})
    names = frozenset(allowed)
    unknown = sorted(set(found) - names)
    if unknown:
        takes = ", ".join(sorted(names)) or "none"
        msg = f"this tool takes no argument {unknown[0]!r} (it takes: {takes})"
        raise InputError(msg)
    return found


def _text(
    arguments: Mapping[str, Any], name: str, *, required: bool = False
) -> str | None:
    value = arguments.get(name)
    if value is None:
        if required:
            msg = f"{name} is required"
            raise InputError(msg)
        return None
    return f.text(value, name, max_length=256)


def _day(arguments: Mapping[str, Any], name: str) -> str | None:
    text = _text(arguments, name)
    return None if text is None else f.parse_day(text, name).isoformat()


def _mapping(arguments: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = arguments.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        msg = f"{name} is an object"
        raise InputError(msg)
    return value


def _bind(arguments: Mapping[str, Any]) -> BindRequest | None:
    """Return a run's bind request, ``None`` when no bind field is given."""
    if all(arguments.get(name) is None for name in _BIND_FIELDS):
        return None
    return BindRequest(
        as_of=_day(arguments, "as_of"),
        vintage=_text(arguments, "vintage"),
        profile=_text(arguments, "profile") or DEFAULT_PROFILE,
        concepts=_mapping(arguments, "concepts"),
        parameters=_mapping(arguments, "parameters"),
    )


# --- answers -----------------------------------------------------------------------


def _blocks(*texts: str) -> list[types.ContentBlock]:
    return [types.TextContent(type="text", text=text) for text in texts]


def _document(body: bytes) -> types.CallToolResult:
    """Answer a canonical document: structured, and its text."""
    text = body.decode("utf-8")
    return types.CallToolResult(
        content=_blocks(text), structured_content=json.loads(text)
    )


def _failed(problem: Problem) -> types.CallToolResult:
    """Answer a tool error: the problem's JSON, and its one-line message."""
    return types.CallToolResult(
        content=_blocks(problem.to_json().decode("utf-8"), problem.cli_message),
        is_error=True,
    )


def _download(
    model: Model[Any, Any], inputs: bytes, bind: BindRequest | None
) -> str | None:
    """Return the REST API's GET form of a run, ``None`` if its inputs are too long."""
    encoded = base64.urlsafe_b64encode(inputs).decode("ascii").rstrip("=")
    if len(encoded) > GET_INPUTS_LIMIT:
        return None
    query: list[tuple[str, str]] = [("inputs", encoded)] if inputs != b"{}" else []
    if bind is not None:
        values = bind.to_dict()
        query += [
            (name, str(values[name]))
            for name in ("as_of", "vintage", "profile")
            if values[name] is not None
        ]
        query += [("concept", f"{k}={v}") for k, v in sorted(bind.concepts.items())]
        query += [("param", f"{k}={v}") for k, v in sorted(bind.parameters.items())]
    path = f"/v1/models/{model.id}/run"
    return f"{path}?{urlencode(query)}" if query else path


# --- the server ----------------------------------------------------------------------


class _Tools:
    """The tools of one server, and what each call does."""

    def __init__(  # noqa: PLR0913 - the server's settings, one by one
        self,
        *,
        mode: McpMode,
        policy: LlmUsePolicy,
        executor: Executor,
        result_limit: int,
        series_limit: int,
        headline: Iterable[str],
    ) -> None:
        self.mode = mode
        self.policy = policy
        self.executor = executor
        self.result_limit = result_limit
        self.series_limit = series_limit
        self.specs = build_tools(hosted=mode == "hosted", headline=headline)
        self.by_name = {spec.name: spec for spec in self.specs}
        self.listed = [_tool(spec) for spec in self.specs]
        self.descriptions: dict[str, bytes] = {}

    def input_schema(self, name: str) -> dict[str, Any] | None:
        """Return a tool's input schema by name, ``None`` for an unknown tool."""
        spec = self.by_name.get(name)
        return None if spec is None else spec.input_schema

    async def call(
        self, name: str, arguments: Mapping[str, Any] | None
    ) -> types.CallToolResult:
        """Answer one tool call; every failure is a tool error with its problem."""
        spec = self.by_name.get(name)
        if spec is None:
            raise MCPError(code=types.INVALID_PARAMS, message=f"Unknown tool: {name}")
        try:
            return await self._dispatch(spec, arguments or {})
        except Refused as refused:
            return _failed(refused.problem)
        except Exception as error:  # noqa: BLE001 - every failure becomes a problem
            return _failed(report(error, logger=_LOG))

    async def _dispatch(
        self, spec: ToolSpec, arguments: Mapping[str, Any]
    ) -> types.CallToolResult:
        if spec.kind == "headline":
            model = registry.get(spec.model_id or "")
            return await self._run(model, dict(arguments), None)
        if spec.kind == "run":
            given = _arguments(arguments, ("model_id", "inputs", *_BIND_FIELDS))
            model_id = _text(given, "model_id", required=True) or ""
            from pyeconomics.core.registry import installed  # noqa: PLC0415

            model = installed().resolve(model_id, stacklevel=2)
            return await self._run(model, _mapping(given, "inputs"), _bind(given))
        if spec.kind == "series":
            return await self._series(
                _arguments(arguments, ("target", *_SERIES_OPTIONS))
            )
        if spec.kind == "search":
            return self._search(_arguments(arguments, ("query", "domain", "limit")))
        if spec.kind == "describe":
            given = _arguments(arguments, ("model_id",))
            return await self._describe(_text(given, "model_id", required=True) or "")
        _arguments(arguments, ())
        return await self._sources()

    async def _run(
        self,
        model: Model[Any, Any],
        inputs: Mapping[str, Any],
        bind: BindRequest | None,
    ) -> types.CallToolResult:
        decoded = codec.decode(dict(inputs), model)
        body = await self.executor.run(model, decoded, bind, self.policy)
        document = json.loads(body)
        gate.check_document(document, self.policy, subject=model.id)
        summary = summary_of(document, model.spec.title)
        if self.mode != "hosted" or len(body) <= self.result_limit:
            # Plotly is imported, and the figure built, off the event loop.
            meta = await asyncio.to_thread(apps.figure_meta, model, document)
            return types.CallToolResult(
                content=_blocks(body.decode("utf-8"), summary),
                structured_content=document,
                meta=meta,
            )
        path = _download(model, canonical_json(decoded), bind)
        notice = {
            "download": None if path is None else {"method": "GET", "path": path},
            "model_id": document["model_id"],
            "model_version": document["model_version"],
            "result_bytes": len(body),
            "result_sha256": document["manifest"]["result_sha256"],
            "summary": summary,
        }
        where = (
            f"The whole result is at GET {path} on this server."
            if path is not None
            else f"The whole result answers POST /v1/models/{model.id}/run on this "
            "server, with the same inputs as the body."
        )
        text = (
            f"{summary} The result is {len(body)} bytes, above this server's "
            f"limit of {self.result_limit} for one answer. {where}"
        )
        return types.CallToolResult(
            content=_blocks(canonical_json(notice).decode("utf-8"), text),
            structured_content=notice,
        )

    async def _series(self, arguments: Mapping[str, Any]) -> types.CallToolResult:
        target = _text(arguments, "target", required=True) or ""
        options: dict[str, str] = {}
        for name in _SERIES_OPTIONS:
            value = (
                _day(arguments, name)
                if name in {"start", "end", "as_of"}
                else (_text(arguments, name))
            )
            if value is not None:
                options[name] = value
        body = await self.executor.series(
            target, options, self.series_limit, self.policy
        )
        document = json.loads(body)
        gate.check_document(document, self.policy, subject=target)
        return types.CallToolResult(
            content=_blocks(body.decode("utf-8"), _series_summary(target, document)),
            structured_content=document,
        )

    def _search(self, arguments: Mapping[str, Any]) -> types.CallToolResult:
        query = _text(arguments, "query")
        domain = _text(arguments, "domain")
        limit = arguments.get("limit", DEFAULT_SEARCH_LIMIT)
        if isinstance(limit, bool) or not isinstance(limit, int):
            msg = "limit is a whole number"
            raise InputError(msg)
        if query is None:
            entries = listing.list_models(domain)
        else:
            if domain is not None:
                listing.list_models(domain)  # refuses an unknown domain, listing them
            found = listing.search_models(query, listing.MAX_SEARCH_RESULTS)
            listing.search_models(query, limit)  # refuses a limit out of range
            entries = [e for e in found if domain is None or e["domain"] == domain]
            entries = entries[:limit]
        return _document(canonical_json({"models": entries}))

    async def _describe(self, model_id: str) -> types.CallToolResult:
        from pyeconomics.core.registry import installed  # noqa: PLC0415

        model = installed().resolve(model_id, stacklevel=2)
        body = self.descriptions.get(model.id)
        if body is None:
            # The card runs the first example: on a thread, off the event loop.
            body = canonical_json(await asyncio.to_thread(registry.describe, model.id))
            self.descriptions[model.id] = body
        return _document(body)

    async def _sources(self) -> types.CallToolResult:
        local = self.mode == "local"
        return _document(
            await asyncio.to_thread(_sources_document, self.policy, local=local)
        )


def _series_summary(target: str, document: Mapping[str, Any]) -> str:
    """Describe a series document in one line: its span and its sources."""
    frame = document.get("frame") or {}
    index = frame.get("index") or []
    span = f"{len(index)} observations" + (
        f", {index[0]} to {index[-1]}" if index else ""
    )
    providers = sorted(
        {str(record.get("provider")) for record in document.get("sources") or ()}
    )
    text = f"{document.get('concept') or target}: {span}."
    if providers:
        text += f" Data from {', '.join(providers)}."
    return text


def _sources_document(policy: LlmUsePolicy, *, local: bool) -> bytes:
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    entries = []
    for source in api.sources(check_keys=local):
        entry: dict[str, object] = {
            "attribution": source.attribution,
            "hosted_allowed": source.hosted_allowed,
            "id": source.id,
            "licence": source.licence.value,
            "llm_permitted": policy.permits(source.llm_use),
            "llm_use": source.llm_use.value,
            "name": source.name,
            "notice": source.notice,
            "terms_url": source.terms_url,
        }
        if local:
            entry["has_key"] = source.key_configured
        entries.append(entry)
    return canonical_json({"sources": entries})


def build_server(  # noqa: PLR0913 - the server's settings are independent
    *,
    mode: McpMode = "local",
    policy: LlmUsePolicy | None = None,
    executor: Executor | None = None,
    result_limit: int = DEFAULT_RESULT_LIMIT,
    series_limit: int = DEFAULT_SERIES_LIMIT,
    headline: Iterable[str] = HEADLINE,
) -> Server[Any]:
    """Build the MCP server of every installed model.

    Parameters
    ----------
    mode
        ``local`` (``pyeconomics mcp``) or ``hosted`` (the REST server's ``/mcp``
        mount in hosted mode): a hosted run larger than ``result_limit`` answers
        a notice, and ``list_sources`` says nothing about keys. The data layer's
        own mode is configured once, by whoever starts the server.
    policy
        The ``llm_use`` policy; ``None`` reads the user's configuration now
        (``allow_unclear_llm_use``), and nothing changes it afterwards.
    executor
        Where runs and series execute; this process's threads by default.
    result_limit
        The largest canonical result, in bytes, a hosted run returns whole.
    series_limit
        The most observations ``get_series`` returns per fetch.
    headline
        The ids of the models with a tool of their own.

    Raises
    ------
    InputError
        For a mode that is not one of the two, or a limit that is not a whole
        number from 1.
    RegistryError
        For a tool name that does not match ``^[a-z0-9_]{1,64}$``, two tools
        with one name, or a headline id that is an alias.
    """
    if mode not in {"local", "hosted"}:
        msg = f"mode is local or hosted, not {mode!r}"
        raise InputError(msg)
    for name, limit in (("result_limit", result_limit), ("series_limit", series_limit)):
        given: object = limit
        if isinstance(given, bool) or not isinstance(given, int) or given < 1:
            msg = f"{name} is a whole number from 1"
            raise InputError(msg)
    if policy is None:
        from pyeconomics.data.config import settings  # noqa: PLC0415

        policy = settings().llm_use_policy
    tools = _Tools(
        mode=mode,
        policy=LlmUsePolicy(policy),
        executor=executor or LocalExecutor(),
        result_limit=result_limit,
        series_limit=series_limit,
        headline=headline,
    )

    async def list_tools(
        _ctx: ServerRequestContext[Any], _params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools.listed)

    async def call_tool(
        _ctx: ServerRequestContext[Any], params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        return await tools.call(params.name, params.arguments)

    async def list_resources(
        _ctx: ServerRequestContext[Any], _params: types.PaginatedRequestParams | None
    ) -> types.ListResourcesResult:
        return types.ListResourcesResult(resources=[apps.chart_resource()])

    async def read_resource(
        _ctx: ServerRequestContext[Any], params: types.ReadResourceRequestParams
    ) -> types.ReadResourceResult:
        if params.uri != apps.CHART_URI:
            raise MCPError(
                code=types.INVALID_PARAMS, message=f"Unknown resource: {params.uri}"
            )
        return types.ReadResourceResult(contents=[apps.chart_contents()])

    hint = CacheHint(ttl_ms=_LIST_TTL_MS, scope="public")
    server: Server[Any] = Server(
        SERVER_NAME,
        version=__version__,
        title="pyeconomics",
        description=(
            "Open economics and finance models and data. Each model runs on the "
            "same path as the pyeconomics Python API and returns its canonical "
            "result, with the manifest of every source it read."
        ),
        website_url="https://pyeconomics.readthedocs.io",
        cache_hints={
            "tools/list": hint,
            "server/discover": hint,
            "resources/list": hint,
            "resources/read": hint,
        },
        get_tool_input_schema=tools.input_schema,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
        on_list_resources=list_resources,
        on_read_resource=read_resource,
    )
    return server
