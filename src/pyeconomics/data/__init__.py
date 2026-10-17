# src/pyeconomics/data/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data layer: licence-aware data for pyeconomics models (ADR-0011).

This package holds the value types every provider returns and every later
layer stores, binds and records: :class:`Series` and :class:`Table` with their
metadata (:mod:`~pyeconomics.data.types`), a source's :class:`Terms` and
:class:`CachePolicy` (:mod:`~pyeconomics.data.terms`), the :class:`Vintage`
selector (:mod:`~pyeconomics.data.vintage`) and the error taxonomy
(:mod:`~pyeconomics.data.errors`). It re-exports the provenance vocabulary that
lives in :mod:`pyeconomics.core.provenance`, because core never imports this
package: :class:`DataSource`, :class:`RealtimePeriod`, :class:`LicenceClass`
and :class:`LlmUse`.

Keys and settings (Phase 3 Step 3): :func:`resolve_key` reads a provider's
key through the chain of ADR-0011 decision 12 and returns it as a
:class:`Secret`; :func:`has_key` checks for one without reading it; and
:func:`settings` and :func:`configure` read and override the layered
``pyeconomics.toml`` (:mod:`~pyeconomics.data.config`). Every registered key
is scrubbed from log records, URLs, headers and messages
(:mod:`~pyeconomics.data.redaction`).

The cache (Phase 3 Step 5): :mod:`pyeconomics.data.cache` keeps what a source's
terms allow in one SQLite file and serves it within its time-to-live; a source or
series whose terms forbid storage has no cache path at all. Offline mode
(``configure(offline=True)``) serves the cache only and raises
:class:`OfflineError` on a miss. :meth:`DataProvider.fetch_with_origin` returns a
:class:`Fetched`, the frame with an :class:`Origin` and a ``DataSource`` record.

Providers (Phase 3 Step 4): a source is a :class:`DataProvider` subclass with a
:class:`ProviderInfo`, registered through the ``pyeconomics.providers``
entry-point group and found with :mod:`pyeconomics.data.registry`. Its
:class:`Request` values go through a :class:`Transport`
(:mod:`~pyeconomics.data.transport`): the one code that opens a socket, reveals
a key and builds a URL. :class:`Mode` selects library or hosted mode, and
hosted mode refuses every source not classed hosted-safe or user-supplied.
Only the configuration, credential and transport modules read files, the
environment, the network or the clock (ADR-0011 decision 1). Importing this
package imports neither urllib3 nor truststore.

Examples
--------
>>> import pyeconomics.data as data
>>> data.LicenceClass("hosted-safe").hosted_allowed
True
>>> data.ObservationFrequency.QUARTERLY.pandas_alias()
'QE-DEC'

"""

from pyeconomics.core.provenance import (
    DATA_DATE_BOUNDS,
    DataSource,
    LicenceClass,
    LlmUse,
    RealtimePeriod,
)
from pyeconomics.data import cache, registry
from pyeconomics.data.cache.policy import Fetched, Origin
from pyeconomics.data.config import Settings, configure, settings
from pyeconomics.data.credentials import (
    KeySource,
    Secret,
    has_key,
    key_variable,
    resolve_key,
)
from pyeconomics.data.errors import (
    ConfigError,
    CredentialError,
    DataError,
    DataWarning,
    LicenceError,
    OfflineError,
    ProviderNotFoundError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
)
from pyeconomics.data.modes import Mode, current_mode, require_allowed
from pyeconomics.data.providers import (
    Access,
    Authentication,
    AuthKind,
    Capability,
    Case,
    DataProvider,
    KeyPlacement,
    KeySlot,
    Platform,
    ProviderInfo,
    Query,
    RateLimit,
    SearchHit,
)
from pyeconomics.data.records import FigiMapping, Filing, Records
from pyeconomics.data.terms import TERMS_MAX_AGE_MONTHS, CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, Transport
from pyeconomics.data.types import (
    MAX_COLUMNS,
    MAX_OBSERVATIONS,
    ColumnMeta,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    TableMeta,
    UnitRecord,
    Weekday,
)
from pyeconomics.data.vintage import Vintage, VintageKind

__all__ = [
    "DATA_DATE_BOUNDS",
    "MAX_COLUMNS",
    "MAX_OBSERVATIONS",
    "TERMS_MAX_AGE_MONTHS",
    "Access",
    "AuthKind",
    "Authentication",
    "CachePolicy",
    "Capability",
    "Case",
    "ColumnMeta",
    "ConfigError",
    "CredentialError",
    "DataError",
    "DataProvider",
    "DataSource",
    "DataWarning",
    "DateConvention",
    "Fetched",
    "FigiMapping",
    "Filing",
    "KeyPlacement",
    "KeySlot",
    "KeySource",
    "LicenceClass",
    "LicenceError",
    "LlmUse",
    "Mode",
    "ObservationFrequency",
    "OfflineError",
    "Origin",
    "Platform",
    "ProviderInfo",
    "ProviderNotFoundError",
    "Query",
    "RateLimit",
    "RateLimitError",
    "RealtimePeriod",
    "Records",
    "Request",
    "Response",
    "ResponseError",
    "SearchHit",
    "SeasonalAdjustment",
    "Secret",
    "Series",
    "SeriesMeta",
    "SeriesNotFoundError",
    "Settings",
    "Table",
    "TableMeta",
    "Terms",
    "Transport",
    "TransportError",
    "UnitRecord",
    "Vintage",
    "VintageKind",
    "Weekday",
    "cache",
    "configure",
    "current_mode",
    "has_key",
    "key_variable",
    "registry",
    "require_allowed",
    "resolve_key",
    "settings",
]
