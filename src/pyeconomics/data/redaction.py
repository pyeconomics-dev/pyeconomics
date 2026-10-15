# src/pyeconomics/data/redaction.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Redaction: keep every key out of logs, URLs, headers and exceptions.

ADR-0011 decision 13. A key is registered here the moment it becomes a
:class:`~pyeconomics.data.credentials.Secret`, and from then on every scrubber
replaces it, and its URL-encoded forms, with :data:`MASK`:

- :func:`install` chains a log-record factory in front of whatever factory is
  installed, so every record from every logger has its message formatted,
  scrubbed and its arguments cleared before any handler sees it. A traceback
  attached to a record is formatted and scrubbed too. The key chain installs
  it the first time it resolves a key.
- :func:`scrub_text` scrubs free text: every registered value, and the value
  of any credential query parameter (:data:`CREDENTIAL_PARAMETERS`).
- :func:`scrub_url` drops a URL's user information and its credential query
  parameters by name, then scrubs what is left.
- :func:`scrub_headers` drops the ``Authorization``, ``Cookie`` and key
  headers and scrubs the rest.
- :func:`call_scrubbed` is the transport's pattern for failures: catch, keep
  only a scrubbed message, leave the ``except`` block, then raise. Even
  ``raise ... from None`` keeps the original in ``__context__``, where a
  formatted traceback can still find it; raising outside the block leaves
  ``__context__`` empty.

The registry lives in memory, in this process only. A value shorter than
:data:`MIN_SECRET_LENGTH` cannot be registered, because scrubbing a short
string would mangle unrelated text. This module does no I/O.

Examples
--------
>>> import secrets
>>> value = secrets.token_hex(16)
>>> register(value)
>>> scrub_text(f"GET /series?id=GDP&k={value}") == "GET /series?id=GDP&k=[redacted]"
True
>>> scrub_url("https://api.example.org/v1/series?api_key=abc&id=GDP")
'https://api.example.org/v1/series?id=GDP'
>>> unregister(value)

"""

from __future__ import annotations

import logging
import re
import threading
import traceback
from typing import TYPE_CHECKING, Final
from urllib.parse import quote, quote_plus, unquote_plus, urlsplit, urlunsplit

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = [
    "CREDENTIAL_HEADERS",
    "CREDENTIAL_PARAMETERS",
    "MASK",
    "MAX_MESSAGE_LENGTH",
    "MIN_SECRET_LENGTH",
    "call_scrubbed",
    "describe_exception",
    "install",
    "installed",
    "is_credential_header",
    "is_credential_parameter",
    "register",
    "scrub_headers",
    "scrub_record",
    "scrub_text",
    "scrub_url",
    "scrub_urls",
    "unregister",
]

#: What every scrubbed value is replaced with.
MASK: Final = "[redacted]"
#: The shortest value the registry accepts.
MIN_SECRET_LENGTH: Final = 8
#: The longest message :func:`describe_exception` keeps, in characters.
MAX_MESSAGE_LENGTH: Final = 1_000

#: Query parameters that carry a credential, compared without case: FRED's
#: ``api_key``, BLS's ``registrationkey``, BEA's ``UserID``, Census's ``key``
#: and the common ``apikey``, ``token`` and ``access_token``.
CREDENTIAL_PARAMETERS: Final = frozenset(
    {"access_token", "api_key", "apikey", "key", "registrationkey", "token", "userid"}
)
#: Headers that carry a credential or a session, compared without case.
CREDENTIAL_HEADERS: Final = frozenset(
    {"authorization", "cookie", "proxy-authorization", "set-cookie"}
)
# Any other header whose name says it holds a key, such as X-Api-Key.
_KEY_HEADER: Final = re.compile(r"(?i)key|token|secret|password|auth")
# The value of a credential parameter in free text, up to its delimiter.
_CREDENTIAL_QUERY: Final = re.compile(
    r"(?i)([?&;#](?:" + "|".join(sorted(CREDENTIAL_PARAMETERS)) + r")=)[^&;#\s'\"<>]*"
)
# A URL with a scheme, as far as the next space or quote.
_URL: Final = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"<>]+")
_PERCENT: Final = re.compile(r"%[0-9A-F]{2}")


def _forms(value: str) -> frozenset[str]:
    """Return a value and the forms URL encoding gives it."""
    encoded = {quote(value, safe=""), quote_plus(value, safe="")}
    lowered = {_PERCENT.sub(lambda match: match.group().lower(), e) for e in encoded}
    return frozenset({value} | encoded | lowered)


class _Registry:
    """Every registered value's forms, counted, and the pattern that finds them.

    A form stays registered while any registration of it remains, so two
    secrets that hold the same key do not unregister each other.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self.pattern: re.Pattern[str] | None = None

    def __len__(self) -> int:
        return len(self._counts)

    def add(self, value: str) -> None:
        with self._lock:
            for form in _forms(value):
                self._counts[form] = self._counts.get(form, 0) + 1
            self._rebuild()

    def remove(self, value: str) -> None:
        with self._lock:
            for form in _forms(value):
                count = self._counts.get(form, 0)
                if count > 1:
                    self._counts[form] = count - 1
                else:
                    self._counts.pop(form, None)
            self._rebuild()

    def _rebuild(self) -> None:
        # Longest first, so a value that contains another is replaced whole.
        forms = sorted(self._counts, key=len, reverse=True)
        self.pattern = re.compile("|".join(map(re.escape, forms))) if forms else None


_REGISTRY = _Registry()


def register(value: object) -> None:
    """Register a value, and its URL-encoded forms, for every scrubber.

    Raises
    ------
    TypeError
        If ``value`` is not a string.
    ValueError
        If it is shorter than :data:`MIN_SECRET_LENGTH`.
    """
    if not isinstance(value, str):
        msg = f"only text can be registered, not {type(value).__name__}"
        raise TypeError(msg)
    if len(value) < MIN_SECRET_LENGTH:
        msg = f"a registered value must be at least {MIN_SECRET_LENGTH} characters"
        raise ValueError(msg)
    _REGISTRY.add(value)


def unregister(value: object) -> None:
    """Withdraw one registration of a value; unknown values are ignored."""
    if isinstance(value, str):
        _REGISTRY.remove(value)


def _scrub_url(match: re.Match[str]) -> str:
    try:
        parts = urlsplit(match.group())
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return "<url>"
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def scrub_urls(text: str) -> str:
    """Remove the user information, query and fragment of every URL in a text.

    Examples
    --------
    >>> scrub_urls("GET https://someone@api.example.org/v1/series?page=2#top failed")
    'GET https://api.example.org/v1/series failed'

    """
    return _URL.sub(_scrub_url, text)


def scrub_text(text: str) -> str:
    """Replace every registered value, and every credential parameter's value.

    Examples
    --------
    >>> scrub_text("read /v1/data?UserID=abc&year=2025")
    'read /v1/data?UserID=[redacted]&year=2025'

    """
    pattern = _REGISTRY.pattern
    if pattern is not None:
        text = pattern.sub(MASK, text)
    return _CREDENTIAL_QUERY.sub(lambda match: match.group(1) + MASK, text)


def _is_credential(piece: str) -> bool:
    return is_credential_parameter(unquote_plus(piece.partition("=")[0]))


def scrub_url(url: str) -> str:
    """Return a URL without user information or credential query parameters.

    Parameters named in :data:`CREDENTIAL_PARAMETERS` are dropped whatever
    their case; every registered value left anywhere in the URL is replaced
    with :data:`MASK`. Text that does not parse as a URL is scrubbed as text.

    Examples
    --------
    >>> scrub_url("https://someone:pw@api.example.org:8443/x?registrationkey=k&a=1")
    'https://api.example.org:8443/x?a=1'

    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError:
        return scrub_text(url)
    netloc = parts.netloc
    if host is not None:
        host = f"[{host}]" if ":" in host else host
        netloc = host if port is None else f"{host}:{port}"
    query = "&".join(
        piece for piece in parts.query.split("&") if piece and not _is_credential(piece)
    )
    rebuilt = urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))
    return scrub_text(rebuilt)


def is_credential_parameter(name: str) -> bool:
    """Return whether a query parameter or body field is named like a credential.

    Examples
    --------
    >>> is_credential_parameter("API_KEY"), is_credential_parameter("series_id")
    (True, False)

    """
    return name.casefold() in CREDENTIAL_PARAMETERS


def is_credential_header(name: str) -> bool:
    """Return whether a header holds a credential or a session.

    Examples
    --------
    >>> is_credential_header("Authorization"), is_credential_header("X-Api-Key")
    (True, True)
    >>> is_credential_header("Accept")
    False

    """
    return name.casefold() in CREDENTIAL_HEADERS or bool(_KEY_HEADER.search(name))


def scrub_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return headers without credentials, and with every other value scrubbed.

    ``Authorization``, ``Proxy-Authorization``, ``Cookie`` and ``Set-Cookie``
    are dropped, as is any header whose name holds ``key``, ``token``,
    ``secret``, ``password`` or ``auth``.

    Examples
    --------
    >>> scrub_headers({"Authorization": "Bearer x", "X-Api-Key": "x", "Accept": "*/*"})
    {'Accept': '*/*'}

    """
    return {
        name: scrub_text(value)
        for name, value in headers.items()
        if not is_credential_header(name)
    }


def _safe_str(value: object) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001 - any object may fail to print
        return f"<unprintable {type(value).__name__}>"


def scrub_record(record: logging.LogRecord) -> None:
    """Scrub one log record in place: its message, traceback and stack.

    The message is formatted with its arguments, scrubbed, and stored with
    the arguments cleared, so no handler formats a raw value later. A
    traceback that held a registered value, or could not be formatted to
    check, is stored scrubbed in ``exc_text`` and its ``exc_info`` dropped,
    so no formatter can render it again; any other traceback is left for the
    handlers to format.
    """
    try:
        message = record.getMessage()
    except Exception:  # noqa: BLE001 - a bad format must not break the logging call
        message = (
            f"{_safe_str(record.msg)} [log arguments dropped: they did not "
            "match the message]"
        )
    record.msg = scrub_text(message)
    record.args = ()
    error = record.exc_info[1] if record.exc_info else None
    if error is not None and not record.exc_text:
        dropped = False
        try:
            text = "".join(traceback.format_exception(error)).removesuffix("\n")
        except Exception:  # noqa: BLE001 - never let a traceback break the logging call
            # A traceback nothing could check is never left for a handler.
            text, dropped = "[traceback dropped: it could not be formatted]", True
        scrubbed = scrub_text(text)
        if dropped or scrubbed != text:
            record.exc_text = scrubbed
            record.exc_info = None
    if record.exc_text:
        record.exc_text = scrub_text(record.exc_text)
    if record.stack_info:
        record.stack_info = scrub_text(record.stack_info)


class _RedactingFactory:
    """A log-record factory that scrubs what the factory before it builds."""

    def __init__(self, previous: Callable[..., logging.LogRecord]) -> None:
        self.previous = previous

    def __call__(self, *args: object, **kwargs: object) -> logging.LogRecord:
        record = self.previous(*args, **kwargs)
        scrub_record(record)
        return record


_INSTALL_LOCK = threading.Lock()


def install() -> None:
    """Chain the redacting log-record factory in front of the current one.

    Idempotent: when the current factory is already the redacting one,
    nothing changes. A factory installed before keeps running; its records
    are scrubbed after it builds them.
    """
    with _INSTALL_LOCK:
        current = logging.getLogRecordFactory()
        if not isinstance(current, _RedactingFactory):
            logging.setLogRecordFactory(_RedactingFactory(current))


def installed() -> bool:
    """Return whether the current log-record factory is the redacting one."""
    return isinstance(logging.getLogRecordFactory(), _RedactingFactory)


def describe_exception(error: BaseException) -> str:
    """Return an exception's type and its scrubbed message, for a new exception.

    The message loses every registered value, credential parameter and URL
    query, and is cut to :data:`MAX_MESSAGE_LENGTH` characters.

    Examples
    --------
    >>> describe_exception(TimeoutError("GET https://api.example.org/v1?api_key=k"))
    'TimeoutError: GET https://api.example.org/v1'

    """
    text = scrub_text(scrub_urls(_safe_str(error)))
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH] + "..."
    name = type(error).__name__
    return f"{name}: {text}" if text else name


def call_scrubbed[T](
    call: Callable[[], T],
    error: Callable[[str], BaseException],
    *,
    catch: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Run ``call``; on failure, raise ``error(message)`` with nothing chained.

    The failure is caught, reduced to :func:`describe_exception`'s scrubbed
    text, and the new exception is raised after the ``except`` block has
    ended, so its ``__context__`` and ``__cause__`` are both empty and no
    formatted traceback reaches the original exception or its message.

    Parameters
    ----------
    call
        What to run, with no arguments.
    error
        Builds the exception to raise from the scrubbed message, such as
        ``lambda message: TransportError(message, provider="fred")``.
    catch
        The exception types to convert; anything else propagates unchanged.

    Examples
    --------
    >>> def fetch():
    ...     raise TimeoutError("GET https://api.example.org/v1?api_key=k timed out")
    >>> try:
    ...     call_scrubbed(fetch, RuntimeError)
    ... except RuntimeError as failure:
    ...     print(failure, failure.__context__)
    TimeoutError: GET https://api.example.org/v1 timed out None

    """
    failure = ""
    try:
        return call()
    except catch as caught:
        failure = describe_exception(caught)
    raise error(failure)
