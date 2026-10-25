# src/pyeconomics/surfaces/problems.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The error table: every error to a problem, an HTTP status and an exit code.

ADR-0012 decision 4. :data:`ROWS` holds one :class:`Row` per error class, core's
(:mod:`pyeconomics.core.errors`), the data layer's
(:mod:`pyeconomics.data.errors`) and the surfaces' own: a slug, a title, an HTTP
status and a command-line exit code. A row names its class by module and name, so
this module imports neither error module, and an error takes the row of the
nearest class in its MRO that has one; an exception that is not a
:class:`~pyeconomics.core.errors.PyeconomicsError` takes ``internal-error``.

:func:`problem_for` turns an error into a :class:`Problem`, an RFC 9457 problem
whose ``type`` is ``https://pyeconomics.dev/problems/<slug>``. **A problem never
holds a key, a file path, a host or an upstream URL**:

- an exception that is not a ``PyeconomicsError`` gets a fixed detail, never its
  message, which may hold a path or a value;
- a ``TransportError``, ``ResponseError`` or ``RateLimitError`` gets a fixed
  detail naming the provider, because its message describes the upstream request;
- an ``InputError`` from validation gets its detail from the field errors, which
  :attr:`Problem.errors` lists without their input values;
- any other detail is the message passed through :func:`scrub`.

The only URLs a problem holds are its ``type`` and, for a licence refusal, the
source's terms page in ``terms``. :func:`report` logs a problem as one scrubbed
record, never a traceback; :func:`record` logs one already made.

Examples
--------
>>> from pyeconomics.core import InputError
>>> problem = problem_for(InputError("coupon_rate: 5 is above its bound 1"))
>>> problem.exit_code, problem.status, problem.type_uri
(3, 422, 'https://pyeconomics.dev/problems/invalid-input')
>>> problem_for(RuntimeError("C:/Users/someone/secret.txt")).detail
'An unexpected error stopped the request.'
"""

from __future__ import annotations

import logging
import math
import re
import sys
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError, PyeconomicsError

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "MAX_DETAIL_LENGTH",
    "MAX_FIELD_ERRORS",
    "ROWS",
    "TYPE_BASE",
    "FieldError",
    "Problem",
    "Row",
    "problem_for",
    "record",
    "report",
    "row_for",
    "scrub",
]

#: Every problem type URI is this followed by the slug.
TYPE_BASE: Final = "https://pyeconomics.dev/problems/"
#: The longest detail, in characters.
MAX_DETAIL_LENGTH: Final = 1_000
#: The most field errors a problem lists.
MAX_FIELD_ERRORS: Final = 100
#: How many field errors an invalid-input detail spells out.
_DETAIL_ERRORS: Final = 3
#: The first HTTP status of a server error, which logs at ERROR.
_SERVER_ERROR: Final = 500

_LOGGER: Final = logging.getLogger("pyeconomics.surfaces")

_CORE: Final = "pyeconomics.core.errors"
_DATA: Final = "pyeconomics.data.errors"
_SERVICE: Final = "pyeconomics.surfaces.service"


@dataclass(frozen=True, slots=True)
class Row:
    """One error class's slug, title, HTTP status and exit code."""

    error: str
    """The class, as ``<module>.<name>``."""
    slug: str
    title: str
    status: int
    exit_code: int

    @property
    def type_uri(self) -> str:
        """The problem type URI."""
        return TYPE_BASE + self.slug

    @property
    def error_name(self) -> str:
        """The class's own name."""
        return self.error.rpartition(".")[2]


#: The error table, most specific rows first (ADR-0012 decision 4).
ROWS: Final = (
    Row(f"{_CORE}.InputError", "invalid-input", "The inputs are not valid", 422, 3),
    Row(
        "pyeconomics.surfaces.codec.InputTooLargeError",
        "input-too-large",
        "The inputs are too large",
        413,
        3,
    ),
    Row(
        f"{_CORE}.DomainError",
        "no-defined-result",
        "The inputs have no defined result",
        422,
        4,
    ),
    Row(
        f"{_CORE}.ConvergenceError",
        "no-convergence",
        "The numerical method found no answer",
        422,
        4,
    ),
    Row(f"{_CORE}.ModelNotFoundError", "model-not-found", "No such model", 404, 5),
    Row(
        f"{_DATA}.ProviderNotFoundError",
        "provider-not-found",
        "No such data provider",
        404,
        5,
    ),
    Row(
        f"{_DATA}.ConceptNotFoundError",
        "concept-not-found",
        "No such catalog concept",
        404,
        5,
    ),
    Row(f"{_DATA}.SeriesNotFoundError", "series-not-found", "No such series", 404, 5),
    Row(
        f"{_DATA}.LicenceError",
        "licence-refused",
        "The source's licence does not permit this use",
        403,
        6,
    ),
    Row(
        f"{_DATA}.CredentialError",
        "credential-unavailable",
        "A credential the source needs is missing or refused",
        503,
        7,
    ),
    Row(
        f"{_DATA}.TransportError",
        "upstream-unavailable",
        "The data source could not be reached",
        502,
        7,
    ),
    Row(
        f"{_DATA}.ResponseError",
        "upstream-invalid-response",
        "The data source sent a response that could not be read",
        502,
        7,
    ),
    Row(
        f"{_DATA}.RateLimitError",
        "upstream-rate-limited",
        "The data source's rate limit was reached",
        503,
        7,
    ),
    Row(
        f"{_DATA}.OfflineError",
        "offline-cache-miss",
        "Offline mode has no cached copy",
        503,
        7,
    ),
    Row(
        f"{_DATA}.SourceDisabledError",
        "source-disabled",
        "The data source is disabled",
        503,
        7,
    ),
    Row(
        f"{_DATA}.DataError",
        "data-unavailable",
        "The data cannot answer this request",
        422,
        7,
    ),
    Row(
        f"{_CORE}.MissingOptionalDependencyError",
        "missing-extra",
        "An optional dependency is not installed",
        501,
        8,
    ),
    Row(
        "pyeconomics.surfaces.budgets.BudgetExceededError",
        "budget-exceeded",
        "The run exceeded its time budget",
        422,
        1,
    ),
    Row(
        f"{_SERVICE}.RouteNotFoundError",
        "route-not-found",
        "No such route",
        404,
        5,
    ),
    Row(
        f"{_SERVICE}.MethodNotAllowedError",
        "method-not-allowed",
        "The route does not take this method",
        405,
        1,
    ),
    Row(
        f"{_SERVICE}.HostNotAllowedError",
        "host-not-allowed",
        "This server does not answer for that host",
        400,
        1,
    ),
    Row(f"{_SERVICE}.ServerBusyError", "server-busy", "The server is busy", 503, 1),
    Row(
        f"{_SERVICE}.EdgeRefusedError",
        "edge-required",
        "The request did not come through the service's edge",
        403,
        1,
    ),
    Row(
        f"{_SERVICE}.TooManyRequestsError",
        "too-many-requests",
        "This client sent too many requests",
        429,
        1,
    ),
    Row(
        f"{_SERVICE}.LimitsUnavailableError",
        "limits-unavailable",
        "The rate limits cannot be checked",
        503,
        1,
    ),
    Row(
        f"{_CORE}.RegistryError",
        "registry-error",
        "The model registry is inconsistent",
        500,
        1,
    ),
    Row(
        f"{_DATA}.ConfigError",
        "invalid-configuration",
        "A setting is invalid",
        500,
        1,
    ),
    Row(
        f"{_CORE}.PyeconomicsError",
        "pyeconomics-error",
        "pyeconomics could not complete the request",
        500,
        1,
    ),
    Row("builtins.Exception", "internal-error", "Internal error", 500, 1),
)

_BY_CLASS: Final[Mapping[str, Row]] = {row.error: row for row in ROWS}
_INTERNAL: Final = ROWS[-1]
_FIXED_DETAIL: Final = "An unexpected error stopped the request."
#: Errors whose messages describe the upstream request: a fixed detail instead.
_UPSTREAM: Final = {
    f"{_DATA}.TransportError": "The request to {provider} failed; try again later.",
    f"{_DATA}.ResponseError": "{provider} sent a response pyeconomics could not read.",
    f"{_DATA}.RateLimitError": (
        "{provider}'s rate limit still held after the permitted retries."
    ),
}

#: pyeconomics' own documentation, the one kind of URL a detail keeps.
_OWN_HOSTS: Final = frozenset(
    {"pyeconomics.readthedocs.io", "pyeconomics.dev", "www.pyeconomics.dev"}
)
_URL: Final = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"<>]+")
_TRAILING: Final = ").,;:!?]}"
_HOST_FIELD: Final = re.compile(r"(?i)\bhost=(['\"]?)[^\s,'\")]+\1")
_PATH: Final = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s'\"<>|]*"  # C:\ or C:/
    r"|\\\\[^\s'\"<>|\\]+\\[^\s'\"<>|]*"  # \\server\share
    r"|(?<![\w.:/\\-])~?/[^\s'\"<>/][^\s'\"<>]*"  # /an/absolute or ~/a/home path
    r"|(?<![\w.])\.\.?[\\/][^\s'\"<>]+"  # ./a or ../a relative path
)


def _key(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def row_for(error: BaseException) -> Row:
    """Return the row of the nearest class in the error's MRO that has one."""
    for cls in type(error).__mro__:
        row = _BY_CLASS.get(_key(cls))
        if row is not None:
            return row
    return _INTERNAL


def _url(match: re.Match[str]) -> str:
    """Keep pyeconomics' own documentation URLs, without a query; drop the rest."""
    text = match.group()
    url = text.rstrip(_TRAILING)
    tail = text[len(url) :]
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return "<url>" + tail
    own = (
        parts.scheme == "https"
        and parts.hostname in _OWN_HOSTS
        and parts.username is None
        and port is None
    )
    if not own:
        return "<url>" + tail
    return f"https://{parts.hostname}{parts.path}{tail}"


def scrub(text: str) -> str:
    """Remove every key, URL, host and file path from a message.

    Every registered secret and credential parameter is replaced (through
    :mod:`pyeconomics.data.redaction`, when the data layer is loaded: a secret can
    be registered only there), every URL but pyeconomics' own documentation
    becomes ``<url>``, a ``host=`` fragment loses its host, and every file path
    becomes ``<path>``. Whitespace runs become one space, and the text is cut to
    :data:`MAX_DETAIL_LENGTH` characters.

    Examples
    --------
    >>> scrub("GET https://api.example.org/v1?id=1 from /home/someone/x.toml failed")
    'GET <url> from <path> failed'
    >>> scrub("see https://pyeconomics.readthedocs.io/en/main/data/keys.html?a=b.")
    'see https://pyeconomics.readthedocs.io/en/main/data/keys.html.'
    """
    redaction = sys.modules.get("pyeconomics.data.redaction")
    if redaction is not None:
        text = redaction.scrub_text(text)
    text = _URL.sub(_url, text)
    text = _HOST_FIELD.sub("host=<host>", text)
    text = _PATH.sub("<path>", text)
    text = " ".join(text.split())
    if len(text) > MAX_DETAIL_LENGTH:
        text = text[:MAX_DETAIL_LENGTH] + "..."
    return text


def _safe_str(error: BaseException) -> str:
    try:
        return str(error)
    except Exception:  # noqa: BLE001 - any error may fail to print
        return ""


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldError:
    """One field's validation error, without the value that failed."""

    location: tuple[str | int, ...]
    """Where: the field name, then any index or key inside it."""
    message: str
    error_type: str
    """Pydantic's error type, such as ``less_than_equal``."""

    def to_dict(self) -> dict[str, object]:
        """Return the error as JSON-ready values."""
        return {
            "loc": list(self.location),
            "msg": self.message,
            "type": self.error_type,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class Problem:
    """An RFC 9457 problem, with the command line's exit code.

    Attributes
    ----------
    slug, title, status, detail
        The problem's slug (its ``type`` is :data:`TYPE_BASE` plus the slug), its
        title, HTTP status and scrubbed detail.
    exit_code
        The command line's exit code.
    errors
        For invalid inputs, each field's error, without its value.
    licence, terms
        For a licence refusal, the source's licence class and terms page.
    retry_after
        For a rate limit, the seconds to wait: what an upstream source asked
        for, when it said, or when this client's own limit takes a request again.
    """

    slug: str
    title: str
    status: int
    detail: str
    exit_code: int
    errors: tuple[FieldError, ...] = ()
    licence: str | None = None
    terms: str | None = None
    retry_after: float | None = None

    @property
    def type_uri(self) -> str:
        """The problem type URI: ``https://pyeconomics.dev/problems/<slug>``."""
        return TYPE_BASE + self.slug

    @property
    def cli_message(self) -> str:
        """The line the command line prints on standard error."""
        return f"{self.slug}: {self.detail}"

    def to_dict(self) -> dict[str, object]:
        """Return the problem's RFC 9457 members and its extension members."""
        body: dict[str, object] = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.errors:
            body["errors"] = [error.to_dict() for error in self.errors]
        if self.licence is not None:
            body["licence"] = self.licence
        if self.terms is not None:
            body["terms"] = self.terms
        if self.retry_after is not None:
            body["retry_after"] = self.retry_after
        return body

    def to_json(self) -> bytes:
        """Return the problem as canonical JSON, for ``application/problem+json``."""
        return canonical_json(self.to_dict())


def _field_errors(error: InputError) -> tuple[FieldError, ...]:
    return tuple(
        FieldError(
            location=tuple(
                scrub(part) if isinstance(part, str) else part for part in item["loc"]
            ),
            message=scrub(item["msg"]),
            error_type=item["type"],
        )
        for item in error.errors[:MAX_FIELD_ERRORS]
    )


def _input_detail(errors: tuple[FieldError, ...], total: int) -> str:
    def where(location: tuple[str | int, ...]) -> str:
        return ".".join(str(part) for part in location) or "inputs"

    shown = "; ".join(
        f"{where(e.location)}: {e.message}" for e in errors[:_DETAIL_ERRORS]
    )
    more = total - min(total, _DETAIL_ERRORS)
    suffix = f"; and {more} more" if more else ""
    return scrub(f"The inputs failed validation: {shown}{suffix}.")


def _terms(error: BaseException) -> str | None:
    """Return a licence refusal's terms page, if it is a plain https page."""
    url = getattr(error, "terms_url", None)
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        plain = (
            parts.scheme == "https"
            and bool(parts.hostname)
            and parts.username is None
            and parts.port is None
            and not parts.query
            and not parts.fragment
        )
    except ValueError:
        plain = False
    return url if plain else None


def problem_for(error: BaseException) -> Problem:
    """Return the problem an error reaches every surface as.

    Parameters
    ----------
    error
        Any exception: a ``PyeconomicsError`` takes its class's row, anything else
        ``internal-error`` with a fixed detail.

    Returns
    -------
    Problem
        The slug, title, status, exit code and a detail that holds no key, file
        path, host or upstream URL.
    """
    row = row_for(error)
    if not isinstance(error, PyeconomicsError):
        return _problem(row, _FIXED_DETAIL)
    upstream = _UPSTREAM.get(row.error)
    if upstream is not None:
        provider = getattr(error, "provider", None) or "the data source"
        return replace(
            _problem(row, scrub(upstream.format(provider=provider))),
            retry_after=_seconds(getattr(error, "retry_after", None)),
        )
    if isinstance(error, InputError) and error.validation_error is not None:
        errors = _field_errors(error)
        detail = _input_detail(errors, len(error.errors))
        return replace(_problem(row, detail), errors=errors)
    message = _safe_str(error)
    terms = _terms(error)
    if terms is not None:
        message = message.replace(f" (terms: {terms})", "")
    licence = getattr(error, "licence", None)
    return replace(
        _problem(row, scrub(message) or row.title),
        licence=str(getattr(licence, "value", licence)) if licence else None,
        terms=terms,
        retry_after=_seconds(getattr(error, "retry_after", None)),
    )


def _seconds(value: object) -> float | None:
    """Return a wait in seconds, or ``None`` for anything but a finite number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    seconds = float(value)
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def _problem(row: Row, detail: str) -> Problem:
    return Problem(
        slug=row.slug,
        title=row.title,
        status=row.status,
        detail=detail,
        exit_code=row.exit_code,
    )


def record(
    problem: Problem, error_name: str, *, logger: logging.Logger | None = None
) -> None:
    """Log a problem as one record: its slug, status, error type name and detail.

    :func:`report` logs through this; a surface whose error was raised in another
    process (the REST API's workers) logs the problem it received the same way.
    A server error (5xx) logs at ``ERROR``, any other at ``INFO``, on
    ``pyeconomics.surfaces`` by default.
    """
    level = logging.ERROR if problem.status >= _SERVER_ERROR else logging.INFO
    (logger or _LOGGER).log(
        level,
        "%s (%d, %s): %s",
        problem.slug,
        problem.status,
        error_name,
        problem.detail,
    )


def report(error: BaseException, *, logger: logging.Logger | None = None) -> Problem:
    """Return an error's problem, after logging it as one scrubbed record.

    The record holds the slug, the status, the scrubbed detail and the error's
    type name: never a traceback or the raw message (:func:`record`).
    """
    problem = problem_for(error)
    record(problem, type(error).__qualname__, logger=logger)
    return problem
