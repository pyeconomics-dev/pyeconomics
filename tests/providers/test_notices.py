# tests/providers/test_notices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A reviewed diff for every notice (ADR-0005's Confirmation).

"A test per provider checks the exact wording": ``NOTICES`` pins, per provider, the
exact attribution, the exact required notice (or ``None``) and the terms page, each
quoted from the terms page on the provider's terms-checked date. A change to a
notice is then a diff someone reads. The suite fails for a registered provider
without a row, and for a row without a provider. Every provider step adds its
providers' rows.

The toys' rows pin the toys' own invented wording.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import pytest
from toys import ToyJson, ToyVintage

from pyeconomics.data import DataProvider, registry

if TYPE_CHECKING:
    from collections.abc import Iterable


class Row(NamedTuple):
    """The wording pinned for one provider."""

    attribution: str
    notice: str | None
    terms_url: str
    checked: dt.date


NOTICES: dict[str, Row] = {
    "ken_french": Row(
        attribution="Source: Eugene F. Fama and Kenneth R. French, Data Library.",
        notice="Copyright Eugene F. Fama and Kenneth R. French",
        terms_url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        checked=dt.date(2026, 10, 17),
    ),
    "shiller": Row(
        attribution="Source: Robert J. Shiller.",
        notice=(
            "The data and CAPE Ratio on this spreadsheet were "
            "developed by Robert J. Shiller using various public sources."
        ),
        terms_url="https://shillerdata.com/",
        checked=dt.date(2026, 10, 17),
    ),
    "damodaran": Row(
        attribution="Source: Aswath Damodaran, Damodaran Online.",
        notice=(
            "The second is that you acknowledge the "
            "parentage when you used the data from this site."
        ),
        terms_url="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/guide.html",
        checked=dt.date(2026, 10, 17),
    ),
    "aqr": Row(
        attribution="Source: AQR Capital Management, LLC.",
        notice="PAST PERFORMANCE DOES NOT GUARANTEE FUTURE RESULTS.",
        terms_url="https://www.aqr.com/Terms-of-Use",
        checked=dt.date(2026, 10, 17),
    ),
    "hou_xue_zhang": Row(
        attribution=(
            "Source: Kewei Hou, Haitao Mo, Chen Xue and Lu Zhang, global-q.org."
        ),
        notice=None,
        terms_url="https://global-q.org/factors.html",
        checked=dt.date(2026, 10, 17),
    ),
    "jkp": Row(
        attribution="Source: Jensen, Kelly and Pedersen (2023), Global Factor Data.",
        notice="Creative Commons Attribution-NonCommercial 4.0 International",
        terms_url="https://jkpfactors.com/",
        checked=dt.date(2026, 10, 17),
    ),
    "open_source_asset_pricing": Row(
        attribution=(
            "Source: Andrew Y. Chen and Tom Zimmermann, Open Source Asset Pricing."
        ),
        notice="Data (October 2025 Release)",
        terms_url="https://www.openassetpricing.com/data/",
        checked=dt.date(2026, 10, 17),
    ),
    "cboe": Row(
        attribution="Source: Cboe Global Markets, VIX Index.",
        notice="All Rights Reserved.",
        terms_url="https://www.cboe.com/terms",
        checked=dt.date(2026, 10, 17),
    ),
    "coin_metrics": Row(
        attribution="Source: Coin Metrics Community Network Data.",
        notice="Creative Commons Attribution-NonCommercial 4.0 International",
        terms_url="https://github.com/coinmetrics/data/blob/master/LICENSE",
        checked=dt.date(2026, 10, 17),
    ),
    "yfinance": Row(
        attribution="Source: Yahoo Finance, through yfinance.",
        notice="the Yahoo! finance API is intended for personal use only.",
        terms_url="https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
        checked=dt.date(2026, 10, 17),
    ),
    "treasury": Row(
        attribution="Source: U.S. Department of the Treasury.",
        notice=None,
        terms_url="https://home.treasury.gov/footer/privacy-act",
        checked=dt.date(2026, 10, 16),
    ),
    "fed_board": Row(
        attribution="Source: Board of Governors of the Federal Reserve System.",
        notice=None,
        terms_url="https://www.federalreserve.gov/disclaimer.htm",
        checked=dt.date(2026, 10, 16),
    ),
    "nyfed": Row(
        attribution="Source: Federal Reserve Bank of New York.",
        notice=(
            "\u00a9 2026 Federal Reserve Bank of New York. "
            "Content from the New York Fed subject to the Terms of Use "
            "at newyorkfed.org."
        ),
        terms_url="https://www.newyorkfed.org/privacy/termsofuse.html",
        checked=dt.date(2026, 10, 16),
    ),
    "openfigi": Row(
        attribution="Source: Bloomberg, OpenFIGI.",
        notice=None,
        terms_url="https://www.openfigi.com/docs/terms-of-service",
        checked=dt.date(2026, 10, 16),
    ),
    "sec_edgar": Row(
        attribution="Source: U.S. Securities and Exchange Commission, EDGAR.",
        notice=None,
        terms_url="https://www.sec.gov/about/privacy-information",
        checked=dt.date(2026, 10, 20),
    ),
    "philadelphia_fed": Row(
        attribution=(
            "Source: Federal Reserve Bank of Philadelphia. Croushore and "
            "Stark (2001), A Real-Time Data Set for Macroeconomists."
        ),
        notice=(
            "The content provided on this website may be used for informa"
            "tional, educational, and research purposes only."
        ),
        terms_url="https://www.philadelphiafed.org/about-us/privacy-notice",
        checked=dt.date(2026, 10, 17),
    ),
    "atlanta_fed": Row(
        attribution="Source: Federal Reserve Bank of Atlanta, GDPNow.",
        notice=(
            "Permission is granted to reproduce for personal and educational use only."
        ),
        terms_url="https://www.atlantafed.org/research-and-data/data/gdpnow",
        checked=dt.date(2026, 10, 17),
    ),
    "cleveland_fed": Row(
        attribution="Source: Federal Reserve Bank of Cleveland.",
        notice=(
            "The information is used for noncommercial, personal, or educ"
            "ational purposes only (i.e., not for private gain)"
        ),
        terms_url="https://www.clevelandfed.org/privacy",
        checked=dt.date(2026, 10, 17),
    ),
    "cbo": Row(
        attribution="Source: Congressional Budget Office.",
        notice=(
            "Government documents are in the public domain and are not pr"
            "otected by copyright law."
        ),
        terms_url="https://www.cbo.gov/about/privacy",
        checked=dt.date(2026, 10, 17),
    ),
    "penn_world_table": Row(
        attribution=(
            "Penn World Table 11.0 by Robert C. Feenstra, Robert Inklaar "
            "and Marcel P. Timmer."
        ),
        notice=(
            "Feenstra, Robert C., Robert Inklaar and Marcel P. Timmer (20"
            '15), "The Next Generation of the Penn World Table" American '
            "Economic Review, 105(10), 3150-3182, available for download "
            "at www.ggdc.net/pwt"
        ),
        terms_url="https://www.rug.nl/ggdc/productivity/pwt/",
        checked=dt.date(2026, 10, 17),
    ),
    "bis": Row(
        attribution="Source: Bank for International Settlements.",
        notice=(
            "their inclusion in the publication or product will not "
            "result in any additional charge to subscribers or other"
            " users;"
        ),
        terms_url="https://data.bis.org/help/legal",
        checked=dt.date(2026, 10, 16),
    ),
    "dbnomics": Row(
        attribution="Source: DBnomics and the original data provider.",
        notice=(
            "Data distributed by DBnomics is subject to the same "
            "license and terms of use as its original source "
            "provider."
        ),
        terms_url="https://db.nomics.world/about",
        checked=dt.date(2026, 10, 16),
    ),
    "ecb": Row(
        attribution="Source: European Central Bank.",
        notice="the information may be obtained free of charge through this website.",
        terms_url=(
            "https://www.ecb.europa.eu/services/using-our-site/disclaimer"
            "/html/index.en.html"
        ),
        checked=dt.date(2026, 10, 16),
    ),
    "eurostat": Row(
        attribution="Source: Eurostat.",
        notice=(
            "Source: [digital object identifier (DOI) number of the "
            "Eurostat dataset], [access date]"
        ),
        terms_url="https://ec.europa.eu/eurostat/help/copyright-notice",
        checked=dt.date(2026, 10, 16),
    ),
    "imf": Row(
        attribution="Source: International Monetary Fund.",
        notice=(
            "For any potential commercial reuse of IMF Data, email "
            "copyright@imf.org to request permission."
        ),
        terms_url="https://www.imf.org/en/about/copyright-and-terms",
        checked=dt.date(2026, 10, 16),
    ),
    "oecd": Row(
        attribution="Source: OECD.",
        notice=(
            "OECD (year), (dataset name),(data source) DOI or URL (accessed on (date))."
        ),
        terms_url="https://www.oecd.org/en/about/terms-conditions.html",
        checked=dt.date(2026, 10, 16),
    ),
    "world_bank": Row(
        attribution="The World Bank: Dataset name: Data source (if known).",
        notice=None,
        terms_url="https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
        checked=dt.date(2026, 10, 16),
    ),
    # FRED API terms of use, Requirements (a), read 2026-10-15.
    "fred": Row(
        attribution="Source: Federal Reserve Bank of St. Louis, FRED®.",
        notice=(
            "This product uses the FRED® API but is not endorsed or certified by "
            "the Federal Reserve Bank of St. Louis."
        ),
        terms_url="https://fred.stlouisfed.org/legal/",
        checked=dt.date(2026, 10, 15),
    ),
    # BLS API terms of service, "Citing Data", read 2026-10-15; each frame adds
    # the access date the same section asks users to cite.
    "bls": Row(
        attribution="Source: U.S. Bureau of Labor Statistics.",
        notice=(
            "BLS.gov cannot vouch for the data or analyses derived from these data "
            "after the data have been retrieved from BLS.gov."
        ),
        terms_url="https://www.bls.gov/developers/termsOfService.htm",
        checked=dt.date(2026, 10, 15),
    ),
    # BEA API terms of service, "Attribution", read 2026-10-15.
    "bea": Row(
        attribution="Source: U.S. Bureau of Economic Analysis.",
        notice=(
            "This product uses the Bureau of Economic Analysis (BEA) Data API but "
            "is not endorsed or certified by BEA."
        ),
        terms_url="https://apps.bea.gov/API/_pdf/bea_api_tos.pdf",
        checked=dt.date(2026, 10, 15),
    ),
    # Census Data API terms of service, "Attribution", read 2026-10-15.
    "census": Row(
        attribution="Source: U.S. Census Bureau.",
        notice=(
            "This product uses the Census Bureau Data API but is not endorsed or "
            "certified by the Census Bureau."
        ),
        terms_url="https://www.census.gov/data/developers/about/terms-of-service.html",
        checked=dt.date(2026, 10, 15),
    ),
    "toy_json": Row(
        attribution="Source: Toy JSON Agency (a test fixture with invented numbers).",
        notice=(
            "This product uses the Toy JSON API but is not endorsed by Toy JSON Agency."
        ),
        terms_url="https://www.toyjson.example.org/terms",
        checked=dt.date(2026, 10, 15),
    ),
    "toy_vintage": Row(
        attribution="Source: Toy Vintage Bank (a test fixture with invented numbers).",
        notice=None,
        terms_url="https://www.toyvintage.example.org/terms",
        checked=dt.date(2026, 10, 15),
    ),
}

PROVIDERS: tuple[type[DataProvider], ...] = (
    ToyJson,
    ToyVintage,
    *(type(registry.get(provider_id)) for provider_id in registry.ids()),
)


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.info.id)
def test_the_wording_is_exactly_what_the_row_pins(provider: type[DataProvider]) -> None:
    row = NOTICES[provider.info.id]
    terms = provider.info.terms
    assert terms.attribution == row.attribution
    assert terms.notice == row.notice
    assert terms.terms_url == row.terms_url
    assert terms.checked == row.checked


def unpinned(
    providers: Iterable[type[DataProvider]], notices: dict[str, Row]
) -> list[str]:
    """Return the ids of providers that have no pinned row."""
    return sorted(p.info.id for p in providers if p.info.id not in notices)


def test_every_registered_provider_has_a_row_and_every_row_a_provider() -> None:
    assert unpinned(PROVIDERS, NOTICES) == []
    assert {p.info.id for p in PROVIDERS} == set(NOTICES)


def test_a_provider_without_a_row_fails_the_suite() -> None:
    other = type("Other", (ToyJson,), {"info": replace(ToyJson.info, id="unpinned")})
    assert unpinned([*PROVIDERS, other], NOTICES) == ["unpinned"]
