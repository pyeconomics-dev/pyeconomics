# src/pyeconomics/data/snapshots/writer.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot job: fetch the set, write each provider's object, then current.json.

``python -m pyeconomics.data.snapshots write`` runs :func:`write` as a Cloud Run
job in hosted mode, once a day and once per staging deploy (ADR-0013 decision 6),
with the bucket mounted read-write at ``PYECONOMICS_SNAPSHOT_DIR``:

1. It refuses to run outside hosted mode, so a source not hosted-safe is refused
   before any request, by the resolver's rule and the provider's own gate.
2. Inside ``cache.bypass()``, which also stands the snapshot reader aside, it
   fetches every entry of :func:`~pyeconomics.data.snapshots.set.snapshot_set`
   through ``data.get``, one provider at a time, within each provider's declared
   rate limits (the transport holds it to them). A request the provider repeats
   for another series of the run is answered from memory, never from storage.
3. A series' own terms are checked again: nothing outside ``hosted-safe`` terms
   that allow storage is kept (:func:`~pyeconomics.data.snapshots.codec.encode_object`
   refuses it as well). A series its source serves only by window (Treasury's
   curves, a file a month) is fetched incrementally: its last :data:`REFRESH`
   again, and a year further back (:data:`BACKFILL`) until its history reaches
   its declared start, spliced onto what the last run kept.
4. A series that fails keeps its last good frame, with its old retrieval time; a
   provider none of whose series succeeded keeps its last good object. Either way
   ``current.json`` marks the failure with its problem slug.
5. Each provider object is written under the run's own id, never overwriting
   another, and ``current.json`` is written last, through a temporary file.
6. Runs older than thirty days that ``current.json`` no longer names are deleted.
7. The heartbeat URL (``PYECONOMICS_SNAPSHOT_HEARTBEAT``, a secret registered
   with redaction) is requested through the data layer's transport, on the one
   host :data:`HEARTBEAT` declares; its ``/fail`` form when no provider succeeded.

The job exits non-zero only when no provider succeeded. Its log records name
providers, series and problem slugs; never a URL, a path or a key.

This module reads files, the clock and the environment's settings; it is one of
the data layer's I/O modules.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

from pyeconomics.core.errors import (
    ConvergenceError,
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelNotFoundError,
    PyeconomicsError,
    RegistryError,
)
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data import api, cache, redaction
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.cache.policy import may_store
from pyeconomics.data.config import HEARTBEAT_VARIABLE, settings, snapshot_heartbeat
from pyeconomics.data.errors import (
    ConceptNotFoundError,
    ConfigError,
    CredentialError,
    DataError,
    LicenceError,
    LlmUseError,
    OfflineError,
    ProviderNotFoundError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    SnapshotMissingError,
    SourceDisabledError,
    TransportError,
)
from pyeconomics.data.modes import Mode, current_mode
from pyeconomics.data.providers.base import ProviderInfo, RateLimit
from pyeconomics.data.snapshots import codec
from pyeconomics.data.snapshots.set import snapshot_set
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport import default_transport
from pyeconomics.data.transport import files as spreadsheets
from pyeconomics.data.transport.base import Request, request_key
from pyeconomics.data.types import Series, Table

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.data.snapshots.set import Entry, SnapshotSet
    from pyeconomics.data.transport.base import Response, Transport

__all__ = [
    "BACKFILL",
    "FAILURE_SLUGS",
    "HEARTBEAT",
    "HEARTBEAT_HOST",
    "REFRESH",
    "Report",
    "failure_slug",
    "heartbeat_request",
    "write",
]

#: The one host the heartbeat may be sent to: Better Stack's heartbeat endpoint
#: (ADR-0013 decision 15), as its documentation names it on 2026-11-02.
HEARTBEAT_HOST: Final = "incidents.betterstack.com"
#: The heartbeat's declaration, as a provider's hosts are declared, so the
#: transport holds it to its one host, HTTPS and a rate. It carries no data.
HEARTBEAT: Final = ProviderInfo(
    id="snapshot_heartbeat",
    name="Better Stack heartbeat",
    homepage="https://betterstack.com",
    terms=Terms(
        licence=LicenceClass.HOSTED_SAFE,
        terms_url="https://betterstack.com/terms",
        checked=dt.date(2026, 11, 2),
        attribution="Better Stack heartbeat; it carries no data.",
        llm_use=LlmUse.FORBIDDEN,
        cache=CachePolicy.FORBIDDEN,
    ),
    hosts=(HEARTBEAT_HOST,),
    rate_limits=(RateLimit(requests=1, per="second"),),
)
#: Each error class's problem slug, as ``pyeconomics.surfaces.problems`` maps it;
#: the data layer imports no surface, so a test holds the two equal. An error
#: takes the slug of the nearest class in its MRO listed here.
FAILURE_SLUGS: Final[Mapping[type[BaseException], str]] = {
    InputError: "invalid-input",
    DomainError: "no-defined-result",
    ConvergenceError: "no-convergence",
    ModelNotFoundError: "model-not-found",
    ProviderNotFoundError: "provider-not-found",
    ConceptNotFoundError: "concept-not-found",
    SeriesNotFoundError: "series-not-found",
    SnapshotMissingError: "not-in-snapshot",
    LlmUseError: "llm-use-forbidden",
    LicenceError: "licence-refused",
    CredentialError: "credential-unavailable",
    TransportError: "upstream-unavailable",
    ResponseError: "upstream-invalid-response",
    RateLimitError: "upstream-rate-limited",
    OfflineError: "offline-cache-miss",
    SourceDisabledError: "source-disabled",
    ConfigError: "invalid-configuration",
    DataError: "data-unavailable",
    MissingOptionalDependencyError: "missing-extra",
    RegistryError: "registry-error",
    PyeconomicsError: "pyeconomics-error",
}
#: How much of a windowed series' recent history each run fetches again, so a
#: late correction of the last weeks is picked up.
REFRESH: Final = dt.timedelta(days=45)
#: How far back one run extends a windowed series' history towards its declared
#: start; a source that answers slowly by month (Treasury's curves) stays inside
#: the job's time.
BACKFILL: Final = dt.timedelta(days=366)
# A history whose first observation lies this close to its declared start is whole.
_WHOLE: Final = dt.timedelta(days=31)
_DAY: Final = dt.timedelta(days=1)
_INTERNAL: Final = "internal-error"
_HEARTBEAT_PATH: Final = re.compile(r"/api/v1/heartbeat/([A-Za-z0-9]{8,128})")
_LOG: Final = logging.getLogger("pyeconomics.data.snapshots")
_TEMPORARY: Final = f"{codec.CURRENT}.tmp"


def failure_slug(error: BaseException) -> str:
    """Return the problem slug an error maps to, as the error table maps it."""
    for kind in type(error).__mro__:
        slug = FAILURE_SLUGS.get(kind)
        if slug is not None:
            return slug
    return _INTERNAL


@dataclass(frozen=True, slots=True, kw_only=True)
class Report:
    """What a run did: its manifest, the providers and series, and its time."""

    run: str
    manifest: codec.Manifest
    succeeded: tuple[str, ...]
    """Providers with at least one series fetched in this run."""
    failed: tuple[str, ...]
    """Providers none of whose series could be fetched."""
    series_written: int
    series_failed: int
    seconds: float
    pruned: tuple[str, ...]
    """The runs deleted."""
    heartbeat: str
    """``sent``, ``failure_sent``, ``failed`` or ``not_configured``."""

    @property
    def ok(self) -> bool:
        """Whether any provider succeeded, which is when the job exits zero."""
        return bool(self.succeeded)

    def summary(self) -> dict[str, object]:
        """Return the run's counts as JSON-ready values, with no URL or key."""
        return {
            "failed": list(self.failed),
            "heartbeat": self.heartbeat,
            "pruned": len(self.pruned),
            "run": self.run,
            "seconds": round(self.seconds, 1),
            "series_failed": self.series_failed,
            "series_written": self.series_written,
            "succeeded": list(self.succeeded),
        }


class _RunTransport:
    """Send each distinct request of one provider once per run.

    CBO's reports and the Penn World Table's workbook answer every series of the
    provider, so they are asked once. The answers live in memory for the
    provider's part of the run only: nothing is stored.
    """

    def __init__(self, inner: Transport) -> None:
        self._inner = inner
        self._answers: dict[tuple[str, str], Response] = {}

    def send(
        self, info: ProviderInfo, request: Request, *, key: str | Secret | None = None
    ) -> Response:
        """Answer a repeated request from memory; send any other."""
        asked = (info.id, request_key(request))
        held = self._answers.get(asked)
        if held is not None:
            return held
        response = self._inner.send(info, request, key=key)
        if response.ok:
            self._answers[asked] = response
        return response


def heartbeat_request(url: str, *, failed: bool = False) -> Request:
    """Return the heartbeat's request, refusing any URL but Better Stack's form.

    The token in the path is registered with redaction first, so no log record
    of the request can show it.

    Raises
    ------
    ConfigError
        If the URL is not ``https://incidents.betterstack.com/api/v1/heartbeat/
        <token>``; the message names the variable, never its value.
    """
    parts = urlsplit(url)
    match = _HEARTBEAT_PATH.fullmatch(parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != HEARTBEAT_HOST
        or parts.query
        or parts.fragment
        or match is None
    ):
        msg = (
            f"{HEARTBEAT_VARIABLE} is not a Better Stack heartbeat URL "
            f"(https://{HEARTBEAT_HOST}/api/v1/heartbeat/<token>)"
        )
        raise ConfigError(msg)
    redaction.register(match.group(1))
    return Request(host=HEARTBEAT_HOST, path=parts.path + ("/fail" if failed else ""))


# --- the run --------------------------------------------------------------------------


def write(  # noqa: PLR0913 - the run's seams for tests and the job
    directory: Path | None = None,
    *,
    chosen: SnapshotSet | None = None,
    registry: ProviderRegistry | None = None,
    transport: Transport | None = None,
    clock: Callable[[], dt.datetime] | None = None,
    nonce: str | None = None,
) -> Report:
    """Write one snapshot run and return what it did.

    Parameters
    ----------
    directory
        The snapshot directory; ``PYECONOMICS_SNAPSHOT_DIR`` by default.
    chosen
        The series to fetch; :func:`~pyeconomics.data.snapshots.set.snapshot_set`
        by default.
    registry, transport
        Seams for tests: an isolated provider registry and a transport, which
        also sends the heartbeat.
    clock, nonce
        Seams for tests: the time and the run id's random part.

    Raises
    ------
    ConfigError
        Outside hosted mode, or without a snapshot directory.
    """
    if current_mode() is not Mode.HOSTED:
        msg = "the snapshot writer runs in hosted mode (PYECONOMICS_MODE=hosted)"
        raise ConfigError(msg)
    where = directory or settings().snapshot_dir
    if where is None:
        msg = "set PYECONOMICS_SNAPSHOT_DIR to the snapshot directory"
        raise ConfigError(msg)
    heartbeat = snapshot_heartbeat()
    if heartbeat is not None:
        heartbeat_request(heartbeat)  # refuse a malformed URL before any fetch

    def now() -> dt.datetime:
        moment = clock() if clock is not None else dt.datetime.now(dt.UTC)
        return moment.astimezone(dt.UTC)

    began = time.monotonic()
    run = codec.run_id(now(), nonce or secrets.token_hex(4))
    previous = _previous(where)
    wanted = chosen or snapshot_set(registry=registry)
    statuses: dict[str, codec.ProviderStatus] = {}
    succeeded: list[str] = []
    written = failed = 0
    with cache.bypass():
        for provider in wanted.providers():
            before = None if previous is None else previous.providers.get(provider)
            status, fresh = _provider(
                provider,
                wanted.of(provider),
                before,
                where=where,
                run=run,
                today=now().date(),
                registry=registry,
                transport=transport,
            )
            statuses[provider] = status
            written += fresh
            failed += sum(1 for s in status.series.values() if s.failure)
            if fresh:
                succeeded.append(provider)
    manifest = codec.Manifest(run=run, completed_at=now(), providers=statuses)
    _replace(where, manifest)
    pruned = _prune(where, manifest, now())
    beat = _heartbeat(heartbeat, failed=not succeeded, transport=transport)
    report = Report(
        run=run,
        manifest=manifest,
        succeeded=tuple(succeeded),
        failed=tuple(p for p in wanted.providers() if p not in succeeded),
        series_written=written,
        series_failed=failed,
        seconds=time.monotonic() - began,
        pruned=pruned,
        heartbeat=beat,
    )
    _LOG.info(
        "snapshot run %s: %d of %d providers, %d series written, %d failed, %.1f s",
        run,
        len(report.succeeded),
        len(wanted.providers()),
        written,
        failed,
        report.seconds,
    )
    return report


def _previous(directory: Path) -> codec.Manifest | None:
    """Return the last run's ``current.json``, or ``None`` if there is none."""
    path = directory / codec.CURRENT
    try:
        with path.open("rb") as handle:
            data = handle.read(codec.MAX_CURRENT_BYTES + 1)
        return codec.decode_manifest(data)
    except FileNotFoundError:
        return None
    except (OSError, ResponseError) as error:
        _LOG.warning(
            "the previous current.json was unreadable and is ignored: %s",
            type(error).__name__,
        )
        return None


def _old_entries(
    directory: Path, provider: str, before: codec.ProviderStatus | None
) -> dict[str, codec.Entry]:
    """Return the entries of the provider's last good object, verified."""
    if before is None:
        return {}
    for ref in (before.object, before.previous):
        if ref is None:
            continue
        try:
            with (directory / ref.name).open("rb") as handle:
                data = handle.read(codec.MAX_OBJECT_BYTES + 1)
            if codec.digest(data) != ref.sha256:
                continue
            return codec.decode_object(data, provider=provider)
        except (OSError, ResponseError):
            continue
    return {}


def _get(
    entry: Entry,
    registry: ProviderRegistry | None,
    transport: Transport,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> Series | Table:
    """Fetch one series over a window and check its terms; raise on any failure.

    A source whose terms keep it out of the snapshot is refused before any
    request; the series' own terms are checked again once it is fetched.
    """
    source = (registry or provider_registry.installed()).provider_class(entry.provider)
    _require_storable(source.info.terms, entry.provider)
    frame = api.get(
        entry.target,
        start=start,
        end=end,
        vintage=entry.vintage,
        mode=Mode.HOSTED,
        transport=transport,
        registry=registry,
    ).frame
    _require_storable(frame.meta.terms, entry.provider)
    return frame


def _fetch(
    entry: Entry,
    old: codec.Entry | None,
    registry: ProviderRegistry | None,
    transport: Transport,
    today: dt.date,
) -> codec.Entry:
    """Fetch one series whole, or a windowed one incrementally onto its last run.

    A windowed series with nothing kept is fetched over the last year (or from
    its start). With a kept history it is fetched again from :data:`REFRESH`
    before its last observation, and, until its history is whole, over the year
    before its first; the parts are spliced, the newest winning on a shared day.
    A failed backfill keeps the history as it was; a failed refresh fails the
    series, which then keeps its last good frame.
    """
    if entry.start is None:
        return codec.Entry(_get(entry, registry, transport), entry.vintage)
    start = entry.start
    held = None if old is None or old.vintage != entry.vintage else old.frame
    if held is None or not held.index or held.realtime is not None:
        frame = _get(entry, registry, transport, max(start, today - BACKFILL), today)
        return codec.Entry(frame, entry.vintage, start)
    first, last = held.index[0], held.index[-1]
    parts = [held, _get(entry, registry, transport, max(start, last - REFRESH), today)]
    if first - start > _WHOLE:
        try:
            older = _get(
                entry, registry, transport, max(start, first - BACKFILL), first - _DAY
            )
        except Exception as error:  # noqa: BLE001 - a backfill never fails the series
            _LOG.warning(
                "%s %s kept its history; the year before it was not fetched: %s",
                entry.provider,
                entry.series,
                failure_slug(error),
            )
        else:
            parts.insert(0, older)
    spliced = _splice(parts)
    if spliced is None:
        _LOG.warning(
            "%s %s changed its shape; its history starts again",
            entry.provider,
            entry.series,
        )
        spliced = parts[-1]
    return codec.Entry(spliced, entry.vintage, start)


def _shape(frame: Series | Table) -> tuple[object, ...]:
    """Return what two parts of one history share: kind, metadata, columns."""
    meta = replace(frame.meta, retrieved_at=None, notes=())
    columns = frame.columns if isinstance(frame, Table) else ()
    return (type(frame), meta, columns, frame.realtime is None)


def _splice(parts: Sequence[Series | Table]) -> Series | Table | None:
    """Join parts of one history by day, the later part winning; ``None`` if unlike.

    The result carries the newest part's metadata, so its retrieval time.
    """
    newest = parts[-1]
    if any(_shape(part) != _shape(newest) or part.realtime for part in parts):
        return None
    if isinstance(newest, Series):
        values: dict[dt.date, float | None] = {}
        for part in parts:
            if isinstance(part, Series):
                values.update(zip(part.index, part.values, strict=True))
        days = tuple(sorted(values))
        return replace(newest, index=days, values=tuple(values[d] for d in days))
    rows: dict[dt.date, tuple[float | None, ...]] = {}
    for part in parts:
        if isinstance(part, Table):
            rows.update(
                (day, tuple(column[i] for column in part.data))
                for i, day in enumerate(part.index)
            )
    days = tuple(sorted(rows))
    width = len(newest.columns)
    data = tuple(tuple(rows[d][c] for d in days) for c in range(width))
    return replace(newest, index=days, data=data)


def _require_storable(terms: Terms, provider: str) -> None:
    """Refuse data whose terms keep it out of the hosted snapshot."""
    if terms.licence is not LicenceClass.HOSTED_SAFE or not may_store(terms):
        reason = "its terms keep it out of the hosted snapshot"
        raise LicenceError(
            reason, provider=provider, licence=terms.licence, terms_url=terms.terms_url
        )


def _status(entry: codec.Entry | None, failure: str | None) -> codec.SeriesStatus:
    if entry is None:
        return codec.SeriesStatus(failure=failure)
    frame = entry.frame
    return codec.SeriesStatus(
        last_observation=frame.index[-1] if frame.index else None,
        retrieved_at=frame.meta.retrieved_at,
        failure=failure,
    )


def _provider(  # noqa: PLR0913 - one provider's part of the run
    provider: str,
    entries: Sequence[Entry],
    before: codec.ProviderStatus | None,
    *,
    where: Path,
    run: str,
    today: dt.date,
    registry: ProviderRegistry | None,
    transport: Transport | None,
) -> tuple[codec.ProviderStatus, int]:
    """Fetch one provider's series and write its object; return its status."""
    began = time.monotonic()
    shared = _RunTransport(transport or default_transport())
    fresh: dict[str, codec.Entry] = {}
    failures: dict[str, str] = {}
    windowed = any(entry.start is not None for entry in entries)
    old = _old_entries(where, provider, before) if windowed else None
    with spreadsheets.reuse():
        for entry in entries:
            kept_entry = None if old is None else old.get(entry.series)
            try:
                fresh[entry.series] = _fetch(entry, kept_entry, registry, shared, today)
            except Exception as error:  # noqa: BLE001 - one series never stops the run
                failures[entry.series] = failure_slug(error)
                _LOG.warning(
                    "%s %s was not fetched: %s (%s)",
                    provider,
                    entry.series,
                    failures[entry.series],
                    type(error).__name__,
                )
    if old is None:
        old = _old_entries(where, provider, before) if failures else {}
    kept = {s: old[s] for s in failures if s in old}
    series = {
        entry.series: _status(
            fresh.get(entry.series) or kept.get(entry.series),
            failures.get(entry.series),
        )
        for entry in entries
    }
    if not fresh:
        first = failures[min(failures)] if failures else None
        _LOG.warning("%s kept its last good object: %s", provider, first)
        status = codec.ProviderStatus(
            object=None if before is None else before.object,
            previous=None if before is None else before.previous,
            failure=first,
            series=series,
        )
        return status, 0
    data = codec.encode_object(provider, run, {**kept, **fresh})
    name = codec.object_name(run, provider)
    _write_new(where / name, data)
    status = codec.ProviderStatus(
        object=codec.ObjectRef(name=name, sha256=codec.digest(data)),
        previous=None if before is None else before.object,
        series=series,
    )
    _LOG.info(
        "%s: %d series written, %d kept from the last good run, %.1f s",
        provider,
        len(fresh),
        len(kept),
        time.monotonic() - began,
    )
    return status, len(fresh)


# --- files ----------------------------------------------------------------------------


def _write_new(path: Path, data: bytes) -> None:
    """Write a new file, flushed to storage before it is closed; never overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        msg = "a snapshot run never overwrites an object"
        raise ConfigError(msg)
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _replace(directory: Path, manifest: codec.Manifest) -> None:
    """Write ``current.json`` through a temporary file, last of all."""
    temporary = directory / _TEMPORARY
    with temporary.open("wb") as handle:
        handle.write(codec.encode_manifest(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(directory / codec.CURRENT)


def _prune(
    directory: Path, manifest: codec.Manifest, now: dt.datetime
) -> tuple[str, ...]:
    """Delete runs older than :data:`~codec.RETAIN` the manifest no longer names."""
    keep = {codec.parse_object_name(name)[0] for name in manifest.names()}
    keep.add(manifest.run)
    removed: list[str] = []
    for child in sorted(directory.iterdir()):
        if (
            child.is_symlink()
            or not child.is_dir()
            or not codec.RUN_ID_PATTERN.fullmatch(child.name)
            or child.name in keep
            or now - codec.run_started(child.name) <= codec.RETAIN
        ):
            continue
        for item in child.iterdir():
            if item.is_file() and not item.is_symlink() and item.suffix == ".gz":
                item.unlink()
        with contextlib.suppress(OSError):
            child.rmdir()
        removed.append(child.name)
    return tuple(removed)


def _heartbeat(url: str | None, *, failed: bool, transport: Transport | None) -> str:
    """Request the heartbeat URL, its ``/fail`` form when nothing succeeded."""
    if url is None:
        return "not_configured"
    try:
        response = (transport or default_transport()).send(
            HEARTBEAT, heartbeat_request(url, failed=failed)
        )
    except DataError as error:
        _LOG.warning("the heartbeat was not sent: %s", type(error).__name__)
        return "failed"
    if not response.ok:
        _LOG.warning("the heartbeat answered HTTP %d", response.status)
        return "failed"
    return "failure_sent" if failed else "sent"
