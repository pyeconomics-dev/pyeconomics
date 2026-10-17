# tests/providers/test_provider_contract.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The shared provider contract, run over the toy providers and every registered one.

Offline, each case replays its cassette. Under ``-m live`` the same cases go
through the real transport and the real keys, for registered providers only
(``uv run pytest -m live --force-enable-socket tests/providers``); the toys have
no real API.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest
from provider_contract import (
    _REPLAY_ONLY,
    check_cases,
    check_error_case,
    check_foreign_hosts_refused,
    check_hosted_mode,
    check_rate_limits_hold,
    check_registered,
    check_success_case,
    check_synthesize,
    live_key,
    load_cassette,
    replay,
    replay_key,
)
from toys import ToyJson, ToyVintage

from pyeconomics.data import DataProvider, TransportError, registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyeconomics.data.providers.base import Case

TOYS: tuple[type[DataProvider], ...] = (ToyJson, ToyVintage)
pytestmark = pytest.mark.filterwarnings("ignore:.*\\[yahoo_personal_use\\]")
REAL: tuple[type[DataProvider], ...] = tuple(
    type(registry.get(provider_id)) for provider_id in registry.ids()
)
ALL = (*TOYS, *REAL)


def _id(provider: type[DataProvider]) -> str:
    return provider.info.id


def _cases(providers: tuple[type[DataProvider], ...], *, errors: bool) -> list[Any]:
    return [
        pytest.param(provider, case, id=f"{_id(provider)}-{case.name}")
        for provider in providers
        for case in provider.cases
        if (case.expect is not None) is errors
    ]


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_the_provider_validates_and_is_found(provider: type[DataProvider]) -> None:
    check_registered(provider)


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_every_capability_and_required_error_has_a_cassette(
    provider: type[DataProvider],
) -> None:
    check_cases(provider)


@pytest.mark.parametrize(("provider", "case"), _cases(ALL, errors=False))
def test_a_success_cassette_replays_into_a_valid_result(
    provider: type[DataProvider], case: Case
) -> None:
    recorded_on = load_cassette(provider.info.id, case).recorded_on
    check_success_case(
        provider,
        case,
        replay(provider.info.id, case),
        recorded_on=recorded_on,
        key=replay_key(provider, case),
    )


@pytest.mark.parametrize(("provider", "case"), _cases(ALL, errors=True))
def test_an_error_cassette_maps_to_the_taxonomy(
    provider: type[DataProvider], case: Case
) -> None:
    check_error_case(
        provider, case, replay(provider.info.id, case), key=replay_key(provider, case)
    )


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_the_transport_refuses_a_foreign_host_and_http(
    provider: type[DataProvider],
) -> None:
    check_foreign_hosts_refused(provider)


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_the_rate_limiter_holds_on_a_fake_clock(provider: type[DataProvider]) -> None:
    check_rate_limits_hold(provider)


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_hosted_mode_refuses_every_class_but_hosted_safe_and_user_supplied(
    provider: type[DataProvider],
) -> None:
    check_hosted_mode(provider)


@pytest.mark.parametrize("provider", ALL, ids=_id)
def test_a_synthetic_source_has_a_synthesize_hook(
    provider: type[DataProvider],
) -> None:
    check_synthesize(provider)


# --- the live suite -----------------------------------------------------------

_NO_REAL = pytest.param(
    None,
    None,
    marks=pytest.mark.skip(
        reason="no data provider is registered yet (Step 6 adds them)"
    ),
    id="none-registered",
)


def _live(*, errors: bool) -> list[Any]:
    found = _cases(REAL, errors=errors)
    return found or [_NO_REAL]


def _once_more_after_a_passing_failure(check: Callable[[], None]) -> None:
    """Run a live check, and once more if the source failed in passing.

    A live source sometimes fails a request it answers when sent again (BLS's
    REQUEST_FAILED, a 5xx outlasting the transport's retries); the weekly run is
    an alarm, so one such failure must not raise it. A second one does.
    """
    try:
        check()
    except TransportError:
        check()


def _skip_if_barred(provider: type[DataProvider]) -> None:
    """The scheduled run skips a source whose terms bar automated collection."""
    if not provider.info.automated_collection and (
        os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("PYECONOMICS_LIVE_YFINANCE") != "1"
    ):
        pytest.skip("its terms bar automated collection: run it on a local machine")


@pytest.mark.live
@pytest.mark.parametrize(("provider", "case"), _live(errors=False))
def test_live_a_real_response_parses_into_a_valid_result(
    provider: type[DataProvider], case: Case
) -> None:
    _skip_if_barred(provider)
    from pyeconomics.data.transport import default_transport  # noqa: PLC0415

    _once_more_after_a_passing_failure(
        lambda: check_success_case(
            provider, case, default_transport(), key=live_key(case)
        )
    )


@pytest.mark.live
@pytest.mark.parametrize(("provider", "case"), _live(errors=True))
def test_live_a_real_failure_maps_to_the_taxonomy(
    provider: type[DataProvider], case: Case
) -> None:
    _skip_if_barred(provider)
    if case.expect in _REPLAY_ONLY or case.simulate is not None:
        pytest.skip("a live source is not made to rate-limit or fail on request")
    from pyeconomics.data.transport import default_transport  # noqa: PLC0415

    _once_more_after_a_passing_failure(
        lambda: check_error_case(
            provider, case, default_transport(), key=live_key(case)
        )
    )


def test_a_live_check_runs_once_more_after_a_passing_failure_only() -> None:
    calls: list[int] = []

    def flaky() -> None:
        calls.append(1)
        if len(calls) == 1:
            msg = "passing"
            raise TransportError(msg, provider="bls")

    _once_more_after_a_passing_failure(flaky)
    assert len(calls) == 2

    def broken() -> None:
        msg = "again"
        raise TransportError(msg, provider="bls")

    with pytest.raises(TransportError):
        _once_more_after_a_passing_failure(broken)
