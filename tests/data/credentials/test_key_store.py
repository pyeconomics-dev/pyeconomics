# tests/data/credentials/test_key_store.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Writing the keyring step, and naming a key's source (Phase 4 Step 4).

``store_key`` and ``delete_key`` are the only code that writes a key, and only
to the OS keyring (here the isolated fixture's in-memory one); ``key_source``
names the kind of source the chain would read, never the value. A stored key is
compared as a boolean, so a failure never prints it.
"""

from __future__ import annotations

import secrets
import sys
from typing import TYPE_CHECKING

import pytest
from leakcheck import LeakCheck, canary

from pyeconomics.core.errors import InputError, MissingOptionalDependencyError
from pyeconomics.data import CredentialError, KeySource, Secret
from pyeconomics.data.credentials import (
    KEYRING_SERVICE,
    delete_key,
    key_source,
    store_key,
    withheld,
)

if TYPE_CHECKING:
    from config_isolation import Home, Isolation


def held(isolation: Isolation, provider: str) -> str | None:
    return isolation.keyring.passwords.get((KEYRING_SERVICE, provider))


def test_store_key_writes_the_keyring_step(isolated: Isolation) -> None:
    key = canary("fred")
    store_key("fred", key.held)
    stored = held(isolated, "fred")
    assert stored is not None
    assert secrets.compare_digest(stored, key.value)
    assert key_source("fred") is KeySource.KEYRING


def test_store_key_refuses_another_providers_key_or_a_plain_value(
    isolated: Isolation,
) -> None:
    with pytest.raises(CredentialError, match="the key is for bea, not fred"):
        store_key("fred", canary("bea").held)
    with pytest.raises(InputError, match="stored as a Secret, not str"):
        store_key("fred", secrets.token_hex(16))  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
    with pytest.raises(InputError):
        store_key("FRED", canary("fred").held)
    assert isolated.keyring.passwords == {}


def test_delete_key_says_whether_one_was_there(isolated: Isolation) -> None:
    isolated.keyring.set_password(KEYRING_SERVICE, "fred", secrets.token_hex(16))
    assert delete_key("fred") is True
    assert held(isolated, "fred") is None
    assert delete_key("fred") is False


def test_both_need_the_keyring_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "keyring", None)
    with pytest.raises(MissingOptionalDependencyError) as caught:
        store_key("fred", canary("fred").held)
    assert caught.value.extra == "keyring"
    with pytest.raises(MissingOptionalDependencyError):
        delete_key("fred")
    assert key_source("fred") is None


@pytest.mark.parametrize("action", ["store", "delete"])
def test_a_backend_failure_names_its_type_never_its_message(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    key = canary("fred")

    def fail(*_arguments: object) -> None:
        msg = f"backend failure holding {key.value}"
        raise RuntimeError(msg)

    monkeypatch.setattr(isolated.keyring, "set_password", fail)
    monkeypatch.setattr(isolated.keyring, "get_password", fail)
    call = (
        (lambda: store_key("fred", key.held))
        if action == "store"
        else (lambda: delete_key("fred"))
    )
    with pytest.raises(CredentialError) as caught:
        call()
    assert caught.value.provider == "fred"
    assert f"could not {action} the fred key (RuntimeError)" in str(caught.value)
    assert caught.value.__cause__ is None
    check = LeakCheck(key)
    check.exception(caught.value)
    check.assert_clean()


def test_key_source_names_the_first_source_in_chain_order(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch, home: Home
) -> None:
    assert key_source("fred") is None
    isolated.keyring.set_password(KEYRING_SERVICE, "fred", secrets.token_hex(16))
    assert key_source("fred") is KeySource.KEYRING
    home.write_dotenv(f"FRED_API_KEY={secrets.token_hex(16)}\n")
    assert key_source("fred", posix=False) is KeySource.DOTENV
    monkeypatch.setenv("FRED_API_KEY", secrets.token_hex(16))
    assert key_source("fred") is KeySource.ENVIRONMENT
    with withheld("fred"):
        assert key_source("fred") is None


def test_an_unusable_key_still_names_its_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRED_API_KEY", "short")
    assert key_source("fred") is KeySource.ENVIRONMENT


def test_a_stored_key_is_found_by_the_chain() -> None:
    from pyeconomics.data import resolve_key  # noqa: PLC0415

    key = canary("bls")
    store_key("bls", key.held)
    assert resolve_key("bls") == Secret("bls", key.value)
