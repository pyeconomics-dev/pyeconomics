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
(:mod:`~pyeconomics.data.redaction`). Only the configuration and credential
modules read files or the environment, and later the transport and the cache
(ADR-0011 decision 1); nothing opens a socket yet, and nothing reads the
clock.

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
from pyeconomics.data.terms import TERMS_MAX_AGE_MONTHS, CachePolicy, Terms
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
    "CachePolicy",
    "ColumnMeta",
    "ConfigError",
    "CredentialError",
    "DataError",
    "DataSource",
    "DataWarning",
    "DateConvention",
    "KeySource",
    "LicenceClass",
    "LicenceError",
    "LlmUse",
    "ObservationFrequency",
    "OfflineError",
    "ProviderNotFoundError",
    "RateLimitError",
    "RealtimePeriod",
    "ResponseError",
    "SeasonalAdjustment",
    "Secret",
    "Series",
    "SeriesMeta",
    "SeriesNotFoundError",
    "Settings",
    "Table",
    "TableMeta",
    "Terms",
    "TransportError",
    "UnitRecord",
    "Vintage",
    "VintageKind",
    "Weekday",
    "configure",
    "has_key",
    "key_variable",
    "resolve_key",
    "settings",
]
