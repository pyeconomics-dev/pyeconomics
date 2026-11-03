# src/pyeconomics/data/snapshots/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The hosted data plane: daily snapshots of the originators (ADR-0013 decision 6).

The hosted service never asks a source per request. A Cloud Run job, the same
image in hosted mode, runs ``python -m pyeconomics.data.snapshots write`` once a
day and writes what the service reads; the service mounts the bucket read-only
at ``PYECONOMICS_SNAPSHOT_DIR``.

- :mod:`~pyeconomics.data.snapshots.set` computes what to keep: every
  candidate of every catalog concept (and so of every bound model's profiles)
  that a hosted-safe originator serves under terms that allow storage, with
  parameterized concepts expanded over a declared list. Never FRED, an
  aggregator, a library-only source or a storage-forbidden series.
- :mod:`~pyeconomics.data.snapshots.codec` is the layout: one gzip-compressed
  canonical-JSON object per provider and run, ``<run-id>/<provider>.json.gz``,
  holding the cache's frame codec, and ``current.json``, written last, naming
  each provider's object, its SHA-256 and each series' last observation and
  retrieval time.
- :mod:`~pyeconomics.data.snapshots.writer` is the job: it fetches the set
  through ``data.get`` inside ``cache.bypass()``, keeps a failed series' or
  provider's last good data, writes ``current.json`` last, prunes old runs and
  requests its heartbeat through the data layer's transport.
- :mod:`~pyeconomics.data.snapshots.reader` is the service's side: with the
  directory set in hosted mode it answers every series fetch after the licence
  gate and before any transport, verifies each object against ``current.json``,
  refuses a series outside the snapshot with
  :class:`~pyeconomics.data.errors.SnapshotMissingError` and marks a series not
  refreshed for two days ``stale_snapshot``.

Nothing here holds a key: the job's keys reach the providers through the key
chain, and no object, ``current.json`` or log record carries one.
"""

from __future__ import annotations

__all__: list[str] = []
