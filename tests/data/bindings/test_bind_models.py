# tests/data/bindings/test_bind_models.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``bind_model``: real-time vintages by default, revised data labelled, overrides.

The toy models of ``bound_support`` bind to real catalog concepts; scripted
providers answer, so the resolver's gates and the binding layer run for real
and offline (ADR-0011 decisions 6 and 16).
"""

from __future__ import annotations

import datetime as dt

import bound_support as bs
import pytest
from scripted import calls_of, registry_of

from pyeconomics.core import (
    AsOf,
    Binding,
    InputError,
    LicenceClass,
    VintagePolicy,
)
from pyeconomics.data import (
    ConceptNotFoundError,
    CredentialError,
    DataError,
    Mode,
    OfflineError,
    bind_model,
)

PAST = dt.date(2024, 3, 20)
APRIL = dt.date(2024, 4, 10)
LATER = dt.date(2024, 9, 30)


def unemployment_at(day: dt.date | None) -> tuple[object, str | None]:
    """Bind the default profile and return the value and the record's vintage."""
    bound = bind_model(bs.unemployment, as_of=day, registry=bs.world())
    (record,) = bound.sources
    return bound.values["unemployment"], record.vintage


# --- real time, by default ---------------------------------------------------------


def test_a_real_time_bind_reads_the_vintage_published_by_the_date() -> None:
    # On 2024-03-20 January had been revised (0.038) and February was the first
    # release (0.039): the values a forecaster could have read that day.
    value, vintage = unemployment_at(PAST)
    assert (value, vintage) == (0.039, "as_of:2024-03-20")


def test_a_later_date_reads_the_later_vintage() -> None:
    value, _ = unemployment_at(APRIL)
    assert value == 0.038  # March's first release; April is not out until May 3
    value, _ = unemployment_at(LATER)
    assert value == 0.041


def test_the_record_names_the_series_the_vintage_the_rule_and_the_field() -> None:
    bound = bind_model(bs.unemployment, as_of=PAST, registry=bs.world())
    (record,) = bound.sources
    assert (record.provider, record.series_id) == ("fred", "UNRATE")
    assert record.field == "unemployment"
    assert record.concept == "us.unemployment.rate"
    assert record.vintage == "as_of:2024-03-20"
    assert record.transforms == ("asof(date=2024-03-20)",)
    assert record.observation_start == record.observation_end == dt.date(2024, 2, 29)
    assert record.realtime is not None
    assert record.realtime.covers(PAST)
    assert record.licence is LicenceClass.LIBRARY_ONLY
    assert record.retrieved_at == bs.FETCHED
    assert record.fallback_chain == ("bls", "fred")
    assert record.warnings[-1] == "skipped_bls_vintage_unsupported"
    assert "revised_data" not in record.warnings
    assert bound.revised == ()
    assert bound.overridden == ()


def test_without_a_date_the_latest_data_is_read_at_its_last_observation() -> None:
    bound = bind_model(bs.unemployment, registry=bs.world())
    (record,) = bound.sources
    assert bound.values["unemployment"] == 0.041
    assert record.provider == "bls"  # nothing asks for a vintage: the originator
    assert record.vintage == "latest"
    assert record.transforms == ("asof(date=2024-06-30)",)
    assert "revised_data" not in record.warnings
    assert bound.as_of is None


def test_a_date_before_any_observation_is_published_raises() -> None:
    with pytest.raises(DataError, match=r"us\.unemployment\.rate.*no observation"):
        bind_model(bs.unemployment, as_of=dt.date(2024, 1, 15), registry=bs.world())


# --- revised data is labelled -------------------------------------------------------


def test_the_latest_policy_reads_revised_data_and_says_so() -> None:
    bound = bind_model(
        bs.unemployment, as_of=PAST, profile="revised", registry=bs.world()
    )
    (record,) = bound.sources
    # The same date reads February's revised 0.040 (published April 5th), not the
    # 0.039 a forecaster had on the 20th of March.
    assert bound.values["unemployment"] == 0.040
    assert record.provider == "bls"
    assert record.vintage == "latest"
    assert "revised_data" in record.warnings
    assert bound.revised == ("unemployment",)


def test_the_vintage_argument_overrides_every_bindings_policy() -> None:
    bound = bind_model(
        bs.unemployment,
        as_of=PAST,
        vintage=VintagePolicy.LATEST,
        registry=bs.world(),
    )
    assert bound.values["unemployment"] == 0.040
    assert bound.revised == ("unemployment",)
    again = bind_model(
        bs.unemployment, as_of=PAST, vintage="latest", registry=bs.world()
    )
    assert (again.values, again.revised) == (bound.values, bound.revised)
    assert again.sources[0].cache_hit  # the isolated cache served the second bind


def test_a_source_without_vintages_is_read_as_revised_data_with_a_warning() -> None:
    bound = bind_model(
        bs.unemployment, as_of=dt.date(2024, 5, 15), profile="uk", registry=bs.world()
    )
    (record,) = bound.sources
    assert (record.provider, record.concept) == ("oecd", "gb.inflation.cpi.yoy")
    assert bound.values["unemployment"] == 0.023  # April 2024, as it stands today
    assert "revised_data" in record.warnings
    assert record.vintage == "latest"
    assert bound.revised == ("unemployment",)


def test_hosted_mode_reads_the_originator_and_labels_it_revised() -> None:
    # FRED keeps the vintages but is library-only, so hosted mode cannot use it:
    # no source it may use keeps vintages, and the binding says so.
    bound = bind_model(
        bs.unemployment, as_of=PAST, mode=Mode.HOSTED, registry=bs.world()
    )
    (record,) = bound.sources
    assert record.provider == "bls"
    assert record.licence is LicenceClass.HOSTED_SAFE
    assert bound.values["unemployment"] == 0.040
    assert bound.revised == ("unemployment",)


def test_a_missing_key_is_not_turned_into_revised_data() -> None:
    # A source that could answer in real time but cannot is an error to fix, not
    # a reason to quietly read revised data.
    with pytest.raises(CredentialError, match="key_missing"):
        bind_model(
            bs.unemployment,
            as_of=PAST,
            registry=registry_of(bs.bls(), bs.fred(keyed=True)),
        )


def test_a_note_on_the_source_reaches_the_record_as_a_warning() -> None:
    # No date: nothing is revised against, so the warning is the source's own.
    bound = bind_model(bs.output, registry=bs.world())
    (record,) = bound.sources
    assert record.provider == "bea"
    assert "revised_data" in record.warnings
    assert bound.revised == ("output",)


# --- overrides ----------------------------------------------------------------------


def test_an_override_replaces_the_bound_value_and_is_recorded_as_user_supplied() -> (
    None
):
    asked = [bs.bls(), bs.fred()]
    bound = bind_model(
        bs.unemployment,
        as_of=PAST,
        overrides={"unemployment": 0.05},
        registry=registry_of(*asked),
    )
    assert bound.values["unemployment"] == 0.05
    (record,) = bound.sources
    assert (record.provider, record.licence) == ("user", LicenceClass.USER_SUPPLIED)
    assert (record.field, record.concept) == ("unemployment", "us.unemployment.rate")
    assert record.retrieved_at is None
    assert record.terms_url is None
    assert bound.overridden == ("unemployment",)
    assert all(calls_of(provider) == [] for provider in asked)


def test_a_field_without_a_binding_is_an_ordinary_input() -> None:
    bound = bind_model(
        bs.unemployment, as_of=PAST, overrides={"weight": 2.0}, registry=bs.world()
    )
    assert bound.values["weight"] == 2.0
    assert [s.field for s in bound.sources] == ["unemployment"]
    assert bound.overridden == ()


def test_an_override_names_a_real_input_field() -> None:
    with pytest.raises(InputError, match="no input field 'nope'"):
        bind_model(bs.unemployment, overrides={"nope": 1.0}, registry=bs.world())


# --- profiles, concepts and errors ---------------------------------------------------


def test_a_profile_is_a_complete_set_and_an_unknown_one_lists_the_known() -> None:
    with pytest.raises(InputError, match=r"no profile 'other'.*default, revised, uk"):
        bind_model(bs.unemployment, profile="other", registry=bs.world())
    with pytest.raises(InputError, match="declares no data bindings"):
        bind_model(bs.plain, registry=bs.world())


def test_concepts_rebind_a_field_to_a_concept_of_the_same_kind_and_frequency() -> None:
    bound = bind_model(
        bs.unemployment,
        as_of=dt.date(2024, 5, 15),
        concepts={"unemployment": "gb.inflation.cpi.yoy"},
        registry=bs.world(),
    )
    (record,) = bound.sources
    assert record.concept == "gb.inflation.cpi.yoy"
    assert bound.values["unemployment"] == 0.023


@pytest.mark.parametrize(
    ("concept", "why"),
    [
        ("us.output.real_gdp", "money at quarterly"),  # another kind and frequency
        ("us.neutral_rate.hlw", "at quarterly"),  # the same kind, another frequency
    ],
)
def test_a_rebind_to_another_kind_or_frequency_is_refused(
    concept: str, why: str
) -> None:
    with pytest.raises(InputError, match=f"cannot replace.*{why}"):
        bind_model(
            bs.unemployment,
            as_of=PAST,
            concepts={"unemployment": concept},
            registry=bs.world(),
        )


def test_a_rebind_names_a_bound_field_and_a_catalog_concept() -> None:
    with pytest.raises(InputError, match="binds no field 'weight'"):
        bind_model(bs.unemployment, concepts={"weight": "gb.x.y"}, registry=bs.world())
    with pytest.raises(ConceptNotFoundError, match=r"us\.unemployment\.rat"):
        bind_model(
            bs.unemployment,
            concepts={"unemployment": "us.unemployment.rat"},
            registry=bs.world(),
        )


def test_a_concept_nothing_can_satisfy_raises_naming_the_concept() -> None:
    with pytest.raises(DataError, match=r"us\.unemployment\.rate cannot be resolved"):
        bind_model(bs.unemployment, as_of=PAST, registry=registry_of(bs.bea()))


def test_offline_mode_with_nothing_cached_propagates() -> None:
    from pyeconomics.data import configure  # noqa: PLC0415 - settings, per test

    configure(offline=True)
    with pytest.raises(OfflineError):
        bind_model(bs.unemployment, as_of=PAST, registry=bs.world())
    with pytest.raises(OfflineError):
        bind_model(bs.unemployment, registry=bs.world())


def test_a_date_outside_the_data_layers_bounds_is_refused() -> None:
    with pytest.raises(InputError):
        bind_model(bs.unemployment, as_of=dt.date(1500, 1, 1), registry=bs.world())


def test_an_unknown_vintage_policy_is_refused() -> None:
    with pytest.raises(InputError, match="vintage"):
        bind_model(bs.unemployment, vintage="eventually", registry=bs.world())


# --- transforms, windows and units ---------------------------------------------------


def test_one_concept_bound_to_two_fields_is_fetched_once() -> None:
    fred = bs.fred()
    providers = registry_of(bs.bls(), fred)
    bound = bind_model(bs.unemployment_change, as_of=APRIL, registry=providers)
    assert calls_of(fred) == [calls_of(fred)[0]]  # one request for two fields
    # March 0.038 less February 0.040, read as of April 10th.
    assert bound.values["unemployment"] == 0.038
    assert bound.values["change"] == pytest.approx(-0.002)
    assert [s.field for s in bound.sources] == ["change", "unemployment"]
    change = bound.sources[0]
    assert change.transforms == ("diff", "asof(date=2024-04-10)")


def test_a_window_binding_reads_the_last_observations_as_a_tuple() -> None:
    bound = bind_model(bs.unemployment_window, as_of=LATER, registry=bs.world())
    assert bound.values["history"] == (0.038, 0.039, 0.040, 0.041)
    (record,) = bound.sources
    assert record.transforms == ("window(count=4,date=2024-09-30)",)
    assert record.observation_start == dt.date(2024, 3, 31)
    assert record.observation_end == dt.date(2024, 6, 30)


def test_a_window_with_too_few_observations_raises() -> None:
    with pytest.raises(DataError, match="fewer than the 4"):
        bind_model(bs.unemployment_window, as_of=APRIL, registry=bs.world())


def test_a_period_binding_reads_the_quarter_that_contains_the_date() -> None:
    bound = bind_model(
        bs.output, as_of=dt.date(2024, 2, 15), registry=bs.world(bs.bea())
    )
    (record,) = bound.sources
    assert record.transforms == ("period(date=2024-02-15)",)
    assert record.observation_end == dt.date(2024, 3, 31)
    assert bound.values["output"] == 22_100.0 * 1e9  # billions, delivered in dollars


def test_a_period_binding_refuses_a_quarter_the_source_has_not_published() -> None:
    with pytest.raises(DataError, match=r"us\.output\.real_gdp.*period ending"):
        bind_model(bs.output, as_of=dt.date(2024, 12, 15), registry=bs.world(bs.bea()))


def test_the_binding_dataclass_defaults_are_the_documented_ones() -> None:
    binding = Binding("unemployment", "us.unemployment.rate")
    assert binding.as_of is AsOf.LAST_ON_OR_BEFORE
    assert binding.vintage is VintagePolicy.REAL_TIME
    assert (binding.window, binding.transform, binding.profile) == (
        None,
        None,
        "default",
    )
