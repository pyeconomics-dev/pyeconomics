# tests/surfaces/test_documents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The JSON documents of the data API's values (Phase 4 Step 4).

``data_document`` must carry the frame with every source record and the texts
its data must be shown with; ``jsonable`` must give any data-layer value a JSON
form canonical JSON accepts, and refuse a type it does not know rather than
guess at its text.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import re
from pathlib import PurePosixPath
from typing import Any

import bound_support as bs
import pytest

from pyeconomics import data
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import DataSource, LicenceClass, LlmUse
from pyeconomics.core.results import ResultWarning
from pyeconomics.data import cache
from pyeconomics.surfaces.documents import attributions, data_document, jsonable


class Colour(enum.Enum):
    RED = "red"


@dataclasses.dataclass(frozen=True)
class Box:
    name: str
    sizes: tuple[int, ...]
    colour: Colour


def test_jsonable_reads_every_kind_of_value() -> None:
    value = {
        "none": None,
        "flag": True,
        "count": 3,
        "rate": 0.05,
        "text": "x",
        "day": dt.date(2026, 10, 24),
        "moment": dt.datetime(2026, 10, 24, 12, tzinfo=dt.UTC),
        "path": PurePosixPath("/srv/data/x"),
        "pattern": re.compile(r"\d+"),
        "box": Box("b", (1, 2), Colour.RED),
        "set": frozenset({"b", "a"}),
        "list": [Colour.RED],
        3: "a key that is no text",
    }
    assert jsonable(value) == {
        "none": None,
        "flag": True,
        "count": 3,
        "rate": 0.05,
        "text": "x",
        "day": "2026-10-24",
        "moment": "2026-10-24T12:00:00+00:00",
        "path": "/srv/data/x",
        "pattern": r"\d+",
        "box": {"name": "b", "sizes": [1, 2], "colour": "red"},
        "set": ["a", "b"],
        "list": ["red"],
        "3": "a key that is no text",
    }
    canonical_json(jsonable(value))


def test_jsonable_uses_to_dict_and_model_dump() -> None:
    from pyeconomics.data.config import Settings  # noqa: PLC0415

    assert jsonable(Settings(offline=True))["offline"] is True
    assert jsonable(ResultWarning("code", "text")) == {
        "code": "code",
        "message": "text",
    }
    record = data.sources(check_keys=False)[0]
    assert jsonable(record)["id"] == record.id


def test_jsonable_refuses_an_unknown_type() -> None:
    with pytest.raises(TypeError, match="object has no JSON form"):
        jsonable(object())
    with pytest.raises(TypeError, match="type has no JSON form"):
        jsonable(Box)


_TOY = DataSource(
    provider="toy",
    series_id="S",
    licence=LicenceClass.HOSTED_SAFE,
    attribution="Source: a toy.",
    notice="Not endorsed by the toy.",
    terms_url="https://www.example.org/terms",
    llm_use=LlmUse.ALLOWED,
)


def _record(**changes: Any) -> DataSource:  # noqa: ANN401 - any field
    return dataclasses.replace(_TOY, **changes)


def test_attributions_come_first_then_notices_without_repeats() -> None:
    supplied = _record(
        licence=LicenceClass.USER_SUPPLIED,
        attribution="mine",
        notice=None,
        terms_url=None,
    )
    other = _record(provider="other", attribution="Source: another.", notice=None)
    assert attributions([_record(), _record(), other, supplied]) == [
        "Source: a toy.",
        "Source: another.",
        "Not endorsed by the toy.",
    ]


def test_a_data_document_holds_the_frame_its_sources_and_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415

    monkeypatch.setattr(provider_registry._CACHE, "registry", bs.world())  # noqa: SLF001
    with cache.bypass():
        resolved = data.get("us.unemployment.rate", as_of=dt.date(2024, 3, 20))
    document = data_document(resolved)
    assert set(document) == {"concept", "frame", "sources", "skipped", "attributions"}
    assert document["concept"] == "us.unemployment.rate"
    assert document["frame"] == resolved.frame.to_dict()
    assert document["sources"] == [record.to_dict() for record in resolved.sources]
    assert document["skipped"] == [jsonable(skip) for skip in resolved.skipped]
    assert document["attributions"] == attributions(resolved.sources)
    canonical_json(document)
