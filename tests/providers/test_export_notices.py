# tests/providers/test_export_notices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every provider's attribution and notice, verbatim in every export (ADR-0005).

ADR-0005's Confirmation asks for a test per provider that checks the exact
wording wherever the data appears. For the toys and every registered provider,
one recorded frame (or, for a source of records only, its records) is replayed
offline from its cassette and exported in each format. The frame's attribution
and required notice must appear verbatim in the CSV metadata block, on the XLSX
manifest sheet, in the Parquet and Arrow schema metadata and in the JSON
document, beside its terms page.

The frame's terms are the provider's, pinned in tests/providers/test_notices.py,
or a series' own where the source asks for more: an access date (BLS, OECD), a
dataset's source line (World Bank), a dated copyright (New York Fed). Their
terms page is always the provider's, which ties each frame to its pinned row.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from export_support import arrow_metadata, csv_metadata, xlsx_sheet
from provider_contract import replay, replay_key
from test_notices import NOTICES
from toys import ToyJson, ToyVintage

from pyeconomics.data import configure, registry
from pyeconomics.data.providers.base import Capability
from pyeconomics.exports import FORMATS, export_bytes

if TYPE_CHECKING:
    from pyeconomics.data import DataProvider, Terms

pytestmark = pytest.mark.filterwarnings("ignore:.*\\[yahoo_personal_use\\]")

PROVIDERS: tuple[type[DataProvider], ...] = (
    ToyJson,
    ToyVintage,
    *(type(registry.get(provider_id)) for provider_id in registry.ids()),
)


def recorded(provider: type[DataProvider]) -> Any:
    """Replay the provider's first recorded fetch, or its records."""
    successes = [c for c in provider.cases if c.expect is None]
    case = next(
        (c for c in successes if c.operation is Capability.FETCH),
        None,
    ) or next(c for c in successes if c.operation is Capability.RECORDS)
    if provider.info.id == "yfinance":
        configure(enable_yfinance=True)
    return provider().run_case(
        case,
        key=replay_key(provider, case),
        transport=replay(provider.info.id, case),
    )


def terms_of(value: Any) -> Terms:
    terms: Terms = value.meta.terms if hasattr(value, "meta") else value.terms
    return terms


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.info.id)
def test_the_exact_wording_appears_in_every_format(
    provider: type[DataProvider],
) -> None:
    value = recorded(provider)
    terms = terms_of(value)
    assert terms.terms_url == NOTICES[provider.info.id].terms_url
    expected = [terms.attribution, *([terms.notice] if terms.notice else [])]
    exported = {fmt: export_bytes(value, fmt) for fmt in FORMATS}

    block = csv_metadata(exported["csv"])
    assert ("attribution", terms.attribution) in block
    if terms.notice:
        assert ("notice", terms.notice) in block
    assert ("terms", terms.terms_url) in block

    sheet = xlsx_sheet(exported["xlsx"], "manifest")
    labels = ["attribution", "notice"]
    assert sheet[: len(expected)] == [
        [label, text] for label, text in zip(labels, expected, strict=False)
    ]
    assert ["terms", terms.terms_url] in sheet

    for fmt in ("parquet", "arrow"):
        metadata = arrow_metadata(exported[fmt], fmt)
        assert metadata["attributions"] == expected
        manifest = metadata["manifest"]
        stored = manifest["meta"]["terms"] if "meta" in manifest else manifest["terms"]
        assert stored["attribution"] == terms.attribution
        assert stored["notice"] == terms.notice

    document = json.loads(exported["json"])
    assert document["attributions"] == expected
    body = document["frame"]["meta"] if "frame" in document else document["records"]
    assert body["terms"]["attribution"] == terms.attribution
    assert body["terms"]["notice"] == terms.notice


def test_every_registered_provider_is_exported() -> None:
    exported = {provider.info.id for provider in PROVIDERS}
    assert set(registry.ids()) <= exported
    assert exported == set(NOTICES)
