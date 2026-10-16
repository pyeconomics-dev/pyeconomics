# src/pyeconomics/data/transport/http.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``HttpTransport``: the one place a request leaves the process (ADR-0011).

Every request in the project passes through :meth:`HttpTransport.send`. It is
the only code that opens a socket, reveals a key and builds a request URL, and
it is built so that nothing a provider or a caller passes can change where a
request goes or leak what it carries:

- **HTTPS only, allowlisted hosts.** The URL is ``https://`` plus a host the
  provider declared and a path built from validated segments. A redirect is
  followed only to ``https`` on the same allowlist, at most five times; anything
  else is refused. No input reaches the scheme or the host.
- **The key is attached here.** From the provider's authentication spec: a query
  parameter, a body field or a header, or the user's contact in the User-Agent.
  The key chain supplies it as a :class:`~pyeconomics.data.credentials.Secret`;
  it is revealed in this module only.
- **Bounded.** Connect and read timeouts, a per-provider response size cap that
  also bounds decompression, and at most five attempts.
- **Retried politely.** Connection errors, 429 and 5xx back off exponentially with
  full jitter, honouring ``Retry-After`` up to a cap; a request is never sent
  faster than the provider's declared limits (:mod:`.ratelimit`). After the last
  attempt the final response is returned; mapping its status to an error is
  :class:`~pyeconomics.data.providers.base.DataProvider`'s job.
- **Scrubbed errors.** A failure is caught, reduced to its type and a message
  scrubbed of keys and URL queries, and raised after the ``except`` block ends,
  so no exception carries the original as its context or cause.
- **Hosted mode.** It refuses a source hosted mode may not serve before it
  builds anything.

urllib3 and truststore are imported when the first request needs them, never at
import, so the data layer imports without either (Pyodide has no truststore).
One connection pool serves the process; a test passes a fake ``pool``, a fake
``clock`` and ``sleep``, and a seeded ``jitter``.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
import secrets
import sys
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import quote, urlencode, urljoin, urlsplit

import pyeconomics
from pyeconomics.data import modes, redaction
from pyeconomics.data.config import settings
from pyeconomics.data.credentials import resolve_key
from pyeconomics.data.errors import CredentialError, ResponseError, TransportError
from pyeconomics.data.providers.base import AuthKind, KeyPlacement, sends_key
from pyeconomics.data.transport.base import (
    KEPT_HEADERS,
    Request,
    Response,
    check_host,
    declared_hosts,
    retry_after_seconds,
)
from pyeconomics.data.transport.ratelimit import DEFAULT_MAX_WAIT, RateLimiters

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo
    from pyeconomics.data.transport.ratelimit import ProviderLimiter

__all__ = ["MAX_ATTEMPTS", "HttpTransport", "user_agent"]

#: The most attempts one request gets.
MAX_ATTEMPTS: Final = 5
_REPOSITORY: Final = "https://github.com/pyeconomics-dev/pyeconomics"
_REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})
_SWITCH_TO_GET: Final = frozenset({301, 302, 303})
_CHUNK: Final = 64 * 1024
_HTTPS_PORT: Final = 443
_TOO_MANY: Final = 429
_SERVER_ERROR: Final = 500

_logger = logging.getLogger(__name__)
_RANDOM: Final = secrets.SystemRandom()
_POOL_LOCK: Final = threading.Lock()
_SHARED_POOL: dict[str, Any] = {}


def user_agent(contact: str | None = None) -> str:
    """Return the User-Agent every request carries.

    ``pyeconomics/<version> (+https://github.com/pyeconomics-dev/pyeconomics)``,
    followed by the user's contact for a source that requires one.
    """
    base = f"pyeconomics/{pyeconomics.__version__} (+{_REPOSITORY})"
    return f"{base} {contact}" if contact else base


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _full_jitter(ceiling: float) -> float:
    """Return a random wait between zero and ``ceiling`` seconds."""
    return _RANDOM.uniform(0.0, ceiling)


def _shared_pool() -> Any:  # noqa: ANN401 - a urllib3 PoolManager
    """Return the process's one connection pool, building it on first use."""
    with _POOL_LOCK:
        pool = _SHARED_POOL.get("pool")
        if pool is None:
            import ssl  # noqa: PLC0415 - imported when first needed

            import urllib3  # noqa: PLC0415 - imported when first needed

            context = None
            if sys.platform != "emscripten":
                import truststore  # noqa: PLC0415 - not installed in Pyodide

                context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            pool = _SHARED_POOL["pool"] = urllib3.PoolManager(
                num_pools=16, maxsize=4, retries=False, ssl_context=context
            )
        return pool


@dataclass(frozen=True, slots=True, repr=False)
class _Wire:
    """A request as it will leave the process; it may hold the key, so it is private."""

    method: str
    url: str
    headers: dict[str, str]
    payload: bytes | None
    keyed: bool = False

    def __repr__(self) -> str:
        """Show nothing of the URL or headers, which may carry the key."""
        return f"<wire request {self.method}>"


@dataclass(frozen=True, slots=True)
class _Outcome:
    """One attempt: a response, or a scrubbed failure and whether to try again."""

    response: Response | None = None
    failure: str = ""
    retryable: bool = False


class HttpTransport:
    """Sends requests over HTTPS with urllib3 (see the module docstring).

    Parameters
    ----------
    pool
        An object with urllib3's ``PoolManager.request``; the process's shared
        pool by default. Tests pass a fake.
    clock, sleep
        A monotonic clock and a sleep, for the rate limiter and the backoff.
    now
        The time to stamp on a response.
    jitter
        Maps a backoff ceiling to the wait; full jitter by default.
    max_attempts
        Attempts per request, at most :data:`MAX_ATTEMPTS`.
    max_retry_after
        The longest ``Retry-After`` honoured, in seconds; a longer one ends the
        retries and returns the response.
    backoff_base, backoff_cap
        Seconds: the first backoff ceiling, doubling per attempt up to the cap.
    max_redirects
        Redirects followed per attempt.
    connect_timeout, read_timeout
        Seconds.
    max_wait
        The longest rate-limit wait to sleep through before refusing.
    max_duration
        The longest, in seconds, one response body may take to arrive; a body
        that dribbles in slower is dropped and the request retried.
    """

    def __init__(  # noqa: PLR0913 - every knob is for a test or an operator
        self,
        *,
        pool: Any = None,  # noqa: ANN401 - a urllib3 PoolManager or a fake
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], dt.datetime] = _utc_now,
        jitter: Callable[[float], float] = _full_jitter,
        max_attempts: int = MAX_ATTEMPTS,
        max_retry_after: float = 60.0,
        backoff_base: float = 0.5,
        backoff_cap: float = 30.0,
        max_redirects: int = 5,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        max_wait: float = DEFAULT_MAX_WAIT,
        max_duration: float = 120.0,
    ) -> None:
        self._pool_object = pool
        self._clock = clock
        self._max_duration = max_duration
        self._sleep = sleep
        self._now = now
        self._jitter = jitter
        self._max_attempts = max(1, min(max_attempts, MAX_ATTEMPTS))
        self._max_retry_after = max_retry_after
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._max_redirects = max_redirects
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._limiters = RateLimiters(clock, max_wait=max_wait)

    # --- sending ---------------------------------------------------------------

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Send one request on a provider's behalf and return the final answer.

        Returns
        -------
        Response
            The answer, of any HTTP status: after a retryable status
            (429, 5xx) it is the last attempt's.

        Raises
        ------
        LicenceError
            In hosted mode, for a source hosted mode may not serve.
        OfflineError
            In offline mode, which sends no request.
        TransportError
            For a host off the allowlist, a refused redirect, or a connection
            that failed on every attempt.
        CredentialError
            If the provider needs a key or a contact and none is configured.
        RateLimitError
            If the provider's declared limit would make the request wait longer
            than the cap.
        ResponseError
            If the body exceeds the provider's size cap.
        """
        modes.require_allowed(info.terms, provider=info.id)
        modes.require_online(provider=info.id)
        check_host(info, request)
        wire = self._wire(info, request, key)
        limiter = self._limiters.for_provider(info)
        for attempt in range(1, self._max_attempts + 1):
            outcome = self._attempt(info, wire, limiter)
            last = attempt == self._max_attempts
            if outcome.response is None:
                if last or not outcome.retryable:
                    msg = f"{info.id} could not be reached: {outcome.failure}"
                    if attempt > 1:
                        msg += f" (after {attempt} attempts)"
                    raise TransportError(msg, provider=info.id)
                self._pause(info, attempt, None)
                continue
            response = outcome.response
            if not self._retryable(response.status) or last:
                return response
            advice = retry_after_seconds(
                response.header("retry-after"), response.retrieved_at
            )
            if advice is not None and advice > self._max_retry_after:
                return response
            self._pause(info, attempt, advice)
        msg = "unreachable: the last attempt returns or raises"  # pragma: no cover
        raise AssertionError(msg)  # pragma: no cover

    @staticmethod
    def _retryable(status: int) -> bool:
        return status == _TOO_MANY or status >= _SERVER_ERROR

    def _pause(self, info: ProviderInfo, attempt: int, advice: float | None) -> None:
        """Sleep before the next attempt: jittered backoff, or the advised wait."""
        ceiling = min(self._backoff_cap, self._backoff_base * 2 ** (attempt - 1))
        delay = max(self._jitter(ceiling), advice or 0.0)
        _logger.debug(
            "retrying %s in %.2f s (attempt %d failed)", info.id, delay, attempt
        )
        self._sleep(delay)

    # --- building the wire request -----------------------------------------------

    def _wire(
        self, info: ProviderInfo, request: Request, key: str | Secret | None
    ) -> _Wire:
        """Build the URL, headers and body, attaching the key or the contact."""
        params = list(request.params)
        headers = {
            "User-Agent": user_agent(self._contact(info)),
            "Accept-Encoding": "gzip",
        }
        headers.update(request.headers)
        body: Any = request.body
        keyed = sends_key(info, key)
        if keyed:
            slot = info.auth.slot(request.key_placement)
            if slot is None:
                msg = (
                    f"{info.id} declares no {request.key_placement} placement "
                    "for its key"
                )
                raise CredentialError(msg, provider=info.id)
            revealed = resolve_key(info.id, key).reveal()
            name, scheme = slot.name, slot.scheme
            if slot.placement is KeyPlacement.QUERY:
                params.append((name, revealed))
            elif slot.placement is KeyPlacement.HEADER:
                headers[name] = f"{scheme} {revealed}" if scheme else revealed
            elif body is None or isinstance(body, dict):  # the body placement
                body = {**(body or {}), name: revealed}
            else:
                msg = f"{info.id} sends its key in a body, which this request has not"
                raise CredentialError(msg, provider=info.id)
        url = f"https://{request.host}{request.path}"
        if params:
            url += "?" + urlencode(params, quote_via=quote)
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body, separators=(",", ":")).encode("ascii")
        return _Wire(request.method, url, headers, payload, keyed)

    def _contact(self, info: ProviderInfo) -> str | None:
        """Return the user's contact for a source that requires it."""
        if info.auth.kind is not AuthKind.CONTACT:
            return None
        contact = settings().sec_contact
        if contact is None:
            msg = (
                f"{info.id} requires your contact (a name and an email address) in "
                "its User-Agent; set PYECONOMICS_SEC_CONTACT or sec_contact in "
                "pyeconomics.toml"
            )
            raise CredentialError(msg, provider=info.id)
        return contact.get_secret_value()

    # --- one attempt ---------------------------------------------------------------

    def _timeout(self) -> Any:  # noqa: ANN401 - a urllib3 Timeout
        import urllib3  # noqa: PLC0415 - imported when first needed

        return urllib3.Timeout(connect=self._connect_timeout, read=self._read_timeout)

    def _pool(self) -> Any:  # noqa: ANN401 - a urllib3 PoolManager or a fake
        return self._pool_object if self._pool_object is not None else _shared_pool()

    def _attempt(
        self, info: ProviderInfo, wire: _Wire, limiter: ProviderLimiter
    ) -> _Outcome:
        """Send once, following allowlisted HTTPS redirects, and read the body.

        Every request on the wire, a redirect's included, takes a place in the
        provider's limit.
        """
        method, url, headers, payload = (
            wire.method,
            wire.url,
            wire.headers,
            wire.payload,
        )
        for _hop in range(self._max_redirects + 1):
            limiter.acquire(self._sleep, keyed=wire.keyed)
            raw, failure = self._open(method, url, headers, payload)
            if raw is None:
                return failure
            status = int(raw.status)
            location = raw.headers.get("location")
            if status in _REDIRECT_STATUSES and location and info.follow_redirects:
                self._discard(raw)
                url = self._follow(info, url, location)
                if status in _SWITCH_TO_GET:
                    method, payload = "GET", None
                    headers = {
                        name: value
                        for name, value in headers.items()
                        if name.casefold() != "content-type"
                    }
                continue
            return self._read(info, raw, status)
        msg = f"{info.id} redirected more than {self._max_redirects} times"
        raise TransportError(msg, provider=info.id)

    def _open(
        self, method: str, url: str, headers: dict[str, str], payload: bytes | None
    ) -> tuple[Any, _Outcome]:
        """Issue the request; a failure comes back scrubbed, never raised here."""
        import ssl  # noqa: PLC0415 - imported when first needed

        import urllib3  # noqa: PLC0415 - imported when first needed

        failure = ""
        retryable = False
        try:
            raw = self._pool().request(
                method,
                url,
                body=payload,
                headers=headers,
                redirect=False,
                retries=False,
                preload_content=False,
                timeout=self._timeout(),
            )
        except (ssl.SSLError, urllib3.exceptions.SSLError) as error:
            failure = redaction.describe_exception(error)
        except (urllib3.exceptions.HTTPError, OSError) as error:
            failure, retryable = redaction.describe_exception(error), True
        except Exception as error:  # noqa: BLE001 - nothing else may carry the URL out
            failure = redaction.describe_exception(error)
        else:
            return raw, _Outcome()
        return None, _Outcome(failure=failure, retryable=retryable)

    def _follow(self, info: ProviderInfo, current: str, location: str) -> str:
        """Resolve a redirect and refuse anything but HTTPS on the allowlist."""
        target = urljoin(current, location)
        parts = urlsplit(target)
        if parts.scheme != "https":
            msg = f"{info.id} was redirected to an address that is not HTTPS"
            raise TransportError(msg, provider=info.id)
        host = parts.hostname or ""
        if (
            parts.username is not None
            or parts.password is not None
            or parts.port not in {None, _HTTPS_PORT}
            or host not in declared_hosts(info)
        ):
            where = host or "an invalid host"
            msg = f"{info.id} was redirected to {where}, which is not a declared host"
            raise TransportError(msg, provider=info.id)
        return target

    @staticmethod
    def _discard(raw: Any, *, close: bool = False) -> None:  # noqa: ANN401
        """Release a response whose body is not wanted, or close an unread one."""
        with contextlib.suppress(Exception):
            raw.close() if close else raw.release_conn()

    def _read(self, info: ProviderInfo, raw: Any, status: int) -> _Outcome:  # noqa: ANN401
        """Read the body up to the provider's size cap and build the response."""
        cap = info.max_response_bytes
        declared = raw.headers.get("content-length")
        if declared is not None and declared.isdecimal() and int(declared) > cap:
            self._discard(raw, close=True)
            msg = f"{info.id} sent a response larger than {cap} bytes"
            raise ResponseError(msg, provider=info.id)
        chunks: list[bytes] = []
        total = 0
        failure = ""
        retryable = False
        oversize = slow = False
        deadline = self._clock() + self._max_duration
        try:
            for chunk in raw.stream(_CHUNK, decode_content=True):
                total += len(chunk)
                if total > cap:
                    oversize = True
                    break
                chunks.append(chunk)
                if self._clock() > deadline:
                    slow, retryable = True, True
                    failure = f"the response took longer than {self._max_duration:g} s"
                    break
        except Exception as error:  # noqa: BLE001 - scrubbed, then re-raised below
            failure = redaction.describe_exception(error)
            retryable = not _is_tls(error)
        finally:
            self._discard(raw, close=oversize or slow)
        if oversize:
            msg = f"{info.id} sent a response larger than {cap} bytes"
            raise ResponseError(msg, provider=info.id)
        if failure:
            return _Outcome(failure=failure, retryable=retryable)
        headers = tuple(
            (name, raw.headers[name]) for name in KEPT_HEADERS if name in raw.headers
        )
        response = Response(status, b"".join(chunks), self._now(), headers)
        _logger.debug("%s -> HTTP %d (%d bytes)", info.id, status, total)
        return _Outcome(response=response)

    def close(self) -> None:
        """Close this transport's own pool, if it was given one."""
        pool = self._pool_object
        if pool is not None and hasattr(pool, "clear"):
            pool.clear()


def _is_tls(error: BaseException) -> bool:
    import ssl  # noqa: PLC0415 - imported when first needed

    return isinstance(error, ssl.SSLError)
