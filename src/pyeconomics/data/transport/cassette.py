# src/pyeconomics/data/transport/cassette.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Cassettes: recorded responses that tests replay offline (ADR-0011 decision 17).

A cassette is one canonical-JSON file under
``tests/providers/cassettes/<provider>/`` holding what a deliberate local
recording (``scripts/record_cassettes.py``) saw: the provider, when it was
recorded, whether its values are synthetic, and each request with its
response. A request holds its method, its URL without a query, its sorted
parameters and its body; a response holds its status, the headers a client
reads, and the body as text (or base64 for bytes).

The recorder scrubs as it writes (:meth:`Cassette.from_exchanges`): no
parameter, body field or header named like a credential, no registered secret
anywhere, no cookie. A source that is not hosted-safe, or whose terms forbid
storage, is recorded with synthetic values and ``"synthetic": true``. A
cassette keeps at most :data:`MAX_OBSERVATIONS` observations per series and
:data:`MAX_CASSETTE_BYTES` bytes. :func:`scan_text` is the scan every cassette
must pass; it reports pattern names, never a matched value.

This module is pure: it reads no file and no clock. Replaying is
:class:`~pyeconomics.data.transport.replay.ReplayTransport`'s job.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data.transport.base import Request, Response
>>> when = dt.datetime(2026, 10, 15, 14, tzinfo=dt.UTC)
>>> request = Request(host="api.example.org", path="/v1/x", params=(("id", "A"),))
>>> cassette = Cassette.from_exchanges(
...     "demo", when, [(request, Response(200, b"{}", when))], synthetic=True
... )
>>> Cassette.from_json(cassette.canonical_json()) == cassette
True
>>> cassette.lookup(request).response.status
200
>>> scan_text("nothing to see")
[]

"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import redaction
from pyeconomics.data.errors import DataError
from pyeconomics.data.transport.base import (
    KEPT_HEADERS,
    MAX_PARAMETERS,
    Request,
    Response,
    request_key,
)

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable

__all__ = [
    "MAX_CASSETTE_BYTES",
    "MAX_OBSERVATIONS",
    "SECRET_PATTERNS",
    "Cassette",
    "RecordedRequest",
    "RecordedResponse",
    "scan_text",
    "synthetic_value",
]

#: The most observations per series a cassette keeps.
MAX_OBSERVATIONS: Final = 24
#: The largest cassette file, in bytes.
MAX_CASSETTE_BYTES: Final = 32 * 1024

_MAX_RECORDED_REQUESTS: Final = 256
_ENCODINGS: Final = ("utf-8", "base64")
_CASSETTE_KEYS: Final = ("provider", "recorded_on", "synthetic", "requests")
_REQUEST_KEYS: Final = ("method", "url", "parameters", "body", "response")
_RESPONSE_KEYS: Final = ("status", "headers", "body", "encoding")
_SCHEME: Final = "https://"

#: What the cassette scan looks for, by name. A project rule per key format the
#: sources issue, then widely known token formats (the kinds gitleaks' default
#: rules find), then a credential parameter carrying a value. The
#: ``fred-api-key`` pattern equals the one in ``.gitleaks.toml``; a test keeps
#: the two in step.
SECRET_PATTERNS: Final = {
    "fred-api-key": re.compile(
        r"(?i)fred[\w.-]{0,24}?(?:key|token)[^\n]{0,40}?(?:=|:|=>|,)"
        r"\s*['\"]?([a-z0-9]{32})\b"
    ),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_\w{50,})"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),
    "openai-style-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "json-web-token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    ),
    "bearer-credential": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "credential-assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|registrationkey|access[_-]?token|client[_-]?secret"
        r"|secret|password|authorization)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}"
    ),
    "credential-parameter": re.compile(
        r"(?i)[?&;](?:access_token|api_key|apikey|key|registrationkey|token|userid)="
        r"[^&;\s\"'<>]{6,}"
    ),
}


def scan_text(text: str) -> list[str]:
    """Return the names of the secret patterns a text matches.

    A name is reported once; the matched value is never returned, so a
    failing test cannot print a key.

    Examples
    --------
    >>> scan_text("GET /v1?series=GDP&limit=24")
    []
    >>> scan_text("see https://api.example.org/v1?api_key=abcdef0123")
    ['credential-parameter']

    """
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def synthetic_value(seed: str, index: int) -> float:
    """Return a deterministic stand-in for an observed value.

    A cassette of a source that is not hosted-safe, or that forbids storage,
    keeps the real structure and invents the numbers. The value depends only on
    the seed (a series id, say) and the position, lies in ``[0, 1]`` and has
    four decimals, so a recording is reproducible and no real value is kept.

    Examples
    --------
    >>> synthetic_value("GDPC1", 0) == synthetic_value("GDPC1", 0)
    True
    >>> 0.0 <= synthetic_value("GDPC1", 7) <= 1.0
    True

    """
    digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
    return round(int.from_bytes(digest[:4], "big") / 0xFFFFFFFF, 4)


@dataclass(frozen=True, slots=True)
class RecordedResponse:
    """The response a recording saw: status, kept headers and the decoded body."""

    status: int
    body: bytes
    headers: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the response as JSON-ready values, the body as text or base64."""
        try:
            text, encoding = self.body.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            text, encoding = base64.b64encode(self.body).decode("ascii"), "base64"
        return {
            "status": self.status,
            "headers": dict(sorted(self.headers)),
            "body": text,
            "encoding": encoding,
        }

    @classmethod
    def from_dict(cls, data: object) -> RecordedResponse:
        """Read a response back from :meth:`to_dict`'s form."""
        fields = f.mapping(data, "a recorded response", _RESPONSE_KEYS)
        status, text, encoding = fields["status"], fields["body"], fields["encoding"]
        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not 100 <= status <= 599  # noqa: PLR2004 - HTTP status codes
        ):
            msg = "a recorded status is an HTTP status code"
            raise f.fail(msg)
        if not isinstance(text, str) or encoding not in _ENCODINGS:
            msg = f"a recorded body is text with an encoding of {', '.join(_ENCODINGS)}"
            raise f.fail(msg)
        if encoding == "base64":
            try:
                body = base64.b64decode(text, validate=True)
            except ValueError as error:
                msg = "a recorded base64 body is not valid base64"
                raise f.fail(msg) from error
        else:
            body = text.encode("utf-8")
        headers = fields["headers"]
        if not isinstance(headers, dict) or not all(
            isinstance(name, str) and name in KEPT_HEADERS and isinstance(value, str)
            for name, value in headers.items()
        ):
            msg = f"recorded headers hold text values of {', '.join(KEPT_HEADERS)}"
            raise f.fail(msg)
        return cls(status, body, tuple(sorted(headers.items())))


@dataclass(frozen=True, slots=True)
class RecordedRequest:
    """A request a recording saw, scrubbed, with the response it got."""

    method: str
    url: str
    parameters: tuple[tuple[str, str], ...]
    body: Any
    response: RecordedResponse

    @property
    def request(self) -> Request:
        """The request as a :class:`~pyeconomics.data.transport.base.Request`."""
        host, _, path = self.url.removeprefix(_SCHEME).partition("/")
        return Request(
            host=host,
            path="/" + path,
            method=self.method,
            params=self.parameters,
            body=self.body,
        )

    @property
    def key(self) -> str:
        """The key replay matches on, as :func:`~.base.request_key` builds it."""
        return request_key(self.request)

    def to_dict(self) -> dict[str, object]:
        """Return the request as JSON-ready values."""
        return {
            "method": self.method,
            "url": self.url,
            "parameters": [list(pair) for pair in sorted(self.parameters)],
            "body": self.body,
            "response": self.response.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: object) -> RecordedRequest:
        """Read a request back from :meth:`to_dict`'s form."""
        fields = f.mapping(data, "a recorded request", _REQUEST_KEYS)
        url = fields["url"]
        if (
            not isinstance(url, str)
            or not url.startswith(_SCHEME)
            or any(mark in url for mark in "?# ")
        ):
            msg = "a recorded url is https with no query, fragment or space"
            raise f.fail(msg)
        pairs = f.sequence(fields["parameters"], "parameters", max_items=MAX_PARAMETERS)
        parameters: list[tuple[str, str]] = []
        for pair in pairs:
            if (
                not isinstance(pair, list)
                or len(pair) != 2  # noqa: PLR2004 - a (name, value) pair
                or not all(isinstance(part, str) for part in pair)
            ):
                msg = "recorded parameters are [name, value] pairs of text"
                raise f.fail(msg)
            parameters.append((pair[0], pair[1]))
        record = cls(
            f.text(fields["method"], "a recorded method", max_length=8),
            url,
            tuple(parameters),
            fields["body"],
            RecordedResponse.from_dict(fields["response"]),
        )
        _ = record.request  # building it validates the host, path and body
        return record


def _scrubbed_body(value: object) -> object:
    """Drop credential fields from a request body and scrub its text."""
    if isinstance(value, dict):
        return {
            name: _scrubbed_body(item)
            for name, item in value.items()
            if not redaction.is_credential_parameter(name)
        }
    if isinstance(value, list):
        return [_scrubbed_body(item) for item in value]
    if isinstance(value, str):
        return redaction.scrub_text(value)
    return value


def _scrubbed_response(response: Response) -> RecordedResponse:
    """Keep the status, the client's headers and a scrubbed body."""
    headers = redaction.scrub_headers(dict(response.headers))
    kept = tuple(
        sorted(
            (name.casefold(), value)
            for name, value in headers.items()
            if name.casefold() in KEPT_HEADERS
        )
    )
    try:
        text = response.body.decode("utf-8")
    except UnicodeDecodeError:
        # Binary: it cannot be scrubbed, so it must not hold a registered key.
        latin = response.body.decode("latin-1")
        if redaction.scrub_text(latin) != latin:
            msg = "a binary response holds a registered key and cannot be recorded"
            raise DataError(msg) from None
        return RecordedResponse(response.status, response.body, kept)
    return RecordedResponse(
        response.status, redaction.scrub_text(text).encode("utf-8"), kept
    )


@dataclass(frozen=True, slots=True)
class Cassette:
    """One recording of a provider: its scrubbed exchanges and how it was made."""

    provider: str
    recorded_on: dt.datetime
    synthetic: bool
    requests: tuple[RecordedRequest, ...]

    def __post_init__(self) -> None:
        """Check the provider id, the time and that each request is recorded once."""
        f.identifier(self.provider, "provider")
        object.__setattr__(
            self, "recorded_on", f.instant(self.recorded_on, "recorded_on")
        )
        f.flag(self.synthetic, "synthetic")
        keys = [record.key for record in self.requests]
        if len(set(keys)) != len(keys):
            msg = "a cassette records each request once"
            raise f.fail(msg)

    @classmethod
    def from_exchanges(
        cls,
        provider: str,
        recorded_on: dt.datetime,
        exchanges: Iterable[tuple[Request, Response]],
        *,
        synthetic: bool,
    ) -> Cassette:
        """Scrub what a recording saw and build the cassette.

        Every parameter, body field and header named like a credential is
        dropped, every registered secret is replaced, and cookies are never
        kept. A request seen twice is recorded once.
        """
        records: dict[str, RecordedRequest] = {}
        for request, response in exchanges:
            parameters = tuple(
                sorted(
                    (name, redaction.scrub_text(value))
                    for name, value in request.params
                    if not redaction.is_credential_parameter(name)
                )
            )
            record = RecordedRequest(
                request.method,
                f"{_SCHEME}{request.host}{request.path}",
                parameters,
                _scrubbed_body(request.body),
                _scrubbed_response(response),
            )
            records.setdefault(record.key, record)
        return cls(provider, recorded_on, synthetic, tuple(records.values()))

    def lookup(self, request: Request) -> RecordedRequest | None:
        """Return the recording of ``request``, or ``None`` when there is none."""
        wanted = request_key(request)
        return next((record for record in self.requests if record.key == wanted), None)

    def to_dict(self) -> dict[str, object]:
        """Return the cassette as JSON-ready values."""
        return {
            "provider": self.provider,
            "recorded_on": self.recorded_on.isoformat(),
            "synthetic": self.synthetic,
            "requests": [record.to_dict() for record in self.requests],
        }

    def canonical_json(self) -> bytes:
        """Return the cassette as canonical JSON (RFC 8785)."""
        return canonical_json(self.to_dict())

    def document(self) -> bytes:
        """Return the bytes a cassette file holds: canonical JSON and one LF.

        The final line feed is what the repository's ``end-of-file-fixer`` hook
        requires of every text file; :meth:`from_json` reads it back.
        """
        return self.canonical_json() + b"\n"

    @classmethod
    def from_dict(cls, data: object) -> Cassette:
        """Read a cassette back from :meth:`to_dict`'s form, refusing any other."""
        fields = f.mapping(data, "a cassette", _CASSETTE_KEYS)
        recorded_on = f.parse_instant(fields["recorded_on"], "recorded_on")
        if recorded_on is None:
            msg = "a cassette has a recorded_on time"
            raise f.fail(msg)
        items = f.sequence(
            fields["requests"], "requests", max_items=_MAX_RECORDED_REQUESTS
        )
        return cls(
            f.identifier(fields["provider"], "provider"),
            recorded_on,
            f.flag(fields["synthetic"], "synthetic"),
            tuple(RecordedRequest.from_dict(item) for item in items),
        )

    @classmethod
    def from_json(cls, document: str | bytes) -> Cassette:
        """Read a cassette back from its canonical JSON, strictly."""
        return cls.from_dict(f.load_json(document))
