# tests/data/cache/test_cache_offline.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Offline mode: only the cache answers, whatever its age, and nothing is requested."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

import pytest
from cache_support import (
    Forbidden,
    Storable,
    WallClock,
    replay_case,
    scripted,
    toy_query,
)
from stubs import Scripted
from toys import JSON_HOST, ToyJson, ToyVintage

from pyeconomics.data import (
    Fetched,
    OfflineError,
    Request,
    config,
    configure,
    current_mode,
    settings,
)
from pyeconomics.data.cache import store as store_module
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from config_isolation import Isolation

    from pyeconomics.data import DataProvider, Transport

pytestmark = pytest.mark.usefixtures("wall")


class Refuse:
    """A transport that fails the test if offline mode ever asks it for anything."""

    def send(self, *_args: object, **_kwargs: object) -> NoReturn:
        msg = "offline mode sent a request"
        raise AssertionError(msg)


def toy(transport: Transport) -> Fetched:
    query = toy_query(ToyJson, "fetch_ok")
    return ToyJson().fetch_with_origin(query, transport=transport)


def test_offline_mode_serves_an_expired_entry_and_says_so(wall: WallClock) -> None:
    online = toy(replay_case(ToyJson, "fetch_ok"))
    wall.advance(days=400)  # long past any time to live
    configure(offline=True)
    served = toy(Refuse())
    assert served.frame == online.frame
    assert served.origin.cache_hit is True
    assert served.origin.served_offline is True
    assert served.origin.warnings == ("served_offline",)
    record = served.source()
    assert record.served_offline is True
    assert record.cache_hit is True
    assert record.warnings == ("served_offline",)
    assert record.retrieved_at == online.frame.meta.retrieved_at  # the original time
    assert record.retrieved_at != wall.now


def test_the_environment_switches_offline_mode_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    online = toy(replay_case(ToyJson, "fetch_ok"))
    monkeypatch.setenv("PYECONOMICS_OFFLINE", "1")
    config.reset()
    assert settings().offline is True
    assert toy(Refuse()).frame == online.frame


def test_offline_mode_can_be_switched_off_again() -> None:
    toy(replay_case(ToyJson, "fetch_ok"))
    configure(offline=True)
    assert toy(Refuse()).origin.served_offline is True
    configure(offline=False)
    assert toy(replay_case(ToyJson, "fetch_ok")).origin.served_offline is False


def test_a_miss_in_offline_mode_raises_and_names_the_provider_and_series(
    isolated: Isolation,
) -> None:
    configure(offline=True)
    with pytest.raises(OfflineError) as caught:
        toy(Refuse())
    error = caught.value
    assert isinstance(error, ConnectionError)
    assert error.provider == "toy_json"
    message = str(error)
    assert "toy_json" in message
    assert "TOYRATE" in message
    assert "no cached copy" in message
    assert str(isolated.cache_dir) not in message
    assert not isolated.cache_dir.exists()  # a miss creates nothing


def test_a_provider_that_forbids_storage_can_never_be_served_offline(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(offline=True)

    def refuse() -> NoReturn:
        msg = "the store was reached"
        raise AssertionError(msg)

    monkeypatch.setattr(store_module, "_driver", refuse)
    query = toy_query(ToyVintage, "fetch_all")
    with pytest.raises(OfflineError) as caught:
        ToyVintage().fetch_with_origin(query, transport=Refuse())
    message = str(caught.value)
    assert "toy_vintage cannot be served offline" in message
    assert "terms forbid storing its data" in message
    assert "TOYGDP" in message
    assert not isolated.cache_dir.exists()


def test_a_series_that_forbids_storage_is_a_miss_that_says_it_is_never_cached() -> None:
    online = ToyJson().fetch_with_origin(
        toy_query(ToyJson, "fetch_restricted"),
        transport=replay_case(ToyJson, "fetch_restricted"),
    )
    assert online.frame is not None
    configure(offline=True)
    with pytest.raises(OfflineError, match="never cached"):
        ToyJson().fetch_with_origin(
            toy_query(ToyJson, "fetch_restricted"), transport=Refuse()
        )


def test_a_query_that_cannot_be_cached_cannot_be_served_offline() -> None:
    from pyeconomics.data import Query  # noqa: PLC0415

    class KeyedQuery(Query):
        api_key: str = "x"

    class Keyed(Storable):
        query_type = KeyedQuery

    configure(offline=True)
    with pytest.raises(OfflineError, match="cannot be cached"):
        Keyed().fetch_with_origin({"series": ("S",)}, transport=Refuse())


@pytest.mark.parametrize("operation", ["search", "describe", "vintages"])
def test_operations_the_cache_does_not_serve_are_refused_offline(
    operation: str,
) -> None:
    configure(offline=True)
    provider: DataProvider = ToyVintage() if operation == "vintages" else ToyJson()
    argument = {"search": "rate", "describe": "TOYRATE", "vintages": "TOYGDP"}[
        operation
    ]
    with pytest.raises(OfflineError, match="sends no request"):
        getattr(provider, operation)(argument, transport=Refuse())


def test_a_stub_provider_that_forbids_storage_names_itself_offline() -> None:
    configure(offline=True)
    with pytest.raises(OfflineError, match="forbidden_stub cannot be served offline"):
        Forbidden().fetch_with_origin({"series": ("S",)}, transport=Refuse())


def test_the_https_transport_refuses_to_send_offline() -> None:
    configure(offline=True)
    request = Request(host=JSON_HOST, path="/v1/observations", series="TOYRATE")
    with pytest.raises(OfflineError, match="sends no request"):
        HttpTransport().send(ToyJson.info, request)


def test_offline_mode_does_not_change_the_library_or_hosted_mode() -> None:
    configure(offline=True)
    assert current_mode().value == "library"


def test_an_entry_a_live_fetch_stored_serves_the_next_offline_call_from_any_state(
    wall: WallClock,
) -> None:
    provider, transport = Storable(), scripted(200)
    first = provider.fetch_with_origin({"series": ("S",)}, transport=transport)
    wall.advance(days=1)
    configure(offline=True)
    again = provider.fetch_with_origin({"series": ("S",)}, transport=Scripted())
    assert again.frame == first.frame
    assert again.origin.served_offline is True
