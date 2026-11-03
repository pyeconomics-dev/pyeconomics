# src/pyeconomics/data/snapshots/codec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot layout: provider objects and ``current.json`` (ADR-0013 decision 6).

This module is pure: it reads no clock, file or environment. The writer and the
reader pass it bytes and times.

A run writes, under the snapshot directory:

- ``<run-id>/<provider>.json.gz``: one gzip-compressed canonical-JSON object per
  provider (RFC 8785), holding each series as the cache's frame codec writes it
  (:meth:`~pyeconomics.data.types.Series.to_dict`), with the vintage it was
  fetched at and, for a series its source serves only by window, the first day
  its history is meant to reach. A run id is the run's start in UTC and eight random hex digits
  (``20261102T233000Z-1a2b3c4d``), so a run never overwrites another's object.
- ``current.json``, written last: the run, its completion time and, per
  provider, the object it is served from, that object's SHA-256, the object
  before it, the failure that kept an older one (a problem slug), and per series
  its last observation, its retrieval time and its own failure, if any.

Reading is strict and bounded. A compressed object larger than
:data:`MAX_OBJECT_BYTES`, or one that expands beyond
:data:`MAX_EXPANDED_BYTES`, is refused before it is parsed; JSON is parsed with
no NaN, no repeated key and a bounded depth; every frame is validated back with
``Series.from_dict`` or ``Table.from_dict`` and must belong to the provider, come
under hosted-safe terms that allow storage, and carry a retrieval time. Nothing
is pickled or evaluated, and a name in ``current.json`` is accepted only in the
exact ``<run-id>/<provider>.json.gz`` form, so it cannot leave the directory.

Examples
--------
>>> import datetime as dt
>>> run = run_id(dt.datetime(2026, 11, 2, 23, 30, tzinfo=dt.UTC), "1a2b3c4d")
>>> run, object_name(run, "treasury")
('20261102T233000Z-1a2b3c4d', '20261102T233000Z-1a2b3c4d/treasury.json.gz')
>>> parse_object_name("../etc/passwd")
Traceback (most recent call last):
    ...
pyeconomics.data.errors.ResponseError: a snapshot object name is <run-id>/<provider>.json.gz
>>> decompress(compress(b"{}"), limit=16)
b'{}'
"""  # noqa: E501 - doctest output lines cannot wrap

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import re
import zlib
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data.cache.policy import STALE_SNAPSHOT_WARNING, may_store
from pyeconomics.data.errors import ResponseError
from pyeconomics.data.types import MAX_NOTES, Series, Table

if TYPE_CHECKING:
    import builtins
    from collections.abc import Mapping

__all__ = [
    "CURRENT",
    "FORMAT",
    "MAX_CURRENT_BYTES",
    "MAX_EXPANDED_BYTES",
    "MAX_OBJECT_BYTES",
    "RETAIN",
    "RUN_ID_PATTERN",
    "STALE_AFTER",
    "Entry",
    "Manifest",
    "ObjectRef",
    "ProviderStatus",
    "SeriesStatus",
    "compress",
    "decode_manifest",
    "decode_object",
    "decompress",
    "digest",
    "encode_manifest",
    "encode_object",
    "object_name",
    "parse_object_name",
    "run_id",
    "run_started",
    "stale_note",
]

#: The layout's version, in every object and in ``current.json``.
FORMAT: Final = 1
#: The file that names what the service reads, written last.
CURRENT: Final = "current.json"
#: The largest compressed provider object read, in bytes.
MAX_OBJECT_BYTES: Final = 64 * 1024 * 1024
#: The most a provider object may expand to, in bytes.
MAX_EXPANDED_BYTES: Final = 256 * 1024 * 1024
#: The largest ``current.json`` read, in bytes.
MAX_CURRENT_BYTES: Final = 4 * 1024 * 1024
#: A series retrieved longer ago than this is stale: twice the daily cadence.
STALE_AFTER: Final = dt.timedelta(days=2)
#: How long a run that ``current.json`` no longer names is kept.
RETAIN: Final = dt.timedelta(days=30)
#: A run id: the run's start in UTC, a hyphen and eight random hex digits.
RUN_ID_PATTERN: Final = re.compile(r"(\d{8}T\d{6}Z)-[0-9a-f]{8}")

_PROVIDER: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
_OBJECT: Final = re.compile(
    r"(?P<run>\d{8}T\d{6}Z-[0-9a-f]{8})/(?P<provider>[a-z][a-z0-9_]{0,63})\.json\.gz"
)
_SHA256: Final = re.compile(r"[0-9a-f]{64}")
_SLUG: Final = re.compile(r"[a-z][a-z0-9-]{0,63}")
_VINTAGES: Final = frozenset({"latest", "all"})
_STAMP: Final = "%Y%m%dT%H%M%SZ"
_OBJECT_KEYS: Final = ("format", "provider", "run", "series")
_ENTRY_KEYS: Final = ("frame", "start", "vintage")
_MANIFEST_KEYS: Final = ("completed_at", "format", "providers", "run")
_PROVIDER_KEYS: Final = ("failure", "object", "previous", "series")
_REF_KEYS: Final = ("name", "sha256")
_SERIES_KEYS: Final = ("failure", "last_observation", "retrieved_at")


# --- names ----------------------------------------------------------------------------


def run_id(started: dt.datetime, nonce: str) -> str:
    """Return a run's id from its start and eight random hex digits."""
    text = f"{started.astimezone(dt.UTC).strftime(_STAMP)}-{nonce}"
    if not RUN_ID_PATTERN.fullmatch(text):
        msg = "a run's nonce is eight lowercase hex digits"
        raise f.fail(msg)
    return text


def run_started(run: str) -> dt.datetime:
    """Return when a run started, read from its id.

    Examples
    --------
    >>> run_started("20261102T233000Z-1a2b3c4d").isoformat()
    '2026-11-02T23:30:00+00:00'
    """
    match = RUN_ID_PATTERN.fullmatch(run)
    if match is None:
        msg = "not a snapshot run id"
        raise ResponseError(msg)
    return dt.datetime.strptime(match.group(1), _STAMP).replace(tzinfo=dt.UTC)


def object_name(run: str, provider: str) -> str:
    """Return the name of a provider's object in a run, relative to the directory."""
    name = f"{run}/{provider}.json.gz"
    parse_object_name(name)
    return name


def parse_object_name(name: object) -> tuple[str, str]:
    """Return the run and the provider an object name holds, or refuse it."""
    match = _OBJECT.fullmatch(name) if isinstance(name, str) else None
    if match is None:
        msg = "a snapshot object name is <run-id>/<provider>.json.gz"
        raise ResponseError(msg)
    return match["run"], match["provider"]


# --- bytes ----------------------------------------------------------------------------


def digest(data: bytes) -> str:
    """Return the SHA-256 of some bytes, in lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def compress(payload: bytes) -> bytes:
    """Compress with gzip, with no timestamp, so equal payloads give equal bytes."""
    return gzip.compress(payload, compresslevel=9, mtime=0)


def decompress(data: bytes, *, limit: int = MAX_EXPANDED_BYTES) -> bytes:
    """Expand gzip bytes, refusing any that would expand beyond ``limit``.

    The size is checked as the bytes expand, so a small object that would
    expand enormously is refused without ever holding the result.
    """
    if len(data) > MAX_OBJECT_BYTES:
        msg = "a snapshot object is larger than its cap"
        raise ResponseError(msg)
    inflater = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)
    try:
        expanded = inflater.decompress(data, limit + 1)
    except zlib.error:
        msg = "a snapshot object is not gzip data"
        raise ResponseError(msg) from None
    if len(expanded) > limit or inflater.unconsumed_tail:
        msg = "a snapshot object expands beyond its cap"
        raise ResponseError(msg)
    if not inflater.eof or inflater.unused_data:
        msg = "a snapshot object is not one complete gzip member"
        raise ResponseError(msg)
    return expanded


# --- provider objects -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Entry:
    """One series in a provider object: its frame and the vintage it was fetched at.

    ``vintage`` is ``latest``, or ``all`` for a source that keeps vintages, from
    which a reader selects what a query asks for. ``start`` is set for a series
    its source serves only by window: the day its history is meant to reach,
    which the job fills a year at a time.
    """

    frame: Series | Table
    vintage: str = "latest"
    start: dt.date | None = None


def _checked_frame(frame: Series | Table, provider: str) -> Series | Table:
    """Refuse a frame that is not the provider's, hosted-safe and storable."""
    meta = frame.meta
    if meta.provider != provider:
        msg = f"a snapshot of {provider} holds another provider's frame"
        raise ResponseError(msg, provider=provider)
    if meta.terms.licence is not LicenceClass.HOSTED_SAFE or not may_store(meta.terms):
        msg = f"a snapshot of {provider} holds data its terms keep out of the snapshot"
        raise ResponseError(msg, provider=provider)
    if meta.retrieved_at is None:
        msg = f"a snapshot of {provider} holds a frame without a retrieval time"
        raise ResponseError(msg, provider=provider)
    return frame


def encode_object(provider: str, run: str, entries: Mapping[str, Entry]) -> bytes:
    """Return a provider object's compressed bytes.

    Each frame is checked first: it must be the provider's, come under
    hosted-safe terms that allow storage and carry its retrieval time, so
    nothing a source's terms keep out of the snapshot is ever written.
    """
    series: dict[str, object] = {}
    for key, entry in sorted(entries.items()):
        if entry.vintage not in _VINTAGES:
            msg = f"a snapshot keeps the latest or every vintage, not {entry.vintage}"
            raise f.fail(msg)
        _checked_frame(entry.frame, provider)
        series[key] = {
            "frame": entry.frame.to_dict(),
            "start": None if entry.start is None else entry.start.isoformat(),
            "vintage": entry.vintage,
        }
    document = {"format": FORMAT, "provider": provider, "run": run, "series": series}
    return compress(canonical_json(document))


def decode_object(data: bytes, *, provider: str) -> dict[str, Entry]:
    """Read a provider object back into its entries, validating every frame.

    Raises
    ------
    ResponseError
        If the bytes are not a well-formed object of this provider.
    """
    try:
        document = f.mapping(
            f.load_json(decompress(data)), "a snapshot object", _OBJECT_KEYS
        )
        if document["format"] != FORMAT or document["provider"] != provider:
            msg = f"the snapshot object is not a format-{FORMAT} object of {provider}"
            raise ResponseError(msg, provider=provider)
        run_started(str(document["run"]))
        series = document["series"]
        if not isinstance(series, dict):
            msg = "a snapshot object's series is an object"
            raise ResponseError(msg, provider=provider)
        return {
            f.text(key, "a snapshot series id"): _entry(value, provider)
            for key, value in series.items()
        }
    except (PyeconomicsError, ValueError, TypeError, RecursionError) as error:
        if isinstance(error, ResponseError):
            raise
        message = f"the snapshot object of {provider} is malformed"
    raise ResponseError(message, provider=provider)


def _entry(value: object, provider: str) -> Entry:
    fields = f.mapping(value, "a snapshot entry", _ENTRY_KEYS)
    vintage = fields["vintage"]
    if vintage not in _VINTAGES:
        msg = "a snapshot entry's vintage is latest or all"
        raise ResponseError(msg, provider=provider)
    frame_data = fields["frame"]
    kind = frame_data.get("type") if isinstance(frame_data, dict) else None
    frame: Series | Table
    if kind == "series":
        frame = Series.from_dict(frame_data)
    elif kind == "table":
        frame = Table.from_dict(frame_data)
    else:
        msg = "a snapshot entry's frame is a series or a table"
        raise ResponseError(msg, provider=provider)
    start = fields["start"]
    return Entry(
        _checked_frame(frame, provider),
        str(vintage),
        None if start is None else f.parse_day(start, "a snapshot entry's start"),
    )


def stale_note(frame: Series | Table, now: dt.datetime) -> Series | Table:
    """Mark a frame ``stale_snapshot`` when it was retrieved too long ago.

    The note's code becomes the record's warning code
    (:data:`~pyeconomics.data.cache.policy.NOTE_WARNINGS`). A fresh frame, or
    one already marked, is returned unchanged.
    """
    retrieved = frame.meta.retrieved_at
    if retrieved is None or now - retrieved <= STALE_AFTER:
        return frame
    codes = {note.partition(": ")[0] for note in frame.meta.notes}
    if STALE_SNAPSHOT_WARNING in codes:
        return frame
    note = (
        f"{STALE_SNAPSHOT_WARNING}: retrieved {retrieved.date().isoformat()}, more "
        f"than {STALE_AFTER.days} days before it was served"
    )
    notes = (note, *frame.meta.notes)[:MAX_NOTES]
    if isinstance(frame, Series):
        return replace(frame, meta=replace(frame.meta, notes=notes))
    return replace(frame, meta=replace(frame.meta, notes=notes))


# --- current.json ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class ObjectRef:
    """An object ``current.json`` names: its name and its SHA-256."""

    name: str
    sha256: str

    def __post_init__(self) -> None:
        """Accept only a name in the layout's form and a SHA-256 in hex."""
        parse_object_name(self.name)
        if not _SHA256.fullmatch(self.sha256):
            msg = "a snapshot object's SHA-256 is 64 lowercase hex digits"
            raise ResponseError(msg)

    def to_dict(self) -> dict[str, object]:
        """Return the reference as JSON-ready values."""
        return {"name": self.name, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, data: object) -> ObjectRef | None:
        """Read a reference, or ``None`` for JSON ``null``."""
        if data is None:
            return None
        fields = f.mapping(data, "a snapshot object reference", _REF_KEYS)
        return cls(
            name=f.text(fields["name"], "a snapshot object name"),
            sha256=f.text(fields["sha256"], "a snapshot object's SHA-256"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesStatus:
    """One series in ``current.json``: its last observation, retrieval and failure."""

    last_observation: dt.date | None = None
    retrieved_at: dt.datetime | None = None
    failure: str | None = None
    """The problem slug of the latest run's failure to fetch it, if it failed."""

    def to_dict(self) -> dict[str, object]:
        """Return the status as JSON-ready values."""
        return {
            "failure": self.failure,
            "last_observation": None
            if self.last_observation is None
            else self.last_observation.isoformat(),
            "retrieved_at": None
            if self.retrieved_at is None
            else self.retrieved_at.astimezone(dt.UTC).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: object) -> SeriesStatus:
        """Read a status back, refusing anything else."""
        fields = f.mapping(data, "a snapshot series status", _SERIES_KEYS)
        last, when = fields["last_observation"], fields["retrieved_at"]
        return cls(
            last_observation=None if last is None else f.parse_day(last, "a day"),
            retrieved_at=None if when is None else _instant(when),
            failure=_slug(fields["failure"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderStatus:
    """One provider in ``current.json``: the object served, and how it got there."""

    object: ObjectRef | None
    """The object the provider is served from; ``None`` if it never succeeded."""
    previous: ObjectRef | None = None
    """The object served before, which a reader falls back to."""
    failure: str | None = None
    """The problem slug that kept an older object, when the provider failed."""
    series: Mapping[str, SeriesStatus] = field(default_factory=dict)

    def to_dict(self) -> dict[str, builtins.object]:
        """Return the status as JSON-ready values."""
        return {
            "failure": self.failure,
            "object": None if self.object is None else self.object.to_dict(),
            "previous": None if self.previous is None else self.previous.to_dict(),
            "series": {k: v.to_dict() for k, v in sorted(self.series.items())},
        }

    @classmethod
    def from_dict(cls, data: builtins.object) -> ProviderStatus:
        """Read a status back, refusing anything else."""
        fields = f.mapping(data, "a snapshot provider status", _PROVIDER_KEYS)
        series = fields["series"]
        if not isinstance(series, dict):
            msg = "a snapshot provider's series is an object"
            raise ResponseError(msg)
        return cls(
            object=ObjectRef.from_dict(fields["object"]),
            previous=ObjectRef.from_dict(fields["previous"]),
            failure=_slug(fields["failure"]),
            series={
                f.text(key, "a snapshot series id"): SeriesStatus.from_dict(value)
                for key, value in series.items()
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Manifest:
    """``current.json``: the run, when it completed and every provider's status."""

    run: str
    completed_at: dt.datetime
    providers: Mapping[str, ProviderStatus]

    def names(self) -> frozenset[str]:
        """Return every object the manifest names, served or fallen back to."""
        return frozenset(
            ref.name
            for status in self.providers.values()
            for ref in (status.object, status.previous)
            if ref is not None
        )


def encode_manifest(manifest: Manifest) -> bytes:
    """Return ``current.json``'s bytes: canonical JSON, uncompressed."""
    return canonical_json(
        {
            "completed_at": manifest.completed_at.astimezone(dt.UTC).isoformat(),
            "format": FORMAT,
            "providers": {
                provider: status.to_dict()
                for provider, status in sorted(manifest.providers.items())
            },
            "run": manifest.run,
        }
    )


def decode_manifest(data: bytes) -> Manifest:
    """Read ``current.json`` strictly.

    Raises
    ------
    ResponseError
        If it is too large, not this layout, or names an object outside it.
    """
    if len(data) > MAX_CURRENT_BYTES:
        msg = "the snapshot's current.json is larger than its cap"
        raise ResponseError(msg)
    try:
        fields = f.mapping(f.load_json(data), "current.json", _MANIFEST_KEYS)
        if fields["format"] != FORMAT:
            msg = f"the snapshot's current.json is not format {FORMAT}"
            raise ResponseError(msg)
        providers = fields["providers"]
        if not isinstance(providers, dict):
            msg = "current.json's providers is an object"
            raise ResponseError(msg)
        run = str(fields["run"])
        run_started(run)
        statuses = {}
        for provider, value in providers.items():
            if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
                msg = "current.json names a provider that is not a provider id"
                raise ResponseError(msg)
            status = ProviderStatus.from_dict(value)
            for ref in (status.object, status.previous):
                if ref is not None and parse_object_name(ref.name)[1] != provider:
                    msg = f"current.json names another provider's object for {provider}"
                    raise ResponseError(msg)
            statuses[provider] = status
        return Manifest(
            run=run, completed_at=_instant(fields["completed_at"]), providers=statuses
        )
    except (PyeconomicsError, ValueError, TypeError, RecursionError) as error:
        if isinstance(error, ResponseError):
            raise
        message = "the snapshot's current.json is malformed"
    raise ResponseError(message)


def _instant(value: object) -> dt.datetime:
    if not isinstance(value, str):
        msg = "a time is ISO 8601 text"
        raise ResponseError(msg)
    moment = dt.datetime.fromisoformat(value)
    if moment.tzinfo is None:
        msg = "a time has a zone"
        raise ResponseError(msg)
    return moment.astimezone(dt.UTC)


def _slug(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        msg = "a failure is a problem slug"
        raise ResponseError(msg)
    return value
