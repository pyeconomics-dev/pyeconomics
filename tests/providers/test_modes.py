# tests/providers/test_modes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Library and hosted mode, and the refusal hosted mode makes per licence class."""

from __future__ import annotations

from dataclasses import replace

import pytest
from stubs import STUB_TERMS

from pyeconomics.data import (
    ConfigError,
    LicenceClass,
    LicenceError,
    Mode,
    config,
    configure,
    current_mode,
    require_allowed,
)


def test_library_mode_is_the_default() -> None:
    assert current_mode() is Mode.LIBRARY


def test_configure_selects_hosted_mode() -> None:
    configure(mode="hosted")
    assert current_mode() is Mode.HOSTED


def test_the_environment_selects_hosted_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    config.reset()
    assert current_mode() is Mode.HOSTED


def test_an_unknown_mode_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_MODE", "cloud")
    config.reset()
    with pytest.raises(ConfigError):
        current_mode()


@pytest.mark.parametrize("licence", list(LicenceClass), ids=lambda c: c.value)
def test_library_mode_serves_every_class(licence: LicenceClass) -> None:
    require_allowed(replace(STUB_TERMS, licence=licence), provider="demo")


@pytest.mark.parametrize("licence", list(LicenceClass), ids=lambda c: c.value)
def test_hosted_mode_serves_only_hosted_safe_and_user_supplied(
    licence: LicenceClass,
) -> None:
    configure(mode="hosted")
    terms = replace(STUB_TERMS, licence=licence)
    if licence in {LicenceClass.HOSTED_SAFE, LicenceClass.USER_SUPPLIED}:
        require_allowed(terms, provider="demo")
        return
    with pytest.raises(LicenceError) as caught:
        require_allowed(terms, provider="demo")
    assert caught.value.licence is licence
    assert caught.value.terms_url == terms.terms_url
    assert licence.value in str(caught.value)
    assert terms.terms_url in str(caught.value)
    assert isinstance(caught.value, PermissionError)


def test_an_explicit_mode_overrides_the_settings() -> None:
    terms = replace(STUB_TERMS, licence=LicenceClass.BYOK)
    require_allowed(terms, provider="demo", mode=Mode.LIBRARY)
    with pytest.raises(LicenceError):
        require_allowed(terms, provider="demo", mode=Mode.HOSTED)
    configure(mode="hosted")
    require_allowed(terms, provider="demo", mode=Mode.LIBRARY)
