# tests/data/catalog/test_resolver_rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The resolver's rules, one by one, against scripted providers.

Each test builds the smallest world that exercises one rule: a concept whose
candidates sit on scripted providers (tests/data/catalog/scripted.py), a registry
of just those, and a frame or an exception per series. The providers are real
``DataProvider`` subclasses, so the base class's own gates run; only the exchange
is scripted, and every request is recorded so a test can show a refused
candidate was never asked.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
from dataclasses import replace

import pytest
from catalog_support import (
    HOSTED_TERMS,
    LIBRARY_TERMS,
    as_series,
    as_table,
    month_end,
    monthly,
    quarterly,
    series,
)
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import InputError, UnitKind
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.provenance import LicenceClass, RealtimePeriod
from pyeconomics.data import (
    Capability,
    ColumnMeta,
    ConceptNotFoundError,
    CredentialError,
    DataError,
    DateConvention,
    LicenceError,
    Mode,
    ObservationFrequency,
    OfflineError,
    RateLimitError,
    SeasonalAdjustment,
    Series,
    SeriesNotFoundError,
    Table,
    TableMeta,
    TransportError,
    UnitRecord,
    Vintage,
    catalog,
    resolve,
)
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Parameter,
    Shape,
    Tier,
)
from pyeconomics.data.providers.base import Platform


def concept(
    candidates: tuple[Candidate | Derived, ...],
    *,
    concept_id: str = "us.test.value",
    kind: UnitKind | None = UnitKind.INDEX_LEVEL,
    frequency: ObservationFrequency = ObservationFrequency.MONTHLY,
    seasonal: SeasonalAdjustment = SeasonalAdjustment.NOT_APPLICABLE,
    **fields: object,
) -> Concept:
    return Concept(
        id=concept_id,
        title="A test concept",
        definition="A concept made for a test of the resolver.",
        unit_kind=kind,
        frequency=frequency,
        seasonal_adjustment=seasonal,
        candidates=candidates,
        **fields,  # type: ignore[arg-type]
    )


def give_key(isolated: object, provider: str) -> None:
    isolated.keyring.set_password("pyeconomics", provider, secrets.token_hex(16))  # type: ignore[attr-defined]


DATA = [100.0 + i for i in range(30)]


# --- order, records and the chain ---------------------------------------------


def test_the_first_candidate_that_answers_wins_and_the_record_names_everything() -> (
    None
):
    first = scripted("alpha", {"A": monthly(DATA, provider="alpha", series_id="A")})
    second = scripted("beta", {"B": monthly(DATA, provider="beta", series_id="B")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(first, second),
    )
    assert result.concept == "us.test.value"
    assert result.skipped == ()
    record = result.source
    assert (record.provider, record.series_id, record.concept) == (
        "alpha",
        "A",
        "us.test.value",
    )
    assert record.fallback_chain == ("alpha",)
    assert record.vintage == "latest"
    assert record.observation_start == result.frame.index[0]
    assert record.observation_end == result.frame.index[-1]
    assert record.transforms == ()
    assert calls_of(second) == []


def test_a_skipped_candidate_is_recorded_in_the_chain_the_codes_and_the_skips() -> None:
    keyed = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, keyed=True)
    second = scripted("beta", {"B": monthly(DATA, provider="beta", series_id="B")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(keyed, second),
    )
    record = result.source
    assert record.provider == "beta"
    assert record.fallback_chain == ("alpha", "beta")
    assert "skipped_alpha_key_missing" in record.warnings
    (skip,) = result.skipped
    assert (skip.provider, skip.reason) == ("alpha", "key_missing")
    assert "ALPHA_API_KEY" in skip.detail
    assert calls_of(keyed) == []  # never asked: no key, no request


def test_a_key_in_the_chain_lets_a_keyed_candidate_answer(isolated: object) -> None:
    give_key(isolated, "alpha")
    keyed = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, keyed=True)
    result = resolve(
        concept((Candidate(provider="alpha", series="A"),)), registry=registry_of(keyed)
    )
    assert result.source.provider == "alpha"
    assert len(calls_of(keyed)) == 1


def test_the_key_never_reaches_a_record(isolated: object) -> None:
    key = secrets.token_hex(16)
    isolated.keyring.set_password("pyeconomics", "alpha", key)  # type: ignore[attr-defined]
    keyed = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, keyed=True)
    result = resolve(
        concept((Candidate(provider="alpha", series="A"),)), registry=registry_of(keyed)
    )
    seen = repr(result) + json.dumps([s.to_dict() for s in result.sources])
    assert key not in seen


def test_a_provider_that_is_not_registered_is_passed_over() -> None:
    other = scripted("beta", {"B": monthly(DATA, provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="ghost", series="G"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(other),
    )
    assert [s.reason for s in result.skipped] == ["provider_unavailable"]


def test_a_provider_that_does_not_run_here_is_passed_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pyeconomics.data.resolver.current_platform", lambda: Platform.PYODIDE
    )
    cls = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    cls.info = replace(cls.info, platforms=(Platform.LINUX,))
    other = scripted("beta", {"B": monthly(DATA, provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(cls, other),
    )
    assert [s.reason for s in result.skipped] == ["platform_unsupported"]


# --- extras, errors and the reasons -------------------------------------------


def test_a_missing_extra_is_recorded_and_the_next_candidate_answers() -> None:
    missing = scripted(
        "alpha",
        {"A": MissingOptionalDependencyError("the sdmx extra is not installed")},
        extra="sdmx",
    )
    other = scripted("beta", {"B": monthly(DATA, provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(missing, other),
    )
    assert [s.reason for s in result.skipped] == ["extra_missing"]
    assert "skipped_alpha_extra_missing" in result.source.warnings


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (SeriesNotFoundError("alpha", "A"), "series_not_found"),
        (TransportError("down", provider="alpha"), "unavailable"),
        (RateLimitError("slow down", provider="alpha"), "rate_limited"),
        (CredentialError("refused", provider="alpha"), "credential_refused"),
        (OfflineError("nothing cached", provider="alpha"), "offline"),
        (DataError("odd", provider="alpha"), "data_error"),
    ],
)
def test_each_failure_maps_to_one_reason_and_the_next_candidate_answers(
    error: Exception, reason: str
) -> None:
    broken = scripted("alpha", {"A": error})
    other = scripted("beta", {"B": monthly(DATA, provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(broken, other),
    )
    assert [s.reason for s in result.skipped] == [reason]


def test_when_nothing_answers_the_error_lists_why_each_was_passed_over() -> None:
    a = scripted("alpha", {"A": SeriesNotFoundError("alpha", "A")})
    b = scripted("beta", {"B": TransportError("down", provider="beta")})
    with pytest.raises(DataError, match="alpha A: series_not_found") as caught:
        resolve(
            concept(
                (
                    Candidate(provider="alpha", series="A"),
                    Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
                )
            ),
            registry=registry_of(a, b),
        )
    assert "beta B: unavailable" in str(caught.value)


def test_every_key_missing_is_a_credential_error_naming_the_variable() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, keyed=True)
    with pytest.raises(CredentialError, match="ALPHA_API_KEY"):
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            registry=registry_of(a),
        )


def test_offline_with_nothing_cached_is_an_offline_error() -> None:
    a = scripted("alpha", {"A": OfflineError("none cached", provider="alpha")})
    with pytest.raises(OfflineError):
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            registry=registry_of(a),
        )


# --- strict -------------------------------------------------------------------


def test_strict_tries_only_the_first_candidate_and_never_falls_back() -> None:
    a = scripted("alpha", {"A": SeriesNotFoundError("alpha", "A")})
    b = scripted("beta", {"B": monthly(DATA, provider="beta")})
    candidates = (
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    assert (
        resolve(concept(candidates), registry=registry_of(a, b)).source.provider
        == "beta"
    )
    with pytest.raises(DataError, match="strictly") as caught:
        resolve(concept(candidates), registry=registry_of(a, b), strict=True)
    assert "beta" not in str(caught.value)
    assert calls_of(b) == [calls_of(b)[0]]  # the one call is the non-strict run's


def test_strict_reports_a_missing_key_as_a_credential_error() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, keyed=True)
    b = scripted("beta", {"B": monthly(DATA, provider="beta")})
    with pytest.raises(CredentialError):
        resolve(
            concept(
                (
                    Candidate(provider="alpha", series="A"),
                    Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
                )
            ),
            registry=registry_of(a, b),
            strict=True,
        )


# --- hosted mode --------------------------------------------------------------


@pytest.mark.parametrize(
    "licence",
    [LicenceClass.LIBRARY_ONLY, LicenceClass.BYOK, LicenceClass.PREMIUM_LOCAL],
)
def test_hosted_mode_refuses_each_class_it_must_before_any_request(
    licence: LicenceClass,
) -> None:
    refused = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha", terms=LIBRARY_TERMS)},
        licence=licence,
    )
    with pytest.raises(LicenceError, match=licence.value) as caught:
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            mode=Mode.HOSTED,
            registry=registry_of(refused),
        )
    assert "classes found" in str(caught.value)
    assert calls_of(refused) == []
    # The same concept resolves in library mode.
    assert (
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            registry=registry_of(refused),
        ).source.licence
        is LicenceClass.LIBRARY_ONLY
    )


@pytest.mark.parametrize(
    "licence", [LicenceClass.HOSTED_SAFE, LicenceClass.USER_SUPPLIED]
)
def test_hosted_mode_serves_hosted_safe_and_user_supplied(
    licence: LicenceClass,
) -> None:
    allowed = scripted("alpha", {"A": monthly(DATA, provider="alpha")}, licence=licence)
    result = resolve(
        concept((Candidate(provider="alpha", series="A"),)),
        mode=Mode.HOSTED,
        registry=registry_of(allowed),
    )
    assert result.source.provider == "alpha"


def test_hosted_mode_skips_the_aggregator_and_takes_the_originator() -> None:
    aggregator = scripted(
        "fredlike",
        {"F": monthly(DATA, provider="fredlike", terms=LIBRARY_TERMS)},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    originator = scripted("agency", {"O": monthly(DATA, provider="agency")})
    # Hosted never falls back to the aggregator, even when the originator fails.
    failing = scripted("agency", {"X": SeriesNotFoundError("agency", "X")})
    ok = resolve(
        concept(
            (
                Candidate(provider="agency", series="O"),
                Candidate(provider="fredlike", series="F", tier=Tier.AGGREGATOR),
            )
        ),
        mode=Mode.HOSTED,
        registry=registry_of(originator, aggregator),
    )
    assert ok.source.provider == "agency"
    with pytest.raises(DataError) as caught:
        resolve(
            concept(
                (
                    Candidate(provider="agency", series="X"),
                    Candidate(provider="fredlike", series="F", tier=Tier.AGGREGATOR),
                )
            ),
            mode=Mode.HOSTED,
            registry=registry_of(failing, aggregator),
        )
    assert not isinstance(caught.value, LicenceError)
    assert calls_of(aggregator) == []


def test_a_concept_with_only_library_candidates_names_every_class_it_found() -> None:
    a = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha")},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    b = scripted(
        "beta", {"B": monthly(DATA, provider="beta")}, licence=LicenceClass.BYOK
    )
    with pytest.raises(LicenceError) as caught:
        resolve(
            concept(
                (
                    Candidate(provider="alpha", series="A", tier=Tier.AGGREGATOR),
                    Candidate(provider="beta", series="B", tier=Tier.PREMIUM),
                )
            ),
            mode=Mode.HOSTED,
            registry=registry_of(a, b),
        )
    text = str(caught.value)
    assert "byok" in text
    assert "library-only" in text
    assert "alpha" in text
    assert "beta" in text


def test_a_series_level_licence_marker_overrides_the_providers_class() -> None:
    restricted = monthly(DATA, provider="alpha", terms=LIBRARY_TERMS)
    marked = scripted("alpha", {"A": restricted})  # the provider is hosted-safe
    open_ = scripted("beta", {"B": monthly(DATA, provider="beta")})
    candidates = (
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B"),
    )
    result = resolve(
        concept(candidates), mode=Mode.HOSTED, registry=registry_of(marked, open_)
    )
    assert result.source.provider == "beta"
    (skip,) = result.skipped
    assert (skip.provider, skip.reason, skip.licence) == (
        "alpha",
        "licence_refused",
        LicenceClass.LIBRARY_ONLY,
    )
    assert "skipped_alpha_licence_refused" in result.source.warnings
    # In library mode the same series is served, with its own class recorded.
    served = resolve(concept(candidates), registry=registry_of(marked, open_))
    assert served.source.licence is LicenceClass.LIBRARY_ONLY


# --- vintages -----------------------------------------------------------------


def _vintaged(provider: str, series_id: str) -> Series:
    periods = [RealtimePeriod(dt.date(2015, 1, 1)) for _ in range(30)]
    return monthly(DATA, provider=provider, series_id=series_id, realtime=periods)


def test_a_candidate_that_keeps_no_vintages_cannot_honour_one() -> None:
    plain = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    vintaged = scripted(
        "beta",
        {"B": _vintaged("beta", "B")},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    candidates = (
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    latest = resolve(concept(candidates), registry=registry_of(plain, vintaged))
    assert latest.source.provider == "alpha"
    old = resolve(
        concept(candidates),
        as_of=dt.date(2020, 6, 30),
        registry=registry_of(plain, vintaged),
    )
    assert old.source.provider == "beta"
    assert old.source.vintage == "as_of:2020-06-30"
    assert old.source.realtime is not None
    assert old.source.realtime.covers(dt.date(2020, 6, 30))
    assert [s.reason for s in old.skipped] == ["vintage_unsupported"]
    assert calls_of(plain) == [calls_of(plain)[0]]  # only the latest run asked it


def test_a_vintage_nobody_can_honour_is_an_error() -> None:
    plain = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    with pytest.raises(DataError, match="vintage_unsupported"):
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            vintage="first_release",
            registry=registry_of(plain),
        )


def test_as_of_and_vintage_together_are_refused_and_a_label_or_object_works() -> None:
    vintaged = scripted(
        "beta",
        {"B": _vintaged("beta", "B")},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    one = concept((Candidate(provider="beta", series="B"),))
    with pytest.raises(InputError, match="not both"):
        resolve(
            one,
            as_of=dt.date(2020, 1, 1),
            vintage="latest",
            registry=registry_of(vintaged),
        )
    by_label = resolve(one, vintage="first_release", registry=registry_of(vintaged))
    by_object = resolve(
        one, vintage=Vintage.first_release(), registry=registry_of(vintaged)
    )
    assert by_label.source.vintage == by_object.source.vintage == "first_release"


# --- definitions --------------------------------------------------------------


def test_a_frequency_that_differs_is_not_the_concept_and_is_passed_over() -> None:
    wrong = scripted("alpha", {"A": quarterly([1.0, 2.0, 3.0], provider="alpha")})
    right = scripted("beta", {"B": monthly(DATA, provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        registry=registry_of(wrong, right),
    )
    (skip,) = result.skipped
    assert skip.reason == "definition_mismatch"
    assert "quarterly" in skip.detail


def test_a_declared_delivery_frequency_is_accepted_for_that_candidate() -> None:
    labelled = scripted("alpha", {"A": quarterly([1.0, 2.0, 3.0], provider="alpha")})
    result = resolve(
        concept(
            (
                Candidate(
                    provider="alpha",
                    series="A",
                    delivers=ObservationFrequency.QUARTERLY,
                ),
            )
        ),
        registry=registry_of(labelled),
    )
    assert result.skipped == ()


def test_a_decimal_kind_must_be_known_exactly_but_an_index_may_be_unlabelled() -> None:
    unlabelled = UnitRecord(text="Percent")
    rate_frame = monthly([4.1, 4.2], provider="alpha", unit=unlabelled)
    a = scripted("alpha", {"A": rate_frame})
    with pytest.raises(DataError, match="definition_mismatch"):
        resolve(
            concept((Candidate(provider="alpha", series="A"),), kind=UnitKind.RATE),
            registry=registry_of(a),
        )
    # The same frame is fine for an index concept: only decimal kinds are strict.
    ok = resolve(
        concept((Candidate(provider="alpha", series="A"),), kind=UnitKind.INDEX_LEVEL),
        registry=registry_of(a),
    )
    assert ok.skipped == ()
    assert replace(rate_frame.meta.unit).kind is None


def test_a_rate_and_a_ratio_may_answer_one_another() -> None:
    rate = UnitRecord(text="Percent", kind=UnitKind.RATE)
    a = scripted("alpha", {"A": monthly([0.01, 0.02], provider="alpha", unit=rate)})
    result = resolve(
        concept((Candidate(provider="alpha", series="A"),), kind=UnitKind.RATIO),
        registry=registry_of(a),
    )
    assert result.skipped == ()


def test_seasonal_adjustment_must_agree_unless_either_side_is_not_applicable() -> None:
    nsa = scripted(
        "alpha",
        {
            "A": monthly(
                DATA,
                provider="alpha",
                seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
            )
        },
    )
    sa = SeasonalAdjustment.SEASONALLY_ADJUSTED
    with pytest.raises(DataError, match="seasonal adjustment"):
        resolve(
            concept((Candidate(provider="alpha", series="A"),), seasonal=sa),
            registry=registry_of(nsa),
        )
    unspecified = concept((Candidate(provider="alpha", series="A"),))
    assert resolve(unspecified, registry=registry_of(nsa)).skipped == ()
    saar = scripted(
        "beta",
        {
            "B": monthly(
                DATA,
                provider="beta",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
            )
        },
    )
    assert (
        resolve(
            concept((Candidate(provider="beta", series="B"),), seasonal=sa),
            registry=registry_of(saar),
        ).skipped
        == ()
    )


def test_a_fiscal_year_end_that_differs_is_not_the_concept() -> None:
    fiscal = scripted(
        "alpha",
        {
            "A": series(
                ObservationFrequency.ANNUAL,
                [dt.date(2024, 9, 30), dt.date(2025, 9, 30)],
                [1.0, 2.0],
                provider="alpha",
                year_ends_in=9,
            )
        },
    )
    with pytest.raises(DataError, match="year ends in month 9"):
        resolve(
            concept(
                (Candidate(provider="alpha", series="A"),),
                frequency=ObservationFrequency.ANNUAL,
            ),
            registry=registry_of(fiscal),
        )
    ok = resolve(
        concept(
            (Candidate(provider="alpha", series="A"),),
            frequency=ObservationFrequency.ANNUAL,
            year_ends_in=9,
        ),
        registry=registry_of(fiscal),
    )
    assert ok.skipped == ()


# --- windows and transforms ---------------------------------------------------


def test_the_result_is_cut_to_the_window_and_the_record_names_it() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    result = resolve(
        concept((Candidate(provider="alpha", series="A"),)),
        start=dt.date(2024, 6, 1),
        end=dt.date(2024, 9, 30),
        registry=registry_of(a),
    )
    assert result.frame.index[0] == dt.date(2024, 6, 30)
    assert result.frame.index[-1] == dt.date(2024, 9, 30)
    assert result.source.observation_start == dt.date(2024, 6, 30)
    assert result.source.observation_end == dt.date(2024, 9, 30)


def test_transforms_run_in_order_and_are_recorded_as_canonical_text() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    result = resolve(
        concept(
            (
                Candidate(
                    provider="alpha",
                    series="A",
                    transforms=(
                        "pct_change(periods=1)",
                        "convert(method=mean, to=quarterly)",
                    ),
                ),
            ),
            kind=UnitKind.RETURN,
            frequency=ObservationFrequency.QUARTERLY,
        ),
        registry=registry_of(a),
    )
    assert result.source.transforms == (
        "pct_change",
        "convert(to=quarterly,method=mean)",
    )
    assert result.frame.meta.frequency is ObservationFrequency.QUARTERLY


def test_a_year_over_year_window_asks_for_the_year_before_the_start_and_trims_it() -> (
    None
):
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    result = resolve(
        concept(
            (Candidate(provider="alpha", series="A", transforms=("yoy",)),),
            kind=UnitKind.RATE,
        ),
        start=dt.date(2025, 1, 1),
        end=dt.date(2025, 6, 30),
        registry=registry_of(a),
    )
    (query,) = calls_of(a)
    assert query.start is not None
    assert query.start < dt.date(2024, 1, 1)  # more than a year of history
    assert query.end == dt.date(2025, 6, 30)
    assert as_series(result.frame).index[0] == dt.date(2025, 1, 31)
    assert all(
        v is not None for v in as_series(result.frame).values
    )  # the history filled it


def test_a_changes_only_transform_reads_the_whole_history_first() -> None:
    steps = series(
        ObservationFrequency.DAILY,
        [dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(10)],
        [1.0] * 4 + [2.0] * 3 + [3.0] * 3,
        provider="alpha",
    )
    a = scripted("alpha", {"A": steps})
    result = resolve(
        concept(
            (Candidate(provider="alpha", series="A", transforms=("changes_only",)),),
            frequency=ObservationFrequency.IRREGULAR,
        ),
        start=dt.date(2025, 1, 6),
        registry=registry_of(a),
    )
    (query,) = calls_of(a)
    assert query.start is None
    # Changes fell on 1 and 5 January (before the window) and on 8 January.
    assert as_series(result.frame).index == (dt.date(2025, 1, 8),)
    assert as_series(result.frame).values == (3.0,)


def test_a_window_with_no_observation_is_passed_over() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    b = scripted("beta", {"B": monthly(DATA, provider="beta", first=(2010, 1))})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A"),
                Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
            )
        ),
        start=dt.date(2011, 1, 1),
        end=dt.date(2011, 12, 31),
        registry=registry_of(a, b),
    )
    assert [s.reason for s in result.skipped] == ["no_observations"]
    assert result.source.provider == "beta"


def test_a_transform_that_cannot_be_applied_is_passed_over() -> None:
    a = scripted("alpha", {"A": monthly([1.0, -2.0, 3.0], provider="alpha")})
    b = scripted("beta", {"B": monthly([1.0, 2.0, 3.0], provider="beta")})
    result = resolve(
        concept(
            (
                Candidate(provider="alpha", series="A", transforms=("log",)),
                Candidate(
                    provider="beta",
                    series="B",
                    transforms=("log",),
                    tier=Tier.AGGREGATOR,
                ),
            ),
        ),
        registry=registry_of(a, b),
    )
    assert [s.reason for s in result.skipped] == ["transform_failed"]
    assert result.source.provider == "beta"


# --- parameters and windows required ------------------------------------------


def test_a_parameter_fills_the_series_key_after_it_is_checked() -> None:
    frame = monthly(DATA, provider="alpha", series_id="sep:2026-09-16")
    a = scripted("alpha", {"sep:2026-09-16": frame})
    meeting = Parameter(
        name="meeting",
        pattern=r"\d{4}-\d{2}-\d{2}",
        summary="A date.",
        example="2026-09-16",
    )
    one = concept(
        (Candidate(provider="alpha", series="sep:{meeting}"),), parameters=(meeting,)
    )
    result = resolve(one, parameters={"meeting": "2026-09-16"}, registry=registry_of(a))
    assert result.source.series_id == "sep:2026-09-16"
    with pytest.raises(InputError, match="needs the parameter 'meeting'"):
        resolve(one, registry=registry_of(a))
    with pytest.raises(InputError, match="must match"):
        resolve(one, parameters={"meeting": "../../etc"}, registry=registry_of(a))
    with pytest.raises(InputError, match="takes no parameter 'other'"):
        resolve(
            one,
            parameters={"meeting": "2026-09-16", "other": "x"},
            registry=registry_of(a),
        )


def test_a_concept_that_needs_a_window_refuses_without_both_dates() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    needs = concept((Candidate(provider="alpha", series="A"),), needs_window=True)
    with pytest.raises(InputError, match="needs both start and end"):
        resolve(needs, start=dt.date(2024, 1, 1), registry=registry_of(a))
    assert (
        resolve(
            needs,
            start=dt.date(2024, 1, 1),
            end=dt.date(2024, 12, 31),
            registry=registry_of(a),
        ).source.provider
        == "alpha"
    )


def test_a_start_after_the_end_is_refused() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    with pytest.raises(InputError, match="after end"):
        resolve(
            concept((Candidate(provider="alpha", series="A"),)),
            start=dt.date(2025, 1, 1),
            end=dt.date(2024, 1, 1),
            registry=registry_of(a),
        )


def test_the_provider_filter_keeps_only_that_providers_candidates() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    b = scripted("beta", {"B": monthly(DATA, provider="beta")})
    candidates = (
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    chosen = resolve(concept(candidates), provider="beta", registry=registry_of(a, b))
    assert chosen.source.provider == "beta"
    assert calls_of(a) == []
    with pytest.raises(InputError, match="no candidate from provider 'gamma'"):
        resolve(concept(candidates), provider="gamma", registry=registry_of(a, b))


def test_an_unknown_concept_id_names_the_close_ones() -> None:
    with pytest.raises(ConceptNotFoundError, match="did you mean"):
        resolve("us.unemployment.rat")


# --- tables -------------------------------------------------------------------


def _table() -> Table:
    rate = UnitRecord(text="Percent", kind=UnitKind.RATE)
    columns = tuple(
        ColumnMeta(
            name=name,
            unit=rate,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        )
        for name in ("BC_1MONTH", "BC_10YEAR", "OTHER")
    )
    meta = TableMeta(
        provider="alpha",
        table_id="curve",
        title="A curve",
        frequency=ObservationFrequency.MONTHLY,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    index = (month_end(2025, 1), month_end(2025, 2))
    return Table(index, columns, ((0.01, 0.02), (0.03, 0.04), (0.05, 0.06)), meta)


def test_a_series_concept_takes_a_column_of_a_table() -> None:
    a = scripted("alpha", {"curve": _table()})
    result = resolve(
        concept(
            (Candidate(provider="alpha", series="curve", column="BC_10YEAR"),),
            kind=UnitKind.RATE,
        ),
        registry=registry_of(a),
    )
    assert as_series(result.frame).values == (0.03, 0.04)
    assert result.source.series_id == "curve:BC_10YEAR"


def test_a_series_concept_over_a_table_with_no_column_named_is_passed_over() -> None:
    a = scripted("alpha", {"curve": _table()})
    with pytest.raises(DataError, match="needs a column of it"):
        resolve(
            concept((Candidate(provider="alpha", series="curve"),), kind=UnitKind.RATE),
            registry=registry_of(a),
        )
    with pytest.raises(DataError, match="has no column 'NOPE'"):
        resolve(
            concept(
                (Candidate(provider="alpha", series="curve", column="NOPE"),),
                kind=UnitKind.RATE,
            ),
            registry=registry_of(a),
        )


def test_a_table_concept_renames_selects_or_matches_columns() -> None:
    a = scripted("alpha", {"curve": _table()})
    renamed = resolve(
        concept(
            (
                Candidate(
                    provider="alpha",
                    series="curve",
                    columns=(("1m", "BC_1MONTH"), ("10y", "BC_10YEAR")),
                ),
            ),
            kind=UnitKind.RATE,
            shape=Shape.TABLE,
        ),
        registry=registry_of(a),
    )
    assert as_table(renamed.frame).column_names == ("1m", "10y")
    matched = resolve(
        concept(
            (Candidate(provider="alpha", series="curve", keep=r"^BC_"),),
            kind=UnitKind.RATE,
            shape=Shape.TABLE,
        ),
        registry=registry_of(a),
    )
    assert as_table(matched.frame).column_names == ("BC_1MONTH", "BC_10YEAR")
    everything = resolve(
        concept(
            (Candidate(provider="alpha", series="curve"),),
            kind=UnitKind.RATE,
            shape=Shape.TABLE,
        ),
        registry=registry_of(a),
    )
    assert len(as_table(everything.frame).column_names) == 3
    with pytest.raises(DataError, match="has no column 'MISSING'"):
        resolve(
            concept(
                (
                    Candidate(
                        provider="alpha",
                        series="curve",
                        columns=(("x", "MISSING"),),
                    ),
                ),
                kind=UnitKind.RATE,
                shape=Shape.TABLE,
            ),
            registry=registry_of(a),
        )
    with pytest.raises(DataError, match="matches"):
        resolve(
            concept(
                (Candidate(provider="alpha", series="curve", keep="zzz"),),
                kind=UnitKind.RATE,
                shape=Shape.TABLE,
            ),
            registry=registry_of(a),
        )


def test_a_table_concept_over_a_series_is_passed_over() -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    with pytest.raises(DataError, match="is a series, but"):
        resolve(
            concept(
                (Candidate(provider="alpha", series="A"),),
                kind=UnitKind.INDEX_LEVEL,
                shape=Shape.TABLE,
            ),
            registry=registry_of(a),
        )


# --- derived concepts ---------------------------------------------------------


def test_a_derived_concept_combines_two_concepts_and_records_both_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = scripted(
        "alpha", {"R": quarterly([105.0, 99.0, 110.0], provider="alpha", series_id="R")}
    )
    potential = scripted(
        "beta",
        {"P": quarterly([100.0] * 4, provider="beta", series_id="P")},
    )
    quarterly_ = ObservationFrequency.QUARTERLY
    operands = {
        "us.test.real": concept(
            (Candidate(provider="alpha", series="R"),),
            concept_id="us.test.real",
            frequency=quarterly_,
        ),
        "us.test.potential": concept(
            (Candidate(provider="beta", series="P"),),
            concept_id="us.test.potential",
            frequency=quarterly_,
        ),
    }
    monkeypatch.setattr(catalog, "CONCEPTS", operands)
    gap = concept(
        (
            Derived(
                operands=(Operand("us.test.real"), Operand("us.test.potential")),
                transform="ratio(excess=true)",
            ),
        ),
        concept_id="us.test.gap",
        kind=UnitKind.RATE,
        frequency=quarterly_,
    )
    result = resolve(gap, registry=registry_of(real, potential))
    assert [round(v, 6) for v in as_series(result.frame).values if v is not None] == [
        0.05,
        -0.01,
        0.1,
    ]
    assert [s.provider for s in result.sources] == ["alpha", "beta"]
    assert {s.concept for s in result.sources} == {"us.test.gap"}
    assert all(s.transforms[-1] == "ratio(excess=true)" for s in result.sources)
    assert result.providers == ("alpha", "beta")


def test_a_derived_concept_fails_when_an_operand_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = scripted("alpha", {"R": SeriesNotFoundError("alpha", "R")})
    fine = scripted(
        "beta", {"P": quarterly([100.0] * 4, provider="beta", series_id="P")}
    )
    quarterly_ = ObservationFrequency.QUARTERLY
    monkeypatch.setattr(
        catalog,
        "CONCEPTS",
        {
            "us.test.real": concept(
                (Candidate(provider="alpha", series="R"),),
                concept_id="us.test.real",
                frequency=quarterly_,
            ),
            "us.test.potential": concept(
                (Candidate(provider="beta", series="P"),),
                concept_id="us.test.potential",
                frequency=quarterly_,
            ),
        },
    )
    gap = concept(
        (
            Derived(
                operands=(Operand("us.test.real"), Operand("us.test.potential")),
                transform="ratio",
            ),
        ),
        concept_id="us.test.gap",
        kind=UnitKind.RATIO,
        frequency=quarterly_,
    )
    with pytest.raises(DataError, match="operand_failed"):
        resolve(gap, registry=registry_of(broken, fine))


def test_a_derived_concept_inherits_the_hosted_refusal_of_an_operand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = scripted(
        "alpha",
        {"R": quarterly([1.0] * 4, provider="alpha", terms=LIBRARY_TERMS)},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    fine = scripted(
        "beta", {"P": quarterly([100.0] * 4, provider="beta", series_id="P")}
    )
    quarterly_ = ObservationFrequency.QUARTERLY
    monkeypatch.setattr(
        catalog,
        "CONCEPTS",
        {
            "us.test.real": concept(
                (Candidate(provider="alpha", series="R"),),
                concept_id="us.test.real",
                frequency=quarterly_,
            ),
            "us.test.potential": concept(
                (Candidate(provider="beta", series="P"),),
                concept_id="us.test.potential",
                frequency=quarterly_,
            ),
        },
    )
    gap = concept(
        (
            Derived(
                operands=(Operand("us.test.real"), Operand("us.test.potential")),
                transform="ratio",
            ),
        ),
        concept_id="us.test.gap",
        kind=UnitKind.RATIO,
        frequency=quarterly_,
    )
    with pytest.raises(LicenceError):
        resolve(gap, mode=Mode.HOSTED, registry=registry_of(closed, fine))
