# src/pyeconomics/data/snapshots/reader.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The hosted service's side of the snapshot: every series from the daily copy.

With ``PYECONOMICS_SNAPSHOT_DIR`` set in hosted mode (:func:`active`),
:meth:`~pyeconomics.data.providers.base.DataProvider.fetch_with_origin` asks
:func:`lookup` after its licence gate and before the cache or any transport, so
the service never asks a source itself (ADR-0013 decision 6):

- ``current.json`` is read at most once a minute (:data:`REREAD_SECONDS`); a
  missing or unreadable one keeps the last good copy, and before any exists
  every series is refused.
- Each provider object named there is read once, checked against its SHA-256
  in ``current.json``, expanded within its cap, validated frame by frame
  (:mod:`~pyeconomics.data.snapshots.codec`) and kept in memory by its SHA-256.
  A bad object is reported (a log record and a ``snapshot_object_rejected``
  warning, naming the provider, never a path) and skipped: the object before it,
  or the last good one in memory, is served instead.
- A series the snapshot holds is served with its own retrieval time, the record
  marked ``served_from_snapshot``; one retrieved more than two days ago is
  marked ``stale_snapshot`` and still served. A window that ends before the
  history a series served by window holds so far is refused. A series outside
  the snapshot is refused with
  :class:`~pyeconomics.data.errors.SnapshotMissingError`, which points to local
  mode. The service never falls back to a live fetch: in hosted
  mode the other operations (search, describe, vintages, records) are refused
  the same way.

Without the directory, or inside ``cache.bypass()`` (the job that writes the
snapshot), :func:`active` is false and hosted mode fetches per request, as in
Phase 4. This module reads files and the clock; it is one of the data layer's
I/O modules.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import threading
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pyeconomics.data import cache
from pyeconomics.data.cache.policy import Fetched, Origin
from pyeconomics.data.config import settings
from pyeconomics.data.errors import DataWarning, ResponseError, SnapshotMissingError
from pyeconomics.data.snapshots import codec
from pyeconomics.data.types import Series, Table
from pyeconomics.data.vintage import VintageKind

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from pyeconomics.data.providers.base import ProviderInfo, Query

__all__ = [
    "REJECTED_WARNING",
    "REREAD_SECONDS",
    "active",
    "lookup",
    "override",
    "refuse",
    "reset",
]

#: How often ``current.json`` is read again, at most, in seconds.
REREAD_SECONDS: Final = 60.0
#: The warning code of an object that failed its checks and was skipped.
REJECTED_WARNING: Final = "snapshot_object_rejected"

_LOG: Final = logging.getLogger("pyeconomics.data.snapshots")
_PACKAGE_DIR: Final = str(Path(__file__).parents[2])
_WINDOW_FIELDS: Final = frozenset(
    {"series", "start", "end", "max_observations", "vintage"}
)
# The operations the command line offers as `pyeconomics data <operation>`.
_COMMANDS: Final = frozenset({"search", "describe", "vintages"})


@dataclass(slots=True)
class _State:
    """What one process has read: the manifest and the objects, by SHA-256."""

    manifest: codec.Manifest | None = None
    checked_at: float | None = None
    objects: dict[str, dict[str, codec.Entry]] = field(default_factory=dict)
    served: dict[str, str] = field(default_factory=dict)
    """Per provider, the SHA-256 of the object last served."""
    clock: Callable[[], dt.datetime] | None = None
    monotonic: Callable[[], float] | None = None


_LOCK: Final = threading.Lock()
_STATE = _State()


def reset() -> None:
    """Forget everything read, and any override. The test suite calls this."""
    global _STATE  # noqa: PLW0603 - the process's one reader state
    with _LOCK:
        _STATE = _State()


@contextlib.contextmanager
def override(
    *,
    clock: Callable[[], dt.datetime] | None = None,
    monotonic: Callable[[], float] | None = None,
) -> Generator[None]:
    """Replace the clock that judges staleness, or the one that paces rereads.

    A tool for tests, not a setting.
    """
    with _LOCK:
        saved = (_STATE.clock, _STATE.monotonic)
        if clock is not None:
            _STATE.clock = clock
        if monotonic is not None:
            _STATE.monotonic = monotonic
    try:
        yield
    finally:
        with _LOCK:
            _STATE.clock, _STATE.monotonic = saved


def active() -> bool:
    """Say whether the snapshot answers fetches here.

    It does in hosted mode with ``PYECONOMICS_SNAPSHOT_DIR`` set, outside a
    ``cache.bypass()`` block.
    """
    configured = settings()
    return (
        configured.mode == "hosted"
        and configured.snapshot_dir is not None
        and not cache.bypassed()
    )


def refuse(provider: str, operation: str) -> None:
    """Refuse an operation the snapshot cannot answer, when the snapshot is active.

    The service never asks a source itself, so a search, a description, a
    vintage list or records are refused in hosted mode with a snapshot.
    """
    if active():
        reason = f"the hosted snapshot answers fetches only, not {operation}"
        command = (
            f"pyeconomics data {operation}"
            if operation in _COMMANDS
            else "the pyeconomics Python API"
        )
        target = f"{provider}:{operation}"
        raise SnapshotMissingError(target, reason=reason, command=command)


def lookup(info: ProviderInfo, query: Query) -> Fetched | None:
    """Answer a fetch from the snapshot, or return ``None`` when it is not active.

    Raises
    ------
    SnapshotMissingError
        For a series the snapshot does not hold, a query it cannot express (more
        than one series, or a provider's own query options), or a vintage it
        did not keep.
    """
    if not active():
        return None
    target = f"{info.id}:{','.join(query.series)}"
    fields = set(type(query).model_fields)
    if len(query.series) != 1 or fields - _WINDOW_FIELDS:
        reason = "the snapshot keeps one plain series"
        raise SnapshotMissingError(target, reason=reason)
    entry = _entry(info.id, query.series[0])
    if entry is None:
        raise SnapshotMissingError(target)
    selector = query.vintage_selector
    frame = entry.frame
    if (
        entry.start is not None
        and query.end is not None
        and frame.index
        and query.end < frame.index[0]
    ):
        reason = f"the snapshot holds it from {frame.index[0].isoformat()}"
        raise SnapshotMissingError(target, reason=reason)
    if entry.vintage != "all" and selector.kind not in {
        VintageKind.LATEST,
        VintageKind.ALL,
    }:
        reason = f"the snapshot keeps its latest data, not {query.vintage}"
        raise SnapshotMissingError(target, reason=reason)
    served = codec.stale_note(_answer(entry, query), _now())
    return Fetched(served, Origin(snapshot=True), query.vintage)


def _answer(entry: codec.Entry, query: Query) -> Series | Table:
    """Select the query's vintage, cut its window and keep its most recent rows."""
    from pyeconomics.data.providers.base import tail  # noqa: PLC0415 - import cycle
    from pyeconomics.data.resolver import trim  # noqa: PLC0415 - import cycle

    selector = query.vintage_selector
    frame = entry.frame
    if isinstance(frame, Series):
        series = selector.select(frame) if entry.vintage == "all" else frame
        return tail(trim(series, query.start, query.end), query.max_observations)
    table = selector.select(frame) if entry.vintage == "all" else frame
    return tail(trim(table, query.start, query.end), query.max_observations)


# --- reading --------------------------------------------------------------------------


def _now() -> dt.datetime:
    clock = _STATE.clock
    moment = clock() if clock is not None else dt.datetime.now(dt.UTC)
    return moment.astimezone(dt.UTC)


def _ticks() -> float:
    monotonic = _STATE.monotonic
    return monotonic() if monotonic is not None else time.monotonic()


def _directory() -> Path:
    directory = settings().snapshot_dir
    if directory is None:  # pragma: no cover - active() checked it
        msg = "PYECONOMICS_SNAPSHOT_DIR is not set"
        target = "snapshot"
        raise SnapshotMissingError(target, reason=msg)
    return directory


def _read(path: Path, cap: int) -> bytes:
    """Read at most ``cap`` bytes of a file; a larger one is refused."""
    with path.open("rb") as handle:
        data = handle.read(cap + 1)
    if len(data) > cap:
        msg = "a snapshot file is larger than its cap"
        raise ResponseError(msg)
    return data


def _report(provider: str | None, problem: str) -> None:
    """Report a snapshot file that failed its checks, naming no path."""
    whose = f" of {provider}" if provider else ""
    message = f"the snapshot{whose} failed its checks and was skipped: {problem}"
    _LOG.warning("%s", message)
    warnings.warn(
        DataWarning(REJECTED_WARNING, message),
        stacklevel=2,
        skip_file_prefixes=(_PACKAGE_DIR,),
    )


def _manifest() -> codec.Manifest | None:
    """Return ``current.json``, read again once :data:`REREAD_SECONDS` have passed."""
    now = _ticks()
    if _STATE.checked_at is not None and now - _STATE.checked_at < REREAD_SECONDS:
        return _STATE.manifest
    _STATE.checked_at = now
    try:
        data = _read(_directory() / codec.CURRENT, codec.MAX_CURRENT_BYTES)
        found = codec.decode_manifest(data)
    except FileNotFoundError:
        return _STATE.manifest
    except (OSError, ResponseError) as error:
        _report(None, _first_line(error))
        return _STATE.manifest
    if _STATE.manifest is None or found != _STATE.manifest:
        _STATE.manifest = found
        names = {ref.sha256 for ref in _refs(found)} | set(_STATE.served.values())
        _STATE.objects = {k: v for k, v in _STATE.objects.items() if k in names}
    return found


def _refs(manifest: codec.Manifest) -> list[codec.ObjectRef]:
    return [
        ref
        for status in manifest.providers.values()
        for ref in (status.object, status.previous)
        if ref is not None
    ]


def _first_line(error: BaseException) -> str:
    lines = str(error).strip().splitlines()
    return lines[0] if lines else type(error).__name__


def _load(provider: str, ref: codec.ObjectRef) -> dict[str, codec.Entry] | None:
    """Return an object's entries, verified; a bad object is reported, ``None``."""
    held = _STATE.objects.get(ref.sha256)
    if held is not None:
        return held
    try:
        data = _read(_directory() / ref.name, codec.MAX_OBJECT_BYTES)
        entries = _verified(data, ref, provider)
    except (OSError, ResponseError) as error:
        _report(provider, _first_line(error))
        return None
    _STATE.objects[ref.sha256] = entries
    return entries


def _verified(
    data: bytes, ref: codec.ObjectRef, provider: str
) -> dict[str, codec.Entry]:
    """Decode an object whose SHA-256 is the one current.json names."""
    if codec.digest(data) != ref.sha256:
        msg = "its SHA-256 differs from current.json's"
        raise ResponseError(msg)
    return codec.decode_object(data, provider=provider)


def _entries(provider: str) -> dict[str, codec.Entry] | None:
    """Return the entries the provider is served from, falling back on failure."""
    manifest = _manifest()
    status = None if manifest is None else manifest.providers.get(provider)
    if status is None:
        # A provider current.json no longer names is never served, so purging
        # a source's snapshots (rule 7) takes effect at the next reread.
        _STATE.served.pop(provider, None)
        return None
    for ref in (status.object, status.previous):
        if ref is None:
            continue
        entries = _load(provider, ref)
        if entries is not None:
            _STATE.served[provider] = ref.sha256
            return entries
    last = _STATE.served.get(provider)
    return None if last is None else _STATE.objects.get(last)


def _entry(provider: str, series: str) -> codec.Entry | None:
    with _LOCK:
        entries = _entries(provider)
    return None if entries is None else entries.get(series)
