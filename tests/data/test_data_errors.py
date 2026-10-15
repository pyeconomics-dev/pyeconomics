# tests/data/test_data_errors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.data.errors: the taxonomy, and messages that carry no query or secret."""

from __future__ import annotations

import secrets

import pytest

from pyeconomics.core import PyeconomicsError
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import (
    ConfigError,
    CredentialError,
    DataError,
    LicenceError,
    OfflineError,
    ProviderNotFoundError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
)
from pyeconomics.data.errors import scrub_urls

# User information with a password, generated at run time: a literal one in a
# URL is what secret scanners look for (the Phase 3 Credential rule).
USERINFO = f"someone:{secrets.token_hex(8)}"


@pytest.mark.parametrize(
    ("error", "builtin"),
    [
        (ProviderNotFoundError, LookupError),
        (SeriesNotFoundError, LookupError),
        (CredentialError, PermissionError),
        (LicenceError, PermissionError),
        (RateLimitError, RuntimeError),
        (TransportError, ConnectionError),
        (OfflineError, ConnectionError),
        (ResponseError, ValueError),
        (ConfigError, ValueError),
    ],
)
def test_every_error_is_a_data_error_and_its_builtin(
    error: type[DataError], builtin: type[Exception]
) -> None:
    assert issubclass(error, DataError)
    assert issubclass(error, builtin)
    assert issubclass(DataError, PyeconomicsError)


@pytest.mark.parametrize(
    "error", [CredentialError, TransportError, OfflineError, ResponseError, ConfigError]
)
def test_message_errors_keep_the_message_and_the_provider(
    error: type[DataError],
) -> None:
    raised = error("no key is set; set FRED_API_KEY", provider="fred")
    assert str(raised) == "no key is set; set FRED_API_KEY"
    assert raised.provider == "fred"
    assert error("x").provider is None


def test_one_except_clause_catches_them_all() -> None:
    errors = [
        ProviderNotFoundError("x"),
        SeriesNotFoundError("fred", "X"),
        LicenceError("no", provider="fred", licence=LicenceClass.LIBRARY_ONLY),
        RateLimitError("too many", provider="bls"),
        OfflineError("no cached copy", provider="bea"),
    ]
    for error in errors:
        with pytest.raises(PyeconomicsError):
            raise error


def test_provider_not_found_suggests_close_ids() -> None:
    error = ProviderNotFoundError("fredd", close_matches=("fred", "frb"))
    assert str(error).endswith("did you mean 'fred' or 'frb'?")
    assert error.provider == "fredd"
    assert error.close_matches == ("fred", "frb")
    assert (
        str(ProviderNotFoundError("x")) == "no data provider is registered with id 'x'"
    )


def test_series_not_found_names_the_series() -> None:
    error = SeriesNotFoundError("bls", "CUUR0000SA0")
    assert (error.provider, error.series_id) == ("bls", "CUUR0000SA0")


def test_licence_error_names_the_class_and_terms() -> None:
    error = LicenceError(
        "hosted mode refuses it",
        provider="ken_french",
        licence=LicenceClass.LIBRARY_ONLY,
    )
    assert str(error) == "ken_french is library-only: hosted mode refuses it"
    assert error.licence is LicenceClass.LIBRARY_ONLY
    assert error.terms_url is None


def test_rate_limit_error_keeps_the_wait() -> None:
    error = RateLimitError("limit held", provider="sec_edgar", retry_after=1.5)
    assert error.retry_after == 1.5
    assert RateLimitError("limit held", provider="bls").retry_after is None


@pytest.mark.parametrize(
    ("message", "scrubbed"),
    [
        (
            "GET https://api.example.org/v1/observations?series_id=GDP&page=2 failed",
            "GET https://api.example.org/v1/observations failed",
        ),
        (
            f"from https://{USERINFO}@api.example.org:8443/v1/x#frag",
            "from https://api.example.org:8443/v1/x",
        ),
        (
            "two: https://a.example.org/x?y=1 and http://b.example.org/?z=2.",
            "two: https://a.example.org/x and http://b.example.org/",
        ),
        ("'https://api.example.org/x?k=v'", "'https://api.example.org/x'"),
        ("bad https://[::1/x?k=v", "bad <url>"),
        ("no URL here", "no URL here"),
    ],
)
def test_urls_lose_their_user_information_query_and_fragment(
    message: str, scrubbed: str
) -> None:
    assert scrub_urls(message) == scrubbed
    assert str(TransportError(message, provider="fred")) == scrubbed


def test_every_error_message_is_scrubbed() -> None:
    query = "https://api.example.org/data?id=1&token=abc"
    errors: list[DataError] = [
        CredentialError(f"refused at {query}"),
        LicenceError(f"see {query}", provider="p", licence=LicenceClass.BYOK),
        RateLimitError(f"limited at {query}", provider="p"),
        OfflineError(f"no copy of {query}"),
        ResponseError(f"bad body from {query}"),
        ConfigError(f"bad setting {query}"),
    ]
    assert [str(error) for error in errors if "token" in str(error)] == []
