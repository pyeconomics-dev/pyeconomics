# tests/data/bindings/test_llm_use_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``llm_use`` gate in a bind and in ``invoke`` (Phase 4 Step 8).

A bind under a policy passes over every source it does not permit, and such a
source does not count as one that keeps vintages: a bind as of a past date whose
only vintage source is refused reads the latest data and labels it
``revised_data``, as when no source keeps vintages. ``invoke`` threads the
policy into the bind and checks the result's records once more before it
returns it. Without a policy every bind is what it was.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

import bound_support as bs
import pytest
from catalog_support import LIBRARY_TERMS, meta
from scripted import calls_of, scripted

from pyeconomics.core import LlmUsePolicy, run_model
from pyeconomics.core import registry as core_registry
from pyeconomics.core.binding import REVISED_DATA, Bound
from pyeconomics.core.provenance import DataSource, LicenceClass, LlmUse
from pyeconomics.data import (
    Capability,
    LlmUseError,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    bind_model,
)
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from pyeconomics.data import DataProvider

PAST = dt.date(2024, 3, 20)


def forbidden_fred() -> type[DataProvider]:
    """FRED as it is: library-only, keeping vintages, forbidden for LLMs."""
    frame = Series(
        tuple(bs.MONTHS[row] for row, *_ in bs.VINTAGED),
        tuple(value for _, value, *_ in bs.VINTAGED),
        meta(
            ObservationFrequency.MONTHLY,
            provider="fred",
            series_id="UNRATE",
            title="Unemployment rate",
            unit=bs.RATE,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            terms=LIBRARY_TERMS,
        ),
        tuple(RealtimePeriod(start, end) for *_, start, end in bs.VINTAGED),
    )
    return scripted(
        "fred",
        {"UNRATE": frame},
        licence=LicenceClass.LIBRARY_ONLY,
        llm_use=LlmUse.FORBIDDEN,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )


def test_a_past_date_without_a_permitted_vintage_source_reads_revised_data() -> None:
    fred = forbidden_fred()
    world = bs.world(bs.bea(), bs.bls(), fred, bs.oecd())
    bound = bind_model(
        bs.unemployment, as_of=PAST, registry=world, llm_use=LlmUsePolicy.ALLOWED_ONLY
    )
    (record,) = bound.sources
    assert record.provider == "bls"
    assert record.llm_use is LlmUse.ALLOWED
    assert REVISED_DATA in record.warnings
    assert calls_of(fred) == []
    result = run_model(bs.unemployment, bound)
    assert REVISED_DATA in {warning.code for warning in result.warnings}


def test_without_a_policy_the_same_bind_reads_the_vintage() -> None:
    world = bs.world(bs.bea(), bs.bls(), forbidden_fred(), bs.oecd())
    (record,) = bind_model(bs.unemployment, as_of=PAST, registry=world).sources
    assert record.provider == "fred"
    assert record.vintage == "as_of:2024-03-20"
    assert REVISED_DATA not in record.warnings


def test_a_bound_concept_with_no_permitted_source_is_an_llm_use_error() -> None:
    oecd = scripted(
        "oecd", {bs.UK_INFLATION: _uk(LlmUse.UNCLEAR)}, llm_use=LlmUse.UNCLEAR
    )
    world = bs.world(bs.bea(), bs.bls(), bs.fred(), oecd)
    with pytest.raises(LlmUseError) as caught:
        bind_model(
            bs.unemployment,
            profile="uk",
            registry=world,
            llm_use=LlmUsePolicy.ALLOWED_ONLY,
        )
    assert caught.value.concept == "gb.inflation.cpi.yoy"
    bound = bind_model(
        bs.unemployment, profile="uk", registry=world, llm_use="allow-unclear"
    )
    assert bound.sources[0].llm_use is LlmUse.UNCLEAR


def _uk(use: LlmUse) -> Series:
    return Series(
        bs.MONTHS,
        (0.040, 0.034, 0.032, 0.023, 0.020, 0.020),
        meta(
            ObservationFrequency.MONTHLY,
            provider="oecd",
            series_id=bs.UK_INFLATION,
            unit=bs.RATE,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            terms=meta().terms.with_overrides(llm_use=use),
        ),
    )


# --- invoke ------------------------------------------------------------------------


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the toy bound models the installed registry, as an entry point would."""
    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001


def _bind_in(monkeypatch: pytest.MonkeyPatch, world: object) -> None:
    """Bind every invoke in this test against a scripted world."""
    from pyeconomics.data import bindings  # noqa: PLC0415

    real = bindings.bind_model

    def scripted_bind(*args: Any, **kwargs: Any) -> Bound:  # noqa: ANN401
        kwargs["registry"] = world
        return real(*args, **kwargs)

    monkeypatch.setattr(bindings, "bind_model", scripted_bind)


@pytest.mark.usefixtures("installed")
def test_invoke_threads_the_policy_into_the_bind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_in(monkeypatch, bs.world(bs.bea(), bs.bls(), forbidden_fred(), bs.oecd()))
    request = BindRequest(as_of=PAST)
    gated = invoke(bs.unemployment.id, None, bind=request, llm_use="allowed-only")
    assert [r.provider for r in gated.manifest.data_sources] == ["bls"]
    plain = invoke(bs.unemployment.id, None, bind=request)
    assert [r.provider for r in plain.manifest.data_sources] == ["fred"]


@pytest.mark.usefixtures("installed")
def test_invoke_withholds_a_result_still_carrying_a_refused_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The final check: a record the bind should never have let through."""
    from pyeconomics.data import bindings  # noqa: PLC0415

    leaked = DataSource(
        provider="fred",
        series_id="UNRATE",
        field="unemployment",
        licence=LicenceClass.LIBRARY_ONLY,
        attribution="Source: an example aggregator.",
        terms_url="https://www.example.org/legal/library",
        llm_use=LlmUse.FORBIDDEN,
    )

    def leaky(*_args: object, **_kwargs: object) -> Bound:
        return Bound(
            model_id=bs.unemployment.id,
            profile="default",
            values={"unemployment": 0.04},
            sources=(leaked,),
        )

    monkeypatch.setattr(bindings, "bind_model", leaky)
    with pytest.raises(LlmUseError) as caught:
        invoke(bs.unemployment.id, None, bind=BindRequest(), llm_use="allowed-only")
    assert "withheld" in str(caught.value)
    assert caught.value.provider == "fred"
    # Without a policy, invoke returns what the bind gave.
    result = invoke(bs.unemployment.id, None, bind=BindRequest())
    assert result.manifest.data_sources == (leaked,)


@pytest.mark.usefixtures("installed")
def test_a_run_without_a_bind_reads_no_data_under_any_policy() -> None:
    result = invoke(bs.plain.id, {"unemployment": 0.04}, llm_use="allowed-only")
    assert result.manifest.data_sources == ()


def test_a_policy_that_is_not_one_is_invalid_input() -> None:
    from pyeconomics.core import InputError  # noqa: PLC0415

    with pytest.raises(InputError, match="llm_use"):
        invoke("foundations.time_value", None, llm_use="anything")
