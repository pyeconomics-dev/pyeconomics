# tests/web/test_attribution_audit.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every provider's attribution and notices wherever the site hands over its data.

Phase 5 Step 16's attribution audit (ADR-0005 rule 2; ROADMAP §5 "Required
notices"), the files' part. The calculator's sources panel and the explorer's
chart annotation are audited per provider in ``web/tests/unit/attribution.test.tsx``,
and the built site's FRED notice in ``web/tests/site/``.

- A series file: Phase 4's export notice test
  (``tests/providers/test_export_notices.py``) exports a recorded frame of each
  provider in every format. This holds that it covers every registered
  provider, and that the formats the explorer downloads are those formats.
- A run's file: a result whose manifest records each provider's terms, in every
  format the calculator downloads, the bundle's ``ATTRIBUTION.txt`` among them,
  carries that provider's attribution and notice verbatim.
- FRED's notice is for local surfaces only: hosted mode may not serve FRED, and
  the hosted snapshot holds none of its series, so no hosted page or file ever
  carries FRED data or needs its notice.
"""

from __future__ import annotations

import ast
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest
from export_support import arrow_metadata, csv_metadata, xlsx_sheet
from test_export_notices import PROVIDERS

from pyeconomics import run
from pyeconomics.core.provenance import DataSource
from pyeconomics.core.results import Result
from pyeconomics.data import registry
from pyeconomics.exports import FORMATS, export_bytes
from pyeconomics.exports.bundle import bundle_bytes, bundle_members

if TYPE_CHECKING:
    from pyeconomics.data import Terms

WEB: Final = Path(__file__).resolve().parents[2] / "web" / "src" / "lib"


def _array(path: Path, name: str) -> tuple[str, ...]:
    """Read an ``export const NAME = [...] as const`` array of strings."""
    source = path.read_text(encoding="utf-8")
    match = re.search(rf"export const {name} = (\[[^\]]*\]) as const;", source)
    assert match is not None, f"{path.name} has no {name}"
    return tuple(ast.literal_eval(match[1]))


def test_the_export_notice_test_covers_every_registered_provider() -> None:
    covered = {provider.info.id for provider in PROVIDERS}
    assert set(registry.ids()) <= covered


def test_the_sites_downloads_are_the_formats_the_audits_cover() -> None:
    pytest.importorskip("fastapi")
    from pyeconomics.server import formats  # noqa: PLC0415

    runs = _array(WEB / "run-request.ts", "RUN_FORMATS")
    series = _array(WEB / "explorer.ts", "SERIES_FORMATS")
    assert runs == formats.RUN_FORMATS
    assert series == formats.SERIES_FORMATS
    # Every series download is a format the export notice test writes, and
    # every run download is one of those or the bundle, audited below.
    assert set(series) == set(FORMATS)
    assert set(runs) == {*FORMATS, "bundle"}


def _sourced(terms: Terms, provider: str) -> Result[Any, Any]:
    result = run(
        "foundations.time_value",
        {
            "calculation": "present_value",
            "rate": 0.05,
            "periods": 10,
            "future_value": 100,
        },
    )
    record = DataSource(
        provider=provider,
        series_id="AUDIT",
        field="rate",
        licence=terms.licence,
        attribution=terms.attribution,
        notice=terms.notice,
        terms_url=terms.terms_url,
        llm_use=terms.llm_use,
    )
    return Result.build(result.model, result.inputs, result.outputs, (), (record,))


@pytest.mark.parametrize("provider_id", sorted(registry.ids()))
def test_a_runs_every_download_carries_the_providers_attribution_and_notice(
    provider_id: str,
) -> None:
    terms = registry.get(provider_id).info.terms
    result = _sourced(terms, provider_id)
    expected = [terms.attribution, *([terms.notice] if terms.notice else [])]
    exported = {fmt: export_bytes(result, fmt) for fmt in FORMATS}

    block = csv_metadata(exported["csv"])
    assert ("attribution", terms.attribution) in block
    if terms.notice:
        assert ("notice", terms.notice) in block

    sheet = xlsx_sheet(exported["xlsx"], "manifest")
    cells = {str(cell) for row in sheet for cell in row}
    assert set(expected) <= cells

    for fmt in ("parquet", "arrow"):
        assert arrow_metadata(exported[fmt], fmt)["attributions"] == expected

    # A run's JSON file is its canonical bytes: the records are its manifest's.
    (stored,) = json.loads(exported["json"])["manifest"]["data_sources"]
    assert stored["attribution"] == terms.attribution
    assert stored.get("notice") == terms.notice

    members = bundle_members(result)
    text = members["ATTRIBUTION.txt"].decode("utf-8")
    for line in expected:
        assert line in text
    with zipfile.ZipFile(BytesIO(bundle_bytes(members))) as archive:
        assert archive.read("ATTRIBUTION.txt") == members["ATTRIBUTION.txt"]


def test_freds_notice_is_for_local_surfaces_only() -> None:
    from pyeconomics.data.snapshots.set import snapshot_set  # noqa: PLC0415

    fred = registry.get("fred").info.terms
    assert fred.notice is not None
    assert "FRED® API" in fred.notice
    assert fred.licence.hosted_allowed is False
    assert snapshot_set().of("fred") == ()
