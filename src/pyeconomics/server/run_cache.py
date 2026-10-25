# src/pyeconomics/server/run_cache.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The GET run cache, entity tags and ``Cache-Control`` (ADR-0012 decision 12).

A run's ``GET`` form is cacheable; its ``POST`` form, which may carry values
from a user's file, is processed in memory and never cached (ADR-0005), and
neither is a problem. :class:`RunCache` keeps answered ``GET`` runs in the
server's memory, bounded by entries and by bytes, least recently used first out,
each for its ``max-age``:

- a run that reads no data: :data:`DATA_FREE_CONTROL`, a day, since the result
  is a function of the model's version, the package's version and the inputs,
  all in the key;
- a bound run whose every data record may be stored (hosted-safe, under terms
  that allow storage): :data:`BOUND_CONTROL`, five minutes, since its data can
  be revised. The data records are not known before the run, so the key holds
  what selects them (the bind request) and an entry lives no longer than this;
- a bound run that read anything else (FRED in local mode, say) is answered
  with :data:`NO_STORE` and kept nowhere.

Each cacheable answer carries the weak entity tag ``W/"<result_sha256>"``
(:func:`~pyeconomics.surfaces.envelope.etag`), and a request whose
``If-None-Match`` names it is answered ``304 Not Modified`` (:func:`etag_matches`
uses the weak comparison RFC 9110 requires there).

Examples
--------
>>> cache = RunCache(max_entries=2, max_bytes=1_000, clock=lambda: 0.0)
>>> entry = Entry(body=b"{}", media_type="application/json", disposition=None,
...     etag='W/"ab"', control=DATA_FREE_CONTROL, stored=0.0)
>>> cache.put("k", entry)
>>> cache.get("k") is entry, len(cache), cache.size
(True, 1, 2)
>>> etag_matches('W/"ab", "cd"', 'W/"ab"'), etag_matches('"ab"', 'W/"ab"')
(True, True)
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pyeconomics import __version__
from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = [
    "BOUND_CONTROL",
    "DATA_FREE_CONTROL",
    "DEFAULT_CACHE_BYTES",
    "DEFAULT_CACHE_ENTRIES",
    "NO_STORE",
    "Entry",
    "RunCache",
    "etag_matches",
    "max_age",
    "run_key",
]

#: ``Cache-Control`` of a run that reads no data: public, for a day.
DATA_FREE_CONTROL: Final = "public, max-age=86400"
#: ``Cache-Control`` of a bound run whose data may be stored: public, five minutes.
BOUND_CONTROL: Final = "public, max-age=300"
#: ``Cache-Control`` of a POST run, a problem, and a run whose data may not be stored.
NO_STORE: Final = "no-store"
#: How many runs the cache keeps by default.
DEFAULT_CACHE_ENTRIES: Final = 1_024
#: How many bytes of bodies the cache keeps by default: 64 MiB.
DEFAULT_CACHE_BYTES: Final = 64 * 1024 * 1024

_MAX_AGE: Final = re.compile(r"max-age=(\d+)")
_TAG: Final = re.compile(r'\s*(?:W/)?("[^"]*")\s*(?:,|$)')


def max_age(control: str) -> int:
    """Return the seconds a ``Cache-Control`` value lets an answer be reused."""
    found = _MAX_AGE.search(control)
    return int(found.group(1)) if found else 0


@dataclass(frozen=True, slots=True, kw_only=True)
class Entry:
    """One answered GET run: its bytes and the headers it is answered with."""

    body: bytes
    media_type: str
    disposition: str | None
    etag: str
    control: str
    stored: float
    """When it was stored, on the cache's clock."""


def run_key(
    model_id: str,
    model_version: int,
    inputs: Mapping[str, object],
    bind: Mapping[str, object] | None,
    export_format: str,
) -> str:
    """Return a GET run's cache key: a digest of all that selects its answer.

    That is the model's id and version, the package's version, the inputs'
    canonical JSON, the bind request (which selects the data) and the format.
    """
    document = {
        "bind": None if bind is None else dict(bind),
        "format": export_format,
        "inputs": dict(inputs),
        "model": model_id,
        "package": __version__,
        "version": model_version,
    }
    return hashlib.sha256(canonical_json(document)).hexdigest()


class RunCache:
    """Answered GET runs in memory, bounded by entries and bytes.

    Parameters
    ----------
    max_entries
        The most runs kept.
    max_bytes
        The most bytes of bodies kept; a body larger than this is never kept.
    clock
        Seconds from any fixed point; :func:`time.monotonic` by default.
    """

    def __init__(
        self,
        *,
        max_entries: int,
        max_bytes: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._entries: OrderedDict[str, Entry] = OrderedDict()
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._clock = clock
        self._size = 0

    def __len__(self) -> int:
        """Return how many runs the cache holds."""
        return len(self._entries)

    @property
    def size(self) -> int:
        """The bytes of bodies the cache holds."""
        return self._size

    def now(self) -> float:
        """Return the cache's clock."""
        return self._clock()

    def age(self, entry: Entry) -> int:
        """Return how many whole seconds ago an entry was stored."""
        return max(int(self._clock() - entry.stored), 0)

    def get(self, key: str) -> Entry | None:
        """Return a fresh entry, marking it recently used; drop a stale one."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._clock() - entry.stored >= max_age(entry.control):
            self._drop(key)
            return None
        self._entries.move_to_end(key)
        return entry

    def put(self, key: str, entry: Entry) -> None:
        """Keep an entry, evicting the least recently used past either bound."""
        if len(entry.body) > self._max_bytes or self._max_entries < 1:
            return
        if key in self._entries:
            self._drop(key)
        self._entries[key] = entry
        self._size += len(entry.body)
        while len(self._entries) > self._max_entries or self._size > self._max_bytes:
            self._drop(next(iter(self._entries)))

    def _drop(self, key: str) -> None:
        entry = self._entries.pop(key)
        self._size -= len(entry.body)


def etag_matches(header: str | None, etag: str) -> bool:
    """Whether an ``If-None-Match`` value names an entity tag, compared weakly.

    ``*`` matches any tag; otherwise each listed tag is compared without its
    ``W/`` prefix (RFC 9110, section 13.1.2). A value that is not a list of
    entity tags matches nothing.
    """
    if header is None:
        return False
    text = header.strip()
    if text == "*":
        return True
    wanted = etag.removeprefix("W/")
    position = 0
    while position < len(text):
        found = _TAG.match(text, position)
        if found is None or found.end() == position:
            return False
        if found.group(1) == wanted:
            return True
        position = found.end()
    return False
