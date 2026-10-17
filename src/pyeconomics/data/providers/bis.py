# src/pyeconomics/data/providers/bis.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bank for International Settlements: official SDMX series.

Use agency/flow/key ids; search returns dataflows, whose structures define
ordered dimension codes. Source terms checked 2026-10-16. Dataset restrictions
travel with series metadata and are enforced by hosted mode.
"""

from __future__ import annotations

import datetime as dt
from typing import ClassVar

from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.providers._sdmx import SdmxProvider, cases
from pyeconomics.data.providers.base import (
    Capability,
    Platform,
    ProviderInfo,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms

__all__ = ["Bis"]

TERMS = Terms(
    licence=LicenceClass("hosted-safe"),
    terms_url="https://data.bis.org/help/legal",
    checked=dt.date(2026, 10, 16),
    attribution="Source: Bank for International Settlements.",
    notice=(
        "their inclusion in the publication or product will not result in "
        "any additional charge to subscribers or other users;"
    ),
    llm_use=LlmUse("allowed"),
    cache=CachePolicy.ALLOWED,
)


class Bis(SdmxProvider):
    """Bank for International Settlements's official statistical service."""

    info = ProviderInfo(
        id="bis",
        name="Bank for International Settlements",
        homepage="https://stats.bis.org",
        terms=TERMS,
        hosts=("stats.bis.org",),
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
        extra="sdmx",
        platforms=(Platform.LINUX, Platform.MACOS, Platform.WINDOWS),
        rate_limits=(RateLimit(requests=1, per="second"),),
        max_response_bytes=20_000_000,
    )
    root = "/api/v1"
    search_agency = "BIS"
    references = "all"
    cases: ClassVar = cases("BIS/WS_CBPOL/D.US", "policy")
