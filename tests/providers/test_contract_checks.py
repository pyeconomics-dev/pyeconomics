# tests/providers/test_contract_checks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The contract checks fail for a provider that breaks the contract.

A shared suite is only as good as what it rejects. Each test breaks a toy in one
way and expects the matching check to fail.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
import toys
from provider_contract import (
    check_cases,
    check_error_case,
    check_registered,
    check_success_case,
    check_synthesize,
    replay,
)
from toys import ToyJson, ToyVintage

from pyeconomics.core.errors import RegistryError
from pyeconomics.data import (
    Capability,
    DataProvider,
    LicenceClass,
    SeriesNotFoundError,
    TransportError,
)


def variant(base: type[DataProvider], **changes: Any) -> type[DataProvider]:
    return type("Broken", (base,), changes)


def case(provider: type[DataProvider], name: str) -> Any:
    return next(c for c in provider.cases if c.name == name)


def test_percent_that_was_not_converted_to_a_decimal_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        toys, "_percent", lambda raw: None if raw == "." else float(raw)
    )
    fetch = case(ToyJson, "fetch_ok")
    with pytest.raises(AssertionError, match="percent, not a decimal"):
        check_success_case(ToyJson, fetch, replay("toy_json", fetch))


def test_a_provider_missing_a_capabilitys_case_is_caught() -> None:
    no_search = variant(
        ToyJson,
        cases=tuple(c for c in ToyJson.cases if c.operation is not Capability.SEARCH),
    )
    with pytest.raises(AssertionError, match="no success case for search"):
        check_cases(no_search)


def test_a_provider_missing_the_required_error_cases_is_caught() -> None:
    no_limit = variant(
        ToyJson, cases=tuple(c for c in ToyJson.cases if c.name != "error_rate_limited")
    )
    with pytest.raises(AssertionError, match="RateLimitError"):
        check_cases(no_limit)
    keyed_without_401 = variant(
        ToyJson, cases=tuple(c for c in ToyJson.cases if c.name != "error_unauthorized")
    )
    with pytest.raises(AssertionError, match="CredentialError"):
        check_cases(keyed_without_401)
    check_cases(ToyVintage)  # a keyless source needs no credential case


def test_a_case_without_a_cassette_is_caught() -> None:
    extra = replace(case(ToyJson, "search_ok"), name="has_no_file")
    with pytest.raises(AssertionError, match="no cassette for"):
        check_cases(variant(ToyJson, cases=(*ToyJson.cases, extra)))


def test_a_case_for_a_capability_the_provider_does_not_declare_is_caught() -> None:
    with pytest.raises(AssertionError, match="undeclared capabilities"):
        check_cases(
            variant(
                ToyJson, info=replace(ToyJson.info, capabilities=(Capability.FETCH,))
            )
        )


def test_an_error_cassette_that_raises_a_different_error_is_caught() -> None:
    wrong = replace(case(ToyJson, "error_not_found"), expect=TransportError)
    # pytest.raises lets the unexpected error through: the check fails with it.
    with pytest.raises(SeriesNotFoundError):
        check_error_case(ToyJson, wrong, replay("toy_json", wrong))


def test_a_library_only_source_without_a_synthesize_hook_is_caught() -> None:
    terms = replace(ToyJson.info.terms, licence=LicenceClass.LIBRARY_ONLY)
    library = variant(
        ToyJson,
        info=replace(ToyJson.info, terms=terms),
        synthesize=DataProvider.synthesize,
    )
    with pytest.raises(AssertionError, match="implement synthesize"):
        check_synthesize(library)
    check_synthesize(ToyVintage)
    check_synthesize(ToyJson)


def test_an_invalid_provider_is_caught_by_the_registration_check() -> None:
    with pytest.raises(RegistryError):
        check_registered(variant(ToyJson, info=replace(ToyJson.info, rate_limits=())))
    check_registered(ToyJson)
