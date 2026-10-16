# src/pyeconomics/data/transport/base.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The transport's vocabulary: a request, a response and the protocol (ADR-0011).

A provider describes what to ask for as :class:`Request` values and reads the
answers as :class:`Response` values. It never sends them: a :class:`Transport`
does, and it is the only code that opens a socket, reveals a key or builds a
URL (ADR-0011 decisions 10 and 13).

- A :class:`Request` names a host, a path, parameters and an optional JSON body.
  It holds no scheme, no port and no query string, and it refuses credentials:
  a parameter, body field or header named like one is rejected, because the
  transport attaches the key from the provider's authentication spec.
- A :class:`Response` holds the status, the few headers a client reads, the
  body bytes and when they were retrieved.

Nothing here does I/O.

Examples
--------
>>> request = Request(
...     host="api.example.org",
...     path=request_path("v1", "series", "GDP/REAL"),
...     params=(("limit", "24"),),
... )
>>> request.path
'/v1/series/GDP%2FREAL'
>>> request_key(request)
'GET api.example.org/v1/series/GDP%2FREAL?limit=24'

"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, Final, Protocol
from urllib.parse import quote, unquote

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.data.errors import ResponseError, TransportError
from pyeconomics.data.redaction import is_credential_header, is_credential_parameter

if TYPE_CHECKING:
    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo

__all__ = [
    "DEFAULT_MAX_RESPONSE_BYTES",
    "HOST_PATTERN",
    "HTTP_METHODS",
    "KEPT_HEADERS",
    "KEY_PLACEMENTS",
    "MAX_BODY_BYTES",
    "MAX_PARAMETERS",
    "MAX_REQUESTS_PER_OPERATION",
    "Request",
    "Response",
    "Transport",
    "check_host",
    "declared_hosts",
    "request_key",
    "request_path",
    "retry_after_seconds",
]

#: Where a request may ask for the key (``KeyPlacement``'s values).
KEY_PLACEMENTS: Final = ("query", "body", "header")
#: The methods a request may use.
HTTP_METHODS: Final = ("GET", "POST")
#: The most query parameters one request carries.
MAX_PARAMETERS: Final = 64
#: The most requests one operation (a fetch, a search ...) may build.
MAX_REQUESTS_PER_OPERATION: Final = 1_000
#: The largest request body, as canonical JSON, in bytes.
MAX_BODY_BYTES: Final = 1_048_576
#: The default cap on a response body, in bytes: 50 MiB.
DEFAULT_MAX_RESPONSE_BYTES: Final = 50 * 1024 * 1024
#: The response headers a :class:`Response` keeps, lower-case: those a client
#: reads. Cookies and everything else are dropped.
KEPT_HEADERS: Final = ("content-type", "etag", "last-modified", "link", "retry-after")

#: An exact DNS name of two or more labels whose last label starts with a letter,
#: so neither an IP address nor a bare name passes; no scheme, port or wildcard.
HOST_PATTERN: Final = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z](?:[a-z0-9-]*[a-z0-9])?"
)
_MAX_HOST_LENGTH: Final = 253
_MAX_DIGITS: Final = 9
_MAX_PATH_LENGTH: Final = 2_048
_MAX_VALUE_LENGTH: Final = 2_048
_PATH: Final = re.compile(r"(?:/[A-Za-z0-9._~!$&'()*+,;=:@%-]*)+")
_PERCENT: Final = re.compile(r"%(?![0-9A-Fa-f]{2})")
_NAME: Final = re.compile(r"[A-Za-z0-9_.$\[\]-]{1,64}")
_HEADER: Final = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,63}")
_CONTROL: Final = re.compile(r"[\x00-\x1f\x7f]")
# Headers the transport owns: a provider that set them could change the framing,
# the encoding or the identity of a request.
_TRANSPORT_HEADERS: Final = frozenset(
    {
        "accept-encoding",
        "connection",
        "content-length",
        "content-type",
        "host",
        "te",
        "transfer-encoding",
        "upgrade",
        "user-agent",
    }
)


def request_path(*segments: str) -> str:
    """Join path segments, percent-encoding each one whole.

    A segment holding ``/``, ``?``, ``#`` or any other character that could
    change the path's structure is encoded, so a series id taken from a query
    can never reach another endpoint of the host. An empty segment, ``.`` and
    ``..`` are refused.

    Raises
    ------
    InputError
        For an empty, ``.`` or ``..`` segment.

    Examples
    --------
    >>> request_path("v2", "data", "A.USA?x=1")
    '/v2/data/A.USA%3Fx%3D1'

    """
    for segment in segments:
        if segment in {"", ".", ".."}:
            msg = f"a path segment is not empty, '.' or '..', not {segment!r}"
            raise f.fail(msg)
    return "".join("/" + quote(segment, safe="") for segment in segments)


def _pairs(
    items: object, what: str, name: re.Pattern[str], *, headers: bool
) -> tuple[tuple[str, str], ...]:
    entries = f.sequence(items, what, max_items=MAX_PARAMETERS)
    checked: list[tuple[str, str]] = []
    for entry in entries:
        if (
            not isinstance(entry, tuple | list)
            or len(entry) != 2  # noqa: PLR2004 - a (name, value) pair
            or not all(isinstance(part, str) for part in entry)
        ):
            msg = f"{what} holds (name, value) pairs of text"
            raise f.fail(msg)
        key, value = entry
        if not name.fullmatch(key):
            msg = f"{what} holds a name that is not a plain token: {key!r}"
            raise f.fail(msg)
        if len(value) > _MAX_VALUE_LENGTH or _CONTROL.search(value):
            msg = f"the value of {key!r} is too long or holds a control character"
            raise f.fail(msg)
        credential = (
            is_credential_header(key) if headers else is_credential_parameter(key)
        )
        if credential:
            msg = (
                f"{what} names {key!r}, a credential: the transport attaches the "
                "key from the provider's authentication, never provider code"
            )
            raise f.fail(msg)
        if headers and key.casefold() in _TRANSPORT_HEADERS:
            msg = f"the transport sets the {key!r} header itself"
            raise f.fail(msg)
        checked.append((key, value))
    return tuple(checked)


def _body(body: object) -> object:
    """Return a deep copy of a JSON-ready body, checked for credentials and size."""
    if body is None:
        return None
    try:
        document = canonical_json(body)
    except (TypeError, ValueError, OverflowError) as error:
        msg = "a request body must be JSON-ready (dict, list, text, numbers, None)"
        raise f.fail(msg) from error
    if len(document) > MAX_BODY_BYTES:
        msg = f"a request body is at most {MAX_BODY_BYTES} bytes of canonical JSON"
        raise f.fail(msg)
    copy = f.load_json(document)
    pending = [copy]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            names = [name for name in item if is_credential_parameter(name)]
            if names:
                msg = (
                    f"a request body names {names[0]!r}, a credential: the transport "
                    "attaches the key, never provider code"
                )
                raise f.fail(msg)
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return copy


@dataclass(frozen=True, slots=True, kw_only=True)
class Request:
    """One request a provider asks the transport to send.

    Parameters
    ----------
    host
        An exact host name on the provider's allowlist, such as
        ``api.example.org``. No scheme, port or wildcard: every request is
        HTTPS.
    path
        The path, starting with ``/``; build it with :func:`request_path` so a
        series id cannot alter its structure.
    method
        ``"GET"`` or ``"POST"``.
    params
        Query parameters as ``(name, value)`` pairs. A name that is a credential
        (``api_key``, ``key``, ``UserID`` ...) is refused.
    body
        A JSON-ready body for a ``POST``; the transport sends it as JSON. A
        field named like a credential is refused.
    headers
        Extra non-credential headers, such as ``Accept``.
    series
        The series or table id the request concerns, so a 404 can name it.
    key_placement
        Where this request wants the key, ``"query"``, ``"body"`` or
        ``"header"``, among the placements the provider's authentication
        declares; ``None`` for its default. FRED's v2 asks for its header.
    """

    host: str
    path: str
    method: str = "GET"
    params: tuple[tuple[str, str], ...] = ()
    body: Any = None
    headers: tuple[tuple[str, str], ...] = ()
    series: str | None = None
    key_placement: str | None = None

    def __post_init__(self) -> None:
        """Check every field, normalizing the parameters and the body."""
        host: object = self.host
        if (
            not isinstance(host, str)
            or len(host) > _MAX_HOST_LENGTH
            or not HOST_PATTERN.fullmatch(host)
        ):
            msg = (
                "a request host is an exact lower-case DNS name such as "
                f"api.example.org, not {host!r}"
            )
            raise f.fail(msg)
        if self.method not in HTTP_METHODS:
            msg = f"a request method is one of {', '.join(HTTP_METHODS)}"
            raise f.fail(msg)
        _check_path(self.path)
        if self.method == "GET" and self.body is not None:
            msg = "a GET request has no body"
            raise f.fail(msg)
        object.__setattr__(
            self, "params", _pairs(self.params, "params", _NAME, headers=False)
        )
        object.__setattr__(
            self, "headers", _pairs(self.headers, "headers", _HEADER, headers=True)
        )
        object.__setattr__(self, "body", _body(self.body))
        f.optional_text(self.series, "series", max_length=128)
        if self.key_placement not in {None, *KEY_PLACEMENTS}:
            msg = f"a key placement is one of {', '.join(KEY_PLACEMENTS)}"
            raise f.fail(msg)


def _check_path(path: object) -> None:
    if (
        not isinstance(path, str)
        or len(path) > _MAX_PATH_LENGTH
        or not _PATH.fullmatch(path)
        or _PERCENT.search(path)
    ):
        msg = f"a request path is a plain absolute path, not {path!r}"
        raise f.fail(msg)
    segments = path.split("/")[1:]
    if "" in segments[:-1]:
        msg = "a request path has no empty segment"
        raise f.fail(msg)
    for segment in segments:
        decoded = unquote(segment)
        if decoded in {".", ".."} or "\\" in decoded or _CONTROL.search(decoded):
            msg = "a request path cannot climb or hold a backslash or control character"
            raise f.fail(msg)


def request_key(request: Request) -> str:
    """Name a request for replay: method, host, path, sorted parameters, body hash.

    The key holds no scheme and no credential (a request has none), so it is
    safe to print when a cassette is missing.
    """
    query = "&".join(
        f"{quote(name, safe='')}={quote(value, safe='')}"
        for name, value in sorted(request.params)
    )
    key = f"{request.method} {request.host}{request.path}"
    if query:
        key += f"?{query}"
    if request.body is not None:
        key += (
            " body-sha256:" + hashlib.sha256(canonical_json(request.body)).hexdigest()
        )
    return key


@dataclass(frozen=True, slots=True)
class Response:
    """What a source answered: the status, a few headers, the body, and when.

    Parameters
    ----------
    status
        The HTTP status.
    headers
        The headers a client reads (:data:`KEPT_HEADERS`), names lower-case.
    body
        The decoded body bytes, at most the provider's size cap.
    retrieved_at
        When the transport got it, in UTC; a replay carries the cassette's
        ``recorded_on``, so an offline run is deterministic.
    """

    status: int
    body: bytes
    retrieved_at: dt.datetime
    headers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Check the status, body and time; keep only :data:`KEPT_HEADERS`."""
        status: object = self.status
        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not 100 <= status <= 599  # noqa: PLR2004 - HTTP status codes
        ):
            msg = f"a response status is an HTTP status code, not {status!r}"
            raise f.fail(msg)
        body: object = self.body
        if not isinstance(body, bytes):
            msg = "a response body is bytes"
            raise f.fail(msg)
        object.__setattr__(
            self, "retrieved_at", f.instant(self.retrieved_at, "retrieved_at")
        )
        kept = tuple(
            (name.casefold(), value)
            for name, value in self.headers
            if name.casefold() in KEPT_HEADERS
        )
        object.__setattr__(self, "headers", kept)

    @property
    def ok(self) -> bool:
        """Whether the status is a success (2xx)."""
        return 200 <= self.status < 300  # noqa: PLR2004 - HTTP success range

    def header(self, name: str) -> str | None:
        """Return a kept header's value, or ``None``."""
        wanted = name.casefold()
        return next((value for key, value in self.headers if key == wanted), None)

    def text(self, *, provider: str | None = None) -> str:
        """Decode the body as UTF-8.

        Raises
        ------
        ResponseError
            If the body is not valid UTF-8.
        """
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            pass
        msg = "the response body is not UTF-8 text"
        raise ResponseError(msg, provider=provider)

    def json(self, *, provider: str | None = None) -> object:
        """Parse the body as strict JSON with the standard library.

        No NaN or infinity, no repeated key and no nesting deeper than
        canonical JSON allows (:func:`pyeconomics.core._fields.load_json`).

        Raises
        ------
        ResponseError
            If the body is not strict JSON. The message never repeats the body.
        """
        failure = ""
        try:
            return f.load_json(self.body)
        except InputError:
            failure = "the response body is not strict JSON"
        raise ResponseError(failure, provider=provider)


class Transport(Protocol):
    """Sends a provider's requests and returns the answers.

    The one implementation that opens a socket is
    :class:`~pyeconomics.data.transport.http.HttpTransport`;
    :class:`~pyeconomics.data.transport.replay.ReplayTransport` serves recorded
    responses offline. A transport refuses any host outside the provider's
    allowlist, attaches the provider's key, and returns a :class:`Response`
    for any HTTP status: retries have already happened, and
    :class:`~pyeconomics.data.providers.base.DataProvider` maps the final
    status to the error taxonomy.
    """

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Send one request on a provider's behalf and return its answer."""
        ...


def declared_hosts(info: ProviderInfo) -> tuple[str, ...]:
    """Return a provider's declared hosts, or none if they are not a tuple of text.

    ``ProviderInfo`` accepts what it is given, and a string would make ``in``
    match substrings, so the transports read the allowlist only through this.
    """
    hosts: object = info.hosts
    if isinstance(hosts, tuple) and all(isinstance(host, str) for host in hosts):
        return hosts
    return ()


def check_host(info: ProviderInfo, request: Request) -> None:
    """Refuse a request to a host outside the provider's allowlist.

    Every transport calls this before it sends or replays anything, so a
    provider (or an input a provider trusted) cannot point a request elsewhere:
    the server-side request forgery check of ADR-0011 decision 10.

    Raises
    ------
    TransportError
        If the provider declares hosts and the request's is not one of them, or
        the provider is session-based and declares none.
    """
    if request.host not in declared_hosts(info):
        msg = f"{info.id} may not contact {request.host}: it is not a declared host"
        raise TransportError(msg, provider=info.id)


def retry_after_seconds(value: str | None, now: dt.datetime) -> float | None:
    """Read a ``Retry-After`` header as seconds to wait, or ``None``.

    The header is whole seconds or an HTTP date; a date is measured from ``now``
    and never negative. Anything else reads as no advice.

    Examples
    --------
    >>> import datetime as dt
    >>> now = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)
    >>> retry_after_seconds("30", now)
    30.0
    >>> retry_after_seconds("Thu, 15 Oct 2026 12:01:00 GMT", now)
    60.0
    >>> retry_after_seconds("soon", now) is None
    True

    """
    if value is None:
        return None
    text = value.strip()
    if text.isascii() and text.isdecimal() and len(text) <= _MAX_DIGITS:
        return float(text)
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.UTC)
    return max(0.0, (when - now).total_seconds())
