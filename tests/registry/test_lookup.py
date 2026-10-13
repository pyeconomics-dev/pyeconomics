# tests/registry/test_lookup.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Looking models up: ids, domains, aliases and the ``pyeconomics.registry`` facade."""

from __future__ import annotations

import pytest
import toy_models as tm

from pyeconomics import registry
from pyeconomics.core import (
    Alias,
    InputError,
    ModelNotFoundError,
    PyeconomicsDeprecationWarning,
    Registry,
)
from pyeconomics.core import registry as core_registry

TOY = tm.toy_registry()
ALIAS = "foundations.toy_tvm"


def test_ids_are_sorted() -> None:
    assert TOY.ids() == (
        "econometrics.toy_extra",
        "fixed_income.toy_zero_coupon",
        "foundations.toy_mean_return",
        "foundations.toy_time_value",
    )


def test_a_model_is_found_by_its_id() -> None:
    assert TOY.get("fixed_income.toy_zero_coupon") is tm.zero_coupon
    assert TOY.resolve("fixed_income.toy_zero_coupon") is tm.zero_coupon


def test_an_alias_returns_the_canonical_model_and_warns() -> None:
    with pytest.warns(PyeconomicsDeprecationWarning) as caught:
        found = TOY.get(ALIAS)
    assert found is tm.time_value
    message = str(caught[0].message)
    assert ALIAS in message
    assert "foundations.toy_time_value" in message  # the replacement
    assert "2.0.0" in message  # the release that removes the alias
    assert issubclass(caught[0].category, FutureWarning)
    assert caught[0].filename == __file__  # points at the caller


def test_resolve_follows_an_alias_too() -> None:
    with pytest.warns(PyeconomicsDeprecationWarning, match=ALIAS) as caught:
        assert TOY.resolve(ALIAS) is tm.time_value
    assert caught[0].filename == __file__


def test_an_alias_names_the_release_that_removes_it() -> None:
    renamed = tm.variant(tm.time_value, aliases=(Alias(ALIAS, removed_in="3.0.0"),))
    with pytest.warns(
        PyeconomicsDeprecationWarning, match=r"removed in pyeconomics 3\.0\.0"
    ):
        tm.toy_registry(renamed).get(ALIAS)


def test_an_unknown_id_lists_close_matches() -> None:
    with pytest.raises(ModelNotFoundError) as caught:
        TOY.get("foundations.toy_time_valu")
    assert caught.value.model_id == "foundations.toy_time_valu"
    assert "foundations.toy_time_value" in caught.value.close_matches
    assert "did you mean" in str(caught.value)
    assert isinstance(caught.value, LookupError)


def test_close_matches_include_aliases() -> None:
    with pytest.raises(ModelNotFoundError) as caught:
        TOY.get("foundations.toy_tv")
    assert ALIAS in caught.value.close_matches


def test_an_id_with_nothing_close_has_no_suggestions() -> None:
    with pytest.raises(ModelNotFoundError) as caught:
        TOY.get("zzzzzzzzzz")
    assert caught.value.close_matches == ()
    assert "did you mean" not in str(caught.value)


def test_models_are_sorted_by_id_and_filtered_by_domain() -> None:
    assert [m.id for m in TOY.models()] == list(TOY.ids())
    assert TOY.models("foundations") == (tm.mean_return, tm.time_value)
    assert TOY.models("risk") == ()


def test_an_unknown_domain_is_an_input_error() -> None:
    with pytest.raises(InputError, match="unknown domain 'astrology'"):
        TOY.models("astrology")


def test_domains_are_the_registered_ones_in_domain_order() -> None:
    assert TOY.domains() == ("foundations", "econometrics", "fixed_income")
    assert tm.toy_registry(tm.zero_coupon).domains() == ("fixed_income",)


def test_aliases_map_to_canonical_ids_read_only() -> None:
    aliases = TOY.aliases()
    assert dict(aliases) == {ALIAS: "foundations.toy_time_value"}
    with pytest.raises(TypeError):
        aliases["x"] = "y"  # type: ignore[index]


def test_a_registry_is_independent_of_the_installed_one() -> None:
    assert TOY.ids() != ()
    assert not set(TOY.ids()) & set(registry.ids())


def test_a_conflicted_registry_still_answers_with_the_first_registration() -> None:
    twin = tm.variant(tm.zero_coupon)
    both = Registry.from_models(tm.zero_coupon, twin, distribution="toy-dist")
    assert both.conflicts
    assert both.get(tm.zero_coupon.id) is tm.zero_coupon


# --- the facade --------------------------------------------------------------


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> Registry:
    monkeypatch.setattr(core_registry._CACHE, "registry", TOY)  # noqa: SLF001
    return TOY


def test_the_facade_reads_the_installed_registry(installed: Registry) -> None:
    assert registry.ids() == installed.ids()
    assert registry.get(tm.zero_coupon.id) is tm.zero_coupon
    assert registry.models("foundations") == (tm.mean_return, tm.time_value)
    assert registry.domains() == ("foundations", "econometrics", "fixed_income")
    assert registry.resolve(tm.zero_coupon.id) is tm.zero_coupon


@pytest.mark.usefixtures("installed")
def test_the_facade_warns_at_the_callers_line() -> None:
    with pytest.warns(PyeconomicsDeprecationWarning, match=ALIAS) as got:
        assert registry.get(ALIAS) is tm.time_value
    assert got[0].filename == __file__
    with pytest.warns(PyeconomicsDeprecationWarning, match=ALIAS) as resolved:
        assert registry.resolve(ALIAS) is tm.time_value
    assert resolved[0].filename == __file__


@pytest.mark.usefixtures("installed")
def test_the_facade_raises_not_found() -> None:
    with pytest.raises(ModelNotFoundError):
        registry.get("fixed_income.nope")
    with pytest.raises(ModelNotFoundError):
        registry.resolve("fixed_income.nope")


@pytest.mark.usefixtures("installed")
def test_the_facade_validates_the_installed_registry_by_default() -> None:
    registry.validate(released={})
    registry.validate(TOY, released={})


@pytest.mark.parametrize("bad", [None, 5, 1.5, ("a", "b")])
def test_an_id_that_is_not_a_string_is_not_found(bad: object) -> None:
    with pytest.raises(ModelNotFoundError) as caught:
        TOY.get(bad)  # type: ignore[arg-type]
    assert caught.value.close_matches == ()
