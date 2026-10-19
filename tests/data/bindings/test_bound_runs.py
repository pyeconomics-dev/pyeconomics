# tests/data/bindings/test_bound_runs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Running a ``Bound``: the schema-2 manifest, determinism, warnings, exports.

``run`` and ``run_model`` take what ``bind`` returns and put one ``DataSource``
record per bound field in the manifest. The hashes keep their definition: they
cover the inputs, outputs and warnings, never the manifest (ADR-0011 decision 16).
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING

import bound_support as bs
import pytest

import pyeconomics
from pyeconomics.core import (
    Bound,
    InputError,
    LicenceClass,
    canonical_json,
    run_model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.binding import user_supplied
from pyeconomics.data import bind_model

if TYPE_CHECKING:
    from pathlib import Path

PAST = dt.date(2024, 3, 20)
LATER = dt.date(2024, 9, 30)


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the toy bound models the installed registry, as an entry point would."""
    monkeypatch.setattr(
        core_registry._CACHE,  # noqa: SLF001
        "registry",
        bs.model_registry(),
    )


def bound_at(day: dt.date | None = PAST) -> Bound:
    return bind_model(bs.unemployment, as_of=day, registry=bs.world())


# --- the manifest ---------------------------------------------------------------------


def test_a_run_records_one_data_source_per_bound_field() -> None:
    bound = bind_model(bs.unemployment_change, as_of=LATER, registry=bs.world())
    result = run_model(bs.unemployment_change, bound)
    assert result.manifest.schema_version == 2
    assert result.manifest.data_sources == bound.sources
    assert [s.field for s in result.manifest.data_sources] == ["change", "unemployment"]
    assert result.outputs.score == pytest.approx(0.041 + 0.001)
    assert result.inputs.unemployment == 0.041


def test_the_manifest_dict_carries_the_records_in_canonical_form() -> None:
    result = run_model(bs.unemployment, bound_at())
    records = result.manifest.to_dict()["data_sources"]
    assert isinstance(records, list)
    assert records == [result.manifest.data_sources[0].to_dict()]
    (record,) = records
    assert isinstance(record, dict)
    assert record["provider"] == "fred"
    assert record["vintage"] == "as_of:2024-03-20"
    assert record["retrieved_at"] == "2026-10-15T12:00:00+00:00"
    assert json.loads(result.to_json())["manifest"]["data_sources"] == records


def test_a_run_without_data_has_no_records_and_keeps_its_hashes() -> None:
    plain = run_model(bs.plain, {"unemployment": 0.04, "weight": 2.0})
    assert plain.manifest.data_sources == ()
    assert plain.manifest.to_dict()["data_sources"] == []


# --- determinism --------------------------------------------------------------


def test_the_same_inputs_and_records_give_the_same_manifest_bytes() -> None:
    bound = bound_at()
    first, second = run_model(bs.unemployment, bound), run_model(bs.unemployment, bound)
    assert first.manifest == second.manifest
    assert canonical_json(first.manifest.to_dict()) == canonical_json(
        second.manifest.to_dict()
    )
    assert first.to_json() == second.to_json()


def test_identical_values_give_identical_result_hashes_whatever_their_source() -> None:
    # 0.041 read in real time from FRED as of September, and as the latest value
    # from the originator: the numbers agree, the provenance does not.
    by_vintage = run_model(bs.unemployment, bound_at(LATER))
    by_latest = run_model(bs.unemployment, bound_at(None))
    assert by_vintage.inputs == by_latest.inputs
    assert by_vintage.manifest.result_sha256 == by_latest.manifest.result_sha256
    assert by_vintage.manifest.inputs_sha256 == by_latest.manifest.inputs_sha256
    assert by_vintage.manifest.data_sources != by_latest.manifest.data_sources
    assert by_vintage.manifest != by_latest.manifest


def test_different_values_give_different_hashes() -> None:
    first = run_model(bs.unemployment, bound_at(PAST))
    second = run_model(bs.unemployment, bound_at(LATER))
    assert first.manifest.result_sha256 != second.manifest.result_sha256


def test_the_records_are_held_sorted_by_field_whatever_their_order() -> None:
    bound = bind_model(bs.unemployment_change, as_of=LATER, registry=bs.world())
    reordered = Bound(
        model_id=bound.model_id,
        profile=bound.profile,
        values=dict(reversed(list(bound.values.items()))),
        sources=tuple(reversed(bound.sources)),
        as_of=bound.as_of,
    )
    assert reordered.sources == bound.sources
    assert list(reordered.values) == sorted(reordered.values)
    one = run_model(bs.unemployment_change, bound)
    two = run_model(bs.unemployment_change, reordered)
    assert canonical_json(one.manifest.to_dict()) == canonical_json(
        two.manifest.to_dict()
    )


def test_a_window_bound_array_field_runs_as_a_tuple() -> None:
    bound = bind_model(bs.unemployment_window, as_of=LATER, registry=bs.world())
    result = run_model(bs.unemployment_window, bound)
    assert result.inputs.history == (0.038, 0.039, 0.040, 0.041)
    assert result.outputs.mean == pytest.approx(0.0395)
    assert [s.field for s in result.manifest.data_sources] == ["history"]


def test_a_value_scaled_to_dollars_runs_and_warns_when_the_source_is_revised() -> None:
    bound = bind_model(
        bs.output, as_of=dt.date(2024, 2, 15), registry=bs.world(bs.bea())
    )
    result = run_model(bs.output, bound)
    assert result.outputs.doubled == pytest.approx(2 * 22_100.0 * 1e9)
    assert [w.code for w in result.warnings] == ["revised_data"]
    (record,) = result.manifest.data_sources
    assert record.provider == "bea"
    assert record.warnings == ("revised_data",)


# --- revised data warns -------------------------------------------------------


def test_a_result_of_revised_data_carries_the_revised_data_warning() -> None:
    bound = bind_model(
        bs.unemployment, as_of=PAST, profile="revised", registry=bs.world()
    )
    result = run_model(bs.unemployment, bound)
    (warning,) = result.warnings
    assert warning.code == "revised_data"
    assert "unemployment" in warning.message
    assert "not those published on the evaluation date" in warning.message
    # The warning is in the hashed body: revised data never shares a hash with the
    # same numbers read in real time.
    real_time = run_model(
        bs.unemployment, bind_model(bs.unemployment, as_of=PAST, registry=bs.world())
    )
    assert real_time.warnings == ()
    assert result.manifest.result_sha256 != real_time.manifest.result_sha256


def test_a_real_time_result_has_no_warning() -> None:
    assert run_model(bs.unemployment, bound_at()).warnings == ()


# --- what a Bound must match --------------------------------------------------


def test_a_bound_runs_only_the_model_it_was_bound_for() -> None:
    with pytest.raises(InputError, match=r"bound for 'macro\.toy_unemployment'"):
        run_model(bs.unemployment_change, bound_at())


def test_a_bound_and_keyword_fields_are_not_both_accepted() -> None:
    with pytest.raises(TypeError, match="not both"):
        run_model(bs.unemployment, bound_at(), weight=2.0)


def test_a_bound_missing_a_required_field_is_a_validation_error() -> None:
    bound = Bound(model_id=bs.unemployment.id, profile="default", values={})
    with pytest.raises(InputError, match="unemployment"):
        run_model(bs.unemployment, bound)


def test_run_by_id_takes_a_bound_and_resolves_an_alias(
    installed: None,  # noqa: ARG001 - the fixture installs the toy models
) -> None:
    bound = bind_model(bs.unemployment, as_of=PAST, registry=bs.world())
    result = pyeconomics.run("macro.toy_unemployment", bound)
    assert result.manifest.data_sources == bound.sources
    assert result.model_id == "macro.toy_unemployment"


def test_the_public_bind_resolves_a_model_id(
    installed: None,  # noqa: ARG001 - the fixture installs the toy models
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415

    monkeypatch.setattr(provider_registry._CACHE, "registry", bs.world())  # noqa: SLF001
    bound = pyeconomics.bind("macro.toy_unemployment", as_of=PAST, weight=2.0)
    assert bound.model_id == "macro.toy_unemployment"
    assert bound.values == {"unemployment": 0.039, "weight": 2.0}
    result = pyeconomics.run("macro.toy_unemployment", bound)
    assert result.outputs.score == pytest.approx(0.078)
    with pytest.raises(pyeconomics.core.ModelNotFoundError):
        pyeconomics.bind("macro.no_such_model")


# --- attributions and exports -------------------------------------------------


def test_attributions_list_each_text_once_attributions_first() -> None:
    bound = bind_model(bs.unemployment_change, as_of=LATER, registry=bs.world())
    result = run_model(bs.unemployment_change, bound)
    texts = result.attributions()
    # Two fields read FRED's series: one attribution, one notice, each once.
    assert texts == ("Source: an example library-only aggregator.",)
    assert len(texts) == len(set(texts))


def test_attributions_carry_a_required_notice_and_skip_a_supplied_value() -> None:
    bound = bind_model(bs.unemployment, registry=bs.world())  # from the originator
    result = run_model(bs.unemployment, bound)
    assert result.attributions() == (
        "Source: an example statistical agency.",
        "This product is not endorsed by the example agency.",
    )
    supplied = bind_model(
        bs.unemployment, overrides={"unemployment": 0.05}, registry=bs.world()
    )
    assert run_model(bs.unemployment, supplied).attributions() == ()
    assert run_model(bs.plain, {"unemployment": 0.04}).attributions() == ()


def test_an_arrow_export_carries_the_records_in_its_metadata(tmp_path: Path) -> None:
    pq = pytest.importorskip("pyarrow.parquet")  # the test group installs pyarrow
    result = run_model(bs.unemployment, bound_at())
    path = tmp_path / "bound.parquet"
    result.to_parquet(path)
    metadata = pq.read_table(path).schema.metadata
    manifest = json.loads(metadata[b"pyeconomics.manifest"])
    assert manifest == result.manifest.to_dict()
    assert manifest["data_sources"][0]["field"] == "unemployment"


# --- the Bound itself ---------------------------------------------------------


def test_a_bound_is_immutable_and_reads_its_values() -> None:
    bound = bound_at()
    with pytest.raises(TypeError):
        bound.values["unemployment"] = 0.5  # type: ignore[index]  # ty: ignore[invalid-assignment]
    assert bound.overridden == ()
    assert bound.to_dict()["values"] == {"unemployment": 0.039}
    canonical_json(bound.to_dict())  # JSON-ready


def test_a_bound_checks_its_parts() -> None:
    record = user_supplied("unemployment")
    with pytest.raises(InputError, match="snake_case"):
        Bound(model_id="a.b", profile="Not Snake", values={}, sources=(record,))
    with pytest.raises(InputError, match="DataSource"):
        Bound(model_id="a.b", profile="default", values={}, sources=("x",))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    with pytest.raises(InputError, match="snake_case"):
        Bound(model_id="a.b", profile="default", values={"Not A Field": 1.0})


def test_a_user_supplied_record_names_the_field_never_the_value() -> None:
    record = user_supplied("unemployment", concept="us.unemployment.rate")
    assert record.licence is LicenceClass.USER_SUPPLIED
    assert "0.05" not in json.dumps(record.to_dict())
    assert record.canonical_json()
