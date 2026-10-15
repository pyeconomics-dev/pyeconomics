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

Nothing here opens a socket, reads a file or the environment, or reads the
clock. Later Phase 3 steps add credentials and configuration, providers and
their transport, the cache, the catalog and bindings; only the transport,
cache, configuration and credential modules do I/O (ADR-0011 decision 1).

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
from pyeconomics.data.errors import (
    ConfigError,
    CredentialError,
    DataError,
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
    "DateConvention",
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
    "Series",
    "SeriesMeta",
    "SeriesNotFoundError",
    "Table",
    "TableMeta",
    "Terms",
    "TransportError",
    "UnitRecord",
    "Vintage",
    "VintageKind",
    "Weekday",
]
