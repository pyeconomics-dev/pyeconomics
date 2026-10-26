# src/pyeconomics/server/app.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The app factory: one ``/v1`` API generated from the registry (ADR-0012 9-11).

:func:`create_app` builds a FastAPI app for either mode. Its routes come from
the registry when it is built, so a model reaches the API with no code here:

- ``GET /v1/models`` (``?q=``, ``?domain=``, ``?limit=``): the listing entries
  (:mod:`~pyeconomics.surfaces.listing`);
- ``GET /v1/models/{model_id}``: ``registry.describe``'s canonical JSON;
- ``POST /v1/models/<id>/run`` for each model, with the model's own input and
  result schemas in the OpenAPI document, and its ``GET`` form, whose
  ``?inputs=`` is the inputs' JSON in base64url (at most 8,192 characters); both
  answer the same bytes. A run reads the raw body and hands it to
  :func:`~pyeconomics.surfaces.invoke.invoke` in the worker pool, so validation
  is the model's own, and answers ``Result.to_json()``'s bytes as they are;
- ``GET /v1/series/{target}``: ``data.get`` in the worker pool;
- ``GET /v1/sources``, ``GET /healthz`` and ``GET /version``;
- ``GET /openapi.json``, and in local mode only the interactive documentation
  (``/docs``, ``/redoc``), which loads its scripts from a CDN.

``?format=`` turns a run or a series into a download (:mod:`~pyeconomics.server.
formats`). A run with ``?as_of=``, ``?vintage=``, ``?profile=``, ``?concept=`` or
``?param=`` binds the model's data first, its body overriding what is bound. An
alias redirects (308) to its model's route. No route accepts a URL, a host or a
key, and none fetches what a caller names: a series target is a concept id or
``provider:series``, which the data layer resolves within its providers' hosts.

Every error is an RFC 9457 problem from the error table
(:mod:`~pyeconomics.surfaces.problems`), as ``application/problem+json``:
FastAPI's validation, an unknown route or method, an exception in a worker, and
anything unexpected, which answers 500 with fixed text. Each problem is logged
as one scrubbed record, and each request as one line naming its route's template
(:mod:`~pyeconomics.server.logs`). A local server answers only requests
addressed to a loopback name unless ``allow_remote`` is set, which keeps a web
page that rebinds its domain to 127.0.0.1 from reading the answers.

Hosted mode adds what a public service needs (ADR-0012 decisions 10-12 and 20),
in the outermost layer, before a route runs: the edge's credential when one is
configured (:mod:`~pyeconomics.server.edge`), and each client's rate limits
(:mod:`~pyeconomics.server.limits`). In either mode a run's ``GET`` form is
cached in memory and answered with an entity tag, ``304`` for a matching
``If-None-Match`` and ``Cache-Control`` (:mod:`~pyeconomics.server.run_cache`);
a ``POST`` run and every problem are ``no-store``.

With the ``mcp`` extra installed, the app also mounts the MCP server
(:func:`pyeconomics.mcp.build_server`) at ``/mcp`` as stateless Streamable HTTP,
in either mode, behind the same host check, edge check and rate limits: each tool
call that runs a model or reads a series goes to the same worker pool, with the
same budgets, as ``/v1``, carrying the server's ``llm_use`` policy, and its
answer is never put in the GET run cache.

Examples
--------
>>> app = create_app(settings=ServerSettings(workers=0))
>>> [route.path for route in app.routes if route.path.startswith("/v1/series")]
['/v1/series/{target:path}']
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import importlib.util
import logging
import math
import re
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Match, Route

from pyeconomics import __version__, registry
from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError, PyeconomicsError
from pyeconomics.core.spec import CostClass
from pyeconomics.server import formats, logs, openapi
from pyeconomics.server.edge import Edge, client_key
from pyeconomics.server.limits import MCP_PATH, Limiter, route_kind
from pyeconomics.server.pool import Pool, make_pool
from pyeconomics.server.run_cache import (
    NO_STORE,
    Entry,
    RunCache,
    etag_matches,
    run_key,
)
from pyeconomics.server.settings import (
    MODES,
    ServerMode,
    ServerSettings,
    budgets_for,
    data_mode,
    git_sha,
    limits_for,
    worker_count,
)
from pyeconomics.server.work import SERIES_OPTIONS, Outcome, Task
from pyeconomics.surfaces import codec, listing
from pyeconomics.surfaces.budgets import (
    GET_INPUTS_LIMIT,
    HOSTED_BODY_LIMIT,
    local_command,
)
from pyeconomics.surfaces.invoke import BindRequest
from pyeconomics.surfaces.problems import Problem, record, report
from pyeconomics.surfaces.service import (
    HostNotAllowedError,
    MethodNotAllowedError,
    RouteNotFoundError,
    host_name,
    is_loopback,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterable, Mapping, Sequence

    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from pyeconomics.core.model import Model
    from pyeconomics.core.provenance import LlmUsePolicy
    from pyeconomics.mcp.transport import HttpEndpoint
    from pyeconomics.surfaces.invoke import BindRequest as Bind

__all__ = ["create_app", "problem_response"]

_LOGGER: Final = logging.getLogger(logs.LOGGER)
_ACCESS: Final = logging.getLogger(logs.ACCESS_LOGGER)
_JSON: Final = "application/json"
_BASE64URL: Final = re.compile(r"[A-Za-z0-9_-]*")
#: A run's query parameters; the GET form adds ``inputs``.
_RUN_QUERY: Final = frozenset(
    {"format", "as_of", "vintage", "profile", "concept", "param"}
)
_REPEATED: Final = frozenset({"concept", "param"})
_SEARCH_LIMIT: Final = 20
#: The Retry-After of a problem that knows no wait of its own, in seconds.
_RETRY: Final = {"server-busy": "1", "limits-unavailable": "5"}


def problem_response(problem: Problem) -> Response:
    """Return a problem as an ``application/problem+json`` response.

    It is never cached (``Cache-Control: no-store``). A rate limit that knows
    how long to wait, the client's own or an upstream source's, a busy server
    and an unreachable limiter add ``Retry-After``.
    """
    headers = {"Cache-Control": NO_STORE}
    if problem.retry_after is not None:
        headers["Retry-After"] = str(math.ceil(problem.retry_after))
    elif problem.slug in _RETRY:
        headers["Retry-After"] = _RETRY[problem.slug]
    return Response(
        problem.to_json(),
        status_code=problem.status,
        media_type=openapi.PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


# --- what the routes share --------------------------------------------------------


class _Service:
    """A server's mode, settings, pool, edge, limits and caches."""

    def __init__(self, mode: ServerMode, settings: ServerSettings) -> None:
        self.mode = mode
        self.settings = settings
        self.workers = worker_count(settings)
        self.budgets = budgets_for(mode, settings)
        self.git_sha = git_sha(settings)
        self.pool: Pool | None = None
        self.documents: dict[str, bytes] = {}
        hosted = mode == "hosted"
        # Only the hosted service sits behind an edge; local mode checks Host.
        self.edge = Edge.from_environment() if hosted else Edge(None)
        self.limiter = Limiter.for_mode(limits_for(mode, settings), hosted=hosted)
        self.cache = RunCache(
            max_entries=settings.cache_entries, max_bytes=settings.cache_bytes
        )
        self.body_limit = HOSTED_BODY_LIMIT if hosted else codec.MAX_INPUT_BYTES

    def start(self) -> None:
        """Configure the data layer once, then start the worker pool."""
        from pyeconomics import data  # noqa: PLC0415 - the data layer loads here

        chosen = data_mode(self.mode)
        data.configure(mode=chosen, offline=self.settings.offline)
        self.pool = make_pool(
            workers=self.workers,
            queue_limit=self.settings.queue_limit,
            config={"mode": chosen, "offline": self.settings.offline},
            setup=self.settings.worker_setup,
        )
        self.pool.start()

    def close(self) -> None:
        """Stop the worker pool."""
        pool, self.pool = self.pool, None
        if pool is not None:
            pool.close()

    def budget(self, cost: CostClass | None) -> float | None:
        """Return the budget of a run of this cost class; ``None`` for none."""
        if self.budgets is None:
            return None
        return self.budgets.get(cost or CostClass.HEAVY)

    async def outcome(self, task: Task) -> Outcome:
        """Run a task in the pool, logging the problem it became, if any."""
        if self.pool is None:
            msg = "the server's worker pool is not running"
            raise RuntimeError(msg)
        outcome = await self.pool.submit(task)
        if outcome.problem is not None:
            record(outcome.problem, outcome.error_name, logger=_LOGGER)
        return outcome

    async def answer(self, task: Task, name: str) -> Response:
        """Run a task in the pool and answer its body, or its problem.

        A run answered this way (a ``POST`` run) is ``no-store``.
        """
        outcome = await self.outcome(task)
        if outcome.problem is not None:
            return problem_response(outcome.problem)
        headers: dict[str, str] = {}
        disposition = formats.disposition(task.export_format, name)
        if disposition is not None:
            headers["Content-Disposition"] = disposition
        if task.kind == "run":
            headers["Cache-Control"] = NO_STORE
        return Response(
            outcome.body,
            media_type=formats.MEDIA_TYPES[task.export_format],
            headers=headers,
        )

    async def answer_cached(
        self, task: Task, model: Model[Any, Any], if_none_match: str | None
    ) -> Response:
        """Answer a ``GET`` run from the cache, or run it and keep what may be kept."""
        key = _cache_key(task, model)
        entry = None if key is None else self.cache.get(key)
        if entry is not None:
            return self._cached_response(entry, if_none_match, hit=True)
        outcome = await self.outcome(task)
        if outcome.problem is not None:
            return problem_response(outcome.problem)
        entry = Entry(
            body=outcome.body,
            media_type=formats.MEDIA_TYPES[task.export_format],
            disposition=formats.disposition(task.export_format, model.id),
            etag=outcome.etag,
            control=outcome.control or NO_STORE,
            stored=self.cache.now(),
        )
        if key is not None and entry.etag and entry.control != NO_STORE:
            self.cache.put(key, entry)
        return self._cached_response(entry, if_none_match, hit=False)

    def _cached_response(
        self, entry: Entry, if_none_match: str | None, *, hit: bool
    ) -> Response:
        headers = {"Cache-Control": entry.control}
        if entry.etag:
            headers["ETag"] = entry.etag
        if hit:
            headers["Age"] = str(self.cache.age(entry))
        if entry.etag and etag_matches(if_none_match, entry.etag):
            return Response(status_code=304, headers=headers)
        if entry.disposition is not None:
            headers["Content-Disposition"] = entry.disposition
        return Response(entry.body, media_type=entry.media_type, headers=headers)


def _cache_key(task: Task, model: Model[Any, Any]) -> str | None:
    """Return a ``GET`` run's cache key; ``None`` for inputs that do not decode."""
    try:
        inputs = codec.decode(task.payload, limit=codec.MAX_INPUT_BYTES)
    except InputError:
        return None  # the run answers the problem, which is never cached
    return run_key(model.id, model.version, inputs, task.bind, task.export_format)


class _Query:
    """A request's query parameters, refused when unknown or repeated."""

    def __init__(
        self,
        request: Request,
        allowed: Iterable[str],
        repeated: frozenset[str] = frozenset(),
    ) -> None:
        names = frozenset(allowed)
        self.single: dict[str, str] = {}
        self.many: dict[str, list[str]] = {}
        for key, value in request.query_params.multi_items():
            if key not in names:
                takes = ", ".join(sorted(names)) or "none"
                msg = f"this route takes no query parameter {key!r} (it takes: {takes})"
                raise InputError(msg)
            if key in repeated:
                self.many.setdefault(key, []).append(value)
            elif key in self.single:
                msg = f"the query names {key} more than once"
                raise InputError(msg)
            else:
                self.single[key] = value

    def one(self, name: str) -> str | None:
        """Return a parameter's value, ``None`` when absent."""
        return self.single.get(name)

    def all(self, name: str) -> list[str]:
        """Return every value of a repeatable parameter."""
        return self.many.get(name, [])


def _assignments(items: Sequence[str], name: str, what: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key:
            msg = f"{name} takes {what}"
            raise InputError(msg)
        if key in found:
            msg = f"{name} names {key} twice"
            raise InputError(msg)
        found[key] = value
    return found


def _bind(query: _Query) -> dict[str, object] | None:
    """Return a run's bind request as plain values, ``None`` when none is asked."""
    singles = ("as_of", "vintage", "profile")
    if all(query.one(name) is None for name in singles) and not (
        query.all("concept") or query.all("param")
    ):
        return None
    request = BindRequest(
        as_of=query.one("as_of"),
        vintage=query.one("vintage"),
        profile=query.one("profile") or DEFAULT_PROFILE,
        concepts=_assignments(query.all("concept"), "concept", "FIELD=ID"),
        parameters=_assignments(query.all("param"), "param", "NAME=VALUE"),
    )
    return request.to_dict()


def _get_inputs(text: str | None) -> bytes | None:
    """Return the GET form's inputs: ``?inputs=``'s base64url text, decoded."""
    if not text:
        return None
    if len(text) > GET_INPUTS_LIMIT:
        raise codec.InputTooLargeError(
            len(text), GET_INPUTS_LIMIT, advice="POST larger inputs as the body"
        )
    if not _BASE64URL.fullmatch(text) or len(text) % 4 == 1:
        msg = (
            "inputs is the inputs' JSON in base64url without padding "
            "(RFC 4648 section 5)"
        )
        raise InputError(msg)
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _too_large(service: _Service, model: Model[Any, Any]) -> str:
    """Say what to do with inputs above the body limit: the local command."""
    if service.mode == "hosted":
        return f"run large inputs locally: {local_command(model.id)}"
    return "pass larger inputs to the Python API"


async def _body(
    request: Request, service: _Service, model: Model[Any, Any]
) -> bytes | None:
    """Read the body up to the mode's limit, refusing it before going past."""
    limit = service.body_limit
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise codec.InputTooLargeError(
            int(declared), limit, advice=_too_large(service, model)
        )
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise codec.InputTooLargeError(
                size, limit, advice=_too_large(service, model)
            )
        chunks.append(chunk)
    return b"".join(chunks) or None


def _aliases() -> Mapping[str, str]:
    from pyeconomics.core.registry import installed  # noqa: PLC0415

    return installed().aliases()


def _whole(text: str | None, name: str, default: int) -> int:
    if text is None:
        return default
    if not text.isdigit():
        msg = f"{name} is a whole number"
        raise InputError(msg)
    return int(text)


def _json(body: bytes) -> Response:
    return Response(body, media_type=_JSON)


# --- the routes -------------------------------------------------------------------


async def _run(
    request: Request, service: _Service, model: Model[Any, Any], method: str
) -> Response:
    allowed = _RUN_QUERY if method == "POST" else _RUN_QUERY | {"inputs"}
    query = _Query(request, allowed, _REPEATED)
    export_format = formats.choose(query.one("format"), formats.RUN_FORMATS)
    bind = _bind(query)
    if method == "POST":
        payload = await _body(request, service, model)
    else:
        payload = _get_inputs(query.one("inputs"))
    task = Task(
        kind="run",
        target=model.id,
        export_format=export_format,
        bind=bind,
        payload=payload,
        budget=service.budget(model.spec.cost),
    )
    if method == "POST":
        return await service.answer(task, model.id)
    return await service.answer_cached(
        task, model, request.headers.get("if-none-match")
    )


def _add_runs(app: FastAPI, service: _Service, model: Model[Any, Any]) -> None:
    """Add a model's run routes: POST, and the GET form."""

    async def post(request: Request) -> Response:
        return await _run(request, service, model, "POST")

    async def get(request: Request) -> Response:
        return await _run(request, service, model, "GET")

    spec = model.spec
    path = f"/v1/models/{model.id}/run"
    for method, endpoint, summary in (
        ("POST", post, f"Run {spec.title}"),
        ("GET", get, f"Run {spec.title} (GET form)"),
    ):
        app.add_api_route(
            path,
            endpoint,
            methods=[method],
            name=f"run:{model.id}:{method}",
            operation_id=openapi.operation_id(model, method),
            summary=summary,
            description=f"{spec.summary}\n\nIts card: GET /v1/models/{model.id}",
            tags=[spec.domain],
            response_class=Response,
            openapi_extra=openapi.run_operation(model, method),
        )


def _service(request: Request) -> _Service:
    service: _Service = request.app.state.service
    return service


async def _list_models(request: Request) -> Response:
    query = _Query(request, {"q", "domain", "limit"})
    domain, text = query.one("domain"), query.one("q")
    if text is None:
        if query.one("limit") is not None:
            msg = "limit applies to a search: add q"
            raise InputError(msg)
        return _json(canonical_json(listing.list_models(domain)))
    limit = _whole(query.one("limit"), "limit", _SEARCH_LIMIT)
    if domain is None:
        return _json(canonical_json(listing.search_models(text, limit)))
    listing.list_models(domain)  # refuses an unknown domain, listing them
    listing.search_models(text, limit)  # refuses a limit out of range
    found = listing.search_models(text, listing.MAX_SEARCH_RESULTS)
    entries = [entry for entry in found if entry["domain"] == domain][:limit]
    return _json(canonical_json(entries))


async def _describe_model(request: Request) -> Response:
    _Query(request, ())
    typed = request.path_params["model_id"]
    canonical = _aliases().get(typed)
    if canonical is not None:
        return RedirectResponse(f"/v1/models/{canonical}", status_code=308)
    documents = _service(request).documents
    body = documents.get(f"model:{typed}")
    if body is None:
        # The card runs the first example: in a thread, off the event loop.
        body = canonical_json(await asyncio.to_thread(registry.describe, typed))
        documents[f"model:{typed}"] = body
    return _json(body)


async def _run_unknown(request: Request) -> Response:
    typed = request.path_params["model_id"]
    canonical = _aliases().get(typed)
    if canonical is None:
        model = registry.get(typed)  # raises ModelNotFoundError, naming matches
        method = "POST" if request.method == "POST" else "GET"
        return await _run(request, _service(request), model, method)
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/v1/models/{canonical}/run{query}", status_code=308)


async def _series(request: Request) -> Response:
    query = _Query(request, (*SERIES_OPTIONS, "format"))
    export_format = formats.choose(query.one("format"), formats.SERIES_FORMATS)
    target = request.path_params["target"]
    options = {
        name: value for name in SERIES_OPTIONS if (value := query.one(name)) is not None
    }
    service = _service(request)
    task = Task(
        kind="series",
        target=target,
        export_format=export_format,
        query=options,
        budget=service.budget(CostClass.HEAVY),
    )
    return await service.answer(task, target)


async def _sources_route(request: Request) -> Response:
    _Query(request, ())
    documents = _service(request).documents
    body = documents.get("sources")
    if body is None:
        body = await asyncio.to_thread(_sources)
        documents["sources"] = body
    return _json(body)


async def _healthz(request: Request) -> Response:
    _Query(request, ())
    return _json(canonical_json({"status": "ok"}))


async def _version(request: Request) -> Response:
    _Query(request, ())
    service = _service(request)
    return _json(
        canonical_json(
            {
                "git_sha": service.git_sha,
                "mode": service.mode,
                "pyeconomics": __version__,
            }
        )
    )


async def _openapi_json(request: Request) -> Response:
    _Query(request, ())
    return _json(canonical_json(request.app.openapi()))


def _add_generic(app: FastAPI) -> None:
    """Add the routes every installation has, whatever its models."""
    documented = (
        (
            "/v1/models",
            _list_models,
            "list_models",
            "List or search the models",
            "models",
            openapi.list_operation(registry.domains()),
        ),
        (
            "/v1/models/{model_id}",
            _describe_model,
            "describe_model",
            "Describe a model",
            "models",
            openapi.describe_operation(),
        ),
        (
            "/v1/series/{target:path}",
            _series,
            "get_series",
            "Get a series",
            "data",
            openapi.series_operation(),
        ),
        (
            "/v1/sources",
            _sources_route,
            "list_sources",
            "List the data providers",
            "data",
            openapi.sources_operation(),
        ),
        (
            "/healthz",
            _healthz,
            "healthz",
            "Health",
            "service",
            openapi.service_operation("Health"),
        ),
        (
            "/version",
            _version,
            "version",
            "Version",
            "service",
            openapi.service_operation("Version"),
        ),
    )
    for path, endpoint, operation_id, summary, tag, extra in documented:
        app.add_api_route(
            path,
            endpoint,
            methods=["GET"],
            name=operation_id,
            operation_id=operation_id,
            summary=summary,
            tags=[tag],
            response_class=Response,
            openapi_extra=extra,
        )
    for path, endpoint, methods, name in (
        ("/v1/models/{model_id}/run", _run_unknown, ["GET", "POST"], "run:unknown"),
        ("/openapi.json", _openapi_json, ["GET"], "openapi"),
    ):
        app.add_api_route(
            path,
            endpoint,
            methods=methods,
            name=name,
            response_class=Response,
            include_in_schema=False,
        )


def _sources() -> bytes:
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here
    from pyeconomics.surfaces.documents import jsonable  # noqa: PLC0415

    # Keys are not looked up: no route says whether a key exists.
    return canonical_json(jsonable(api.sources(check_keys=False)))


def _add_docs(app: FastAPI) -> None:
    """Add the interactive documentation, which loads its scripts from a CDN."""

    async def docs(request: Request) -> HTMLResponse:
        _Query(request, ())
        return get_swagger_ui_html(openapi_url="/openapi.json", title="pyeconomics")

    async def redoc(request: Request) -> HTMLResponse:
        _Query(request, ())
        return get_redoc_html(openapi_url="/openapi.json", title="pyeconomics")

    for path, endpoint in (("/docs", docs), ("/redoc", redoc)):
        app.add_api_route(
            path,
            endpoint,
            methods=["GET"],
            name=path.strip("/"),
            response_class=HTMLResponse,
            include_in_schema=False,
        )


# --- errors and the guard -----------------------------------------------------------


async def _pyeconomics_error(_request: Request, error: Exception) -> Response:
    return problem_response(report(error, logger=_LOGGER))


def _allowed(request: Request) -> list[str]:
    """Return the methods of every route whose path matches the request's."""
    path = request.scope["path"]
    methods: set[str] = set()
    for route in request.app.router.routes:
        if isinstance(route, Route) and route.path_regex.match(path) and route.methods:
            methods |= route.methods
    return sorted(methods)


async def _http_error(request: Request, error: Exception) -> Response:
    status = getattr(error, "status_code", 500)
    mapped: BaseException = error
    if status == 404:  # noqa: PLR2004 - Starlette's unmatched route
        mapped = RouteNotFoundError()
    elif status == 405:  # noqa: PLR2004 - Starlette's unmatched method
        mapped = MethodNotAllowedError(_allowed(request))
    response = problem_response(report(mapped, logger=_LOGGER))
    if isinstance(mapped, MethodNotAllowedError):
        response.headers["Allow"] = ", ".join(mapped.allowed)
    return response


async def _validation_error(_request: Request, error: Exception) -> Response:
    """Turn FastAPI's own validation error into the invalid-input problem."""
    items: list[Any] = (
        list(error.errors()) if isinstance(error, RequestValidationError) else []
    )
    shown = "; ".join(
        f"{'.'.join(str(part) for part in item.get('loc', ())) or 'request'}: "
        f"{item.get('msg', 'invalid')}"
        for item in items[:3]
    )
    mapped = InputError(f"the request is not valid: {shown or 'unreadable'}")
    return problem_response(report(mapped, logger=_LOGGER))


class _Guard:
    """The outermost layer: host, edge and limits, one access line, a last resort.

    Before a route runs, a local server checks the ``Host`` header, a hosted one
    with an edge credential checks it (which also decides the client address),
    and a server with limits counts the request against its client's. An
    exception that reaches it (anything not a ``PyeconomicsError``) answers the
    ``internal-error`` problem with fixed text and is not raised further, so no
    server logs its traceback.
    """

    def __init__(self, app: ASGIApp, *, check_host: bool, service: _Service) -> None:
        self.app = app
        self.check_host = check_host
        self.service = service

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500
        sent = False

        async def tracked(message: Message) -> None:
            nonlocal status, sent
            if message["type"] == "http.response.start":
                sent = True
                status = message["status"]
            await send(message)

        try:
            if self.check_host and not is_loopback(
                host_name(Headers(scope=scope).get("host", ""))
            ):
                raise HostNotAllowedError  # noqa: TRY301 - answered just below
            client = self.service.edge.check(scope)
            limiter = self.service.limiter
            if limiter is not None:
                kind = route_kind(scope["path"], Headers(scope=scope))
                await limiter.check(kind, client_key(client))
            await self.app(scope, receive, tracked)
        except Exception as error:  # noqa: BLE001 - every failure becomes a problem
            if not sent:
                response = problem_response(report(error, logger=_LOGGER))
                await response(scope, receive, tracked)
        finally:
            route = scope.get("route")
            template = getattr(route, "path_format", None) or "(no route)"
            _ACCESS.info(
                "%s %s %d %.0f ms",
                scope.get("method", ""),
                template,
                status,
                (time.perf_counter() - started) * 1000,
            )


# --- the MCP mount ------------------------------------------------------------------


class _PoolExecutor:
    """Runs the MCP server's tasks in the app's worker pool, under its budgets."""

    def __init__(self, service: _Service) -> None:
        self.service = service

    async def run(
        self,
        model: Model[Any, Any],
        inputs: Mapping[str, Any],
        bind: Bind | None,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Run a model in the pool; a worker's problem is raised as ``Refused``."""
        task = Task(
            kind="run",
            target=model.id,
            payload=canonical_json(dict(inputs)),
            bind=None if bind is None else bind.to_dict(),
            budget=self.service.budget(model.spec.cost),
            llm_use=policy.value,
        )
        return self._body(await self.service.outcome(task))

    async def series(
        self,
        target: str,
        options: Mapping[str, str],
        limit: int,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Read a series in the pool; a worker's problem is raised as ``Refused``."""
        task = Task(
            kind="series",
            target=target,
            query=dict(options),
            budget=self.service.budget(CostClass.HEAVY),
            llm_use=policy.value,
            max_observations=limit,
        )
        return self._body(await self.service.outcome(task))

    @staticmethod
    def _body(outcome: Outcome) -> bytes:
        from pyeconomics.mcp.execution import Refused  # noqa: PLC0415

        if outcome.problem is not None:
            raise Refused(outcome.problem, outcome.error_name)
        return outcome.body


class _McpRoute(Route):
    """The MCP endpoint's route, which names itself in the scope as API routes do.

    The access line then names ``/mcp``, the route's template, as it names every
    other route's.
    """

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """Match as a route does, and record the route in the child scope."""
        match, child = super().matches(scope)
        if match is not Match.NONE:
            child["route"] = self
        return match, child


def _mcp_endpoint(service: _Service) -> HttpEndpoint | None:
    """Return the MCP endpoint over the app's pool, or ``None`` without the extra."""
    if importlib.util.find_spec("mcp") is None:
        return None
    from pyeconomics.mcp import server as mcp  # noqa: PLC0415 - the mcp extra
    from pyeconomics.mcp.transport import HttpEndpoint  # noqa: PLC0415

    settings = service.settings
    server = mcp.build_server(
        mode=service.mode,
        executor=_PoolExecutor(service),
        result_limit=settings.mcp_result_limit or mcp.DEFAULT_RESULT_LIMIT,
        series_limit=settings.mcp_series_limit or mcp.DEFAULT_SERIES_LIMIT,
    )
    return HttpEndpoint(server, mode=service.mode)


# --- the factory --------------------------------------------------------------------


def create_app(
    *, mode: ServerMode = "local", settings: ServerSettings | None = None
) -> FastAPI:
    """Build the REST API of every installed model.

    Parameters
    ----------
    mode
        ``local`` (the default; ``pyeconomics serve``) or ``hosted`` (the
        container): see :mod:`~pyeconomics.server.settings`.
    settings
        Workers, queue, budgets and hosts; the defaults otherwise.

    Raises
    ------
    InputError
        For a mode that is not one of the two.
    ConfigError
        If ``PYECONOMICS_WORKERS`` is not a whole number, or, in hosted mode,
        ``PYECONOMICS_EDGE_CREDENTIAL`` is too short or
        ``PYECONOMICS_RATELIMIT_URL`` is not a TLS Redis URL, or a setting the MCP
        server reads is invalid.
    """
    if mode not in MODES:
        msg = f"mode is one of {', '.join(MODES)}, not {mode!r}"
        raise InputError(msg)
    service = _Service(mode, settings or ServerSettings())
    models = registry.models()
    endpoint = _mcp_endpoint(service)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        service.start()
        try:
            mounted = endpoint.running() if endpoint else contextlib.nullcontext()
            async with mounted:
                yield
        finally:
            await asyncio.to_thread(service.close)

    app = FastAPI(
        title="pyeconomics",
        version=__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.service = service
    app.add_middleware(
        _Guard,
        check_host=mode == "local" and not service.settings.allow_remote,
        service=service,
    )
    app.add_exception_handler(PyeconomicsError, _pyeconomics_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    for model in models:
        _add_runs(app, service, model)
    _add_generic(app)
    if mode == "local":
        _add_docs(app)
    if endpoint is not None:
        app.router.routes.append(_McpRoute(MCP_PATH, endpoint=endpoint, name="mcp"))

    def build_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = openapi.document(app, models)
        return app.openapi_schema

    app.openapi = build_openapi  # type: ignore[method-assign] # ty: ignore[invalid-assignment]
    return app
