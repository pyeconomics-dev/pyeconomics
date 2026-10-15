# tests/data/credentials/test_redaction.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Redaction: the registry, the scrubbers, the record factory and the raise.

Each test starts with an empty registry and restores the log-record factory
afterwards (the suite-wide ``isolated`` fixture).
"""

from __future__ import annotations

import logging
import secrets
import traceback
from urllib.parse import quote, quote_plus

import pytest
from leakcheck import LeakCheck, canary

from pyeconomics.data import TransportError, redaction
from pyeconomics.data.redaction import (
    MASK,
    MAX_MESSAGE_LENGTH,
    call_scrubbed,
    describe_exception,
    install,
    installed,
    register,
    scrub_headers,
    scrub_record,
    scrub_text,
    scrub_url,
    scrub_urls,
    unregister,
)


def special_key() -> str:
    """A random key with characters URL encoding changes."""
    return f"{secrets.token_hex(6)}/+={secrets.token_hex(6)}&?"


def test_register_refuses_short_and_non_text_values() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        register(secrets.token_hex(3))
    with pytest.raises(TypeError, match="only text"):
        register(12345678)
    unregister(12345678)
    unregister(secrets.token_hex(8))
    assert len(redaction._REGISTRY) == 0  # noqa: SLF001 - the registry itself


def test_registrations_are_counted() -> None:
    value = secrets.token_hex(8)
    register(value)
    register(value)
    unregister(value)
    still = scrub_text(value) == MASK
    unregister(value)
    gone = scrub_text(value) == value
    assert (still, gone, len(redaction._REGISTRY)) == (True, True, 0)  # noqa: SLF001


def test_every_url_encoded_form_is_scrubbed() -> None:
    value = special_key()
    register(value)
    forms = {
        "plain": value,
        "quote": quote(value, safe=""),
        "quote_plus": quote_plus(value, safe=""),
        "lower": quote(value, safe="").lower(),
    }
    remaining = {
        name: scrub_text(f"before {form} after") != f"before {MASK} after"
        for name, form in forms.items()
    }
    assert [name for name, left in remaining.items() if left] == []


def test_a_longer_key_holding_a_shorter_one_is_replaced_whole() -> None:
    short = secrets.token_hex(8)
    longer = short + secrets.token_hex(8)
    register(short)
    register(longer)
    whole = scrub_text(f"[{longer}]") == f"[{MASK}]"
    assert whole


@pytest.mark.parametrize(
    ("text", "scrubbed"),
    [
        ("/fred/series?api_key=VALUE&id=GDP", "/fred/series?api_key=[redacted]&id=GDP"),
        ("?registrationkey=VALUE", "?registrationkey=[redacted]"),
        ("/data?UserID=VALUE&Year=2025", "/data?UserID=[redacted]&Year=2025"),
        ("&KEY=VALUE;", "&KEY=[redacted];"),
        ("#access_token=VALUE&state=1", "#access_token=[redacted]&state=1"),
        ('"/x?token=VALUE" 200', '"/x?token=[redacted]" 200'),
        ("monkey=VALUE&keys=2", "monkey=VALUE&keys=2"),
    ],
)
def test_credential_parameters_are_scrubbed_in_text(text: str, scrubbed: str) -> None:
    assert scrub_text(text) == scrubbed


def test_scrub_url_drops_userinfo_and_credential_parameters() -> None:
    value = secrets.token_hex(16)
    register(value)
    url = (
        f"https://someone:{secrets.token_hex(4)}@api.example.org:8443/v1/{value}"
        f"?API_KEY=a&id=GDP&api%5Fkey=b&Token=c&file_type=json#part"
    )
    assert scrub_url(url) == (
        f"https://api.example.org:8443/v1/{MASK}?id=GDP&file_type=json#part"
    )


@pytest.mark.parametrize(
    ("url", "scrubbed"),
    [
        ("https://[2001:db8::1]:443/x?key=a&b=1", "https://[2001:db8::1]:443/x?b=1"),
        ("https://api.example.org/x?&&key=a", "https://api.example.org/x"),
        ("/relative/path?token=a&page=2", "/relative/path?page=2"),
        (
            "https://api.example.org:99999/x?key=a",
            "https://api.example.org:99999/x?key=[redacted]",
        ),
        ("https://[::1/x?key=a", "https://[::1/x?key=[redacted]"),
    ],
)
def test_scrub_url_keeps_hosts_and_falls_back_to_text(url: str, scrubbed: str) -> None:
    assert scrub_url(url) == scrubbed


def test_scrub_urls_strips_queries_and_names_malformed_urls() -> None:
    assert scrub_urls("see https://a.example.org/x?q=1#f and https://[::1/y") == (
        "see https://a.example.org/x and <url>"
    )


def test_scrub_headers_drops_credentials_and_scrubs_the_rest() -> None:
    contact = f"tester {secrets.token_hex(6)}@example.org"
    register(contact)
    headers = {
        "Authorization": "Bearer abc",
        "Proxy-Authorization": "Basic abc",
        "Cookie": "session=abc",
        "Set-Cookie": "session=abc",
        "X-Api-Key": "abc",
        "X-Auth-Token": "abc",
        "Accept": "application/json",
        "User-Agent": f"pyeconomics/1.0 {contact}",
    }
    assert scrub_headers(headers) == {
        "Accept": "application/json",
        "User-Agent": f"pyeconomics/1.0 {MASK}",
    }


def record(message: str, *args: object, **extra: object) -> logging.LogRecord:
    """Build a record the way a logger does, through the current factory."""
    factory = logging.getLogRecordFactory()
    return factory(
        "pyeconomics.test",
        logging.DEBUG,
        __file__,
        1,
        message,
        args,
        extra.get("exc_info"),
        None,
        extra.get("sinfo"),
    )


def test_install_chains_the_default_factory_once() -> None:
    assert not installed()
    install()
    install()
    factory = logging.getLogRecordFactory()
    assert installed()
    assert factory.previous is logging.LogRecord  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    held = canary()
    built = record("key %s and %r", held.value, held.held)
    assert (built.getMessage(), built.args) == (
        f"key {MASK} and <Secret leakcheck_toy: redacted>",
        (),
    )


def test_install_keeps_a_factory_installed_before() -> None:
    class Tagged(logging.LogRecord):
        """A record type another library installed first."""

    logging.setLogRecordFactory(Tagged)
    install()
    held = canary()
    built = record("%s", held.value)
    assert isinstance(built, Tagged)
    assert built.getMessage() == MASK
    assert logging.getLogRecordFactory().previous is Tagged  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]


def test_a_record_whose_arguments_do_not_fit_its_message_is_kept_without_them() -> None:
    held = canary()
    built = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "no placeholder", (held.value,), None
    )
    scrub_record(built)
    assert built.getMessage() == (
        "no placeholder [log arguments dropped: they did not match the message]"
    )


def test_an_unprintable_message_is_named_by_its_type() -> None:
    class Unprintable:
        def __str__(self) -> str:
            raise RuntimeError

    built = logging.LogRecord(
        "x", logging.INFO, __file__, 1, Unprintable(), ("a",), None
    )
    scrub_record(built)
    assert built.getMessage().startswith("<unprintable Unprintable>")


def failure(message: str) -> tuple[type[BaseException], BaseException, None]:
    """The exc_info a record carries for an exception, without a traceback."""
    error = ValueError(message)
    return type(error), error, None


def test_a_traceback_holding_a_key_is_stored_scrubbed() -> None:
    held = canary()
    built = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "failed", (), failure(f"bad {held.value}")
    )
    scrub_record(built)
    assert built.exc_info is None
    assert built.exc_text is not None
    assert built.exc_text.endswith(f"ValueError: bad {MASK}")
    formatted = logging.Formatter().format(built)
    assert LeakCheck(held).found_in({"formatted": [formatted]}) == []


def test_a_traceback_without_a_key_is_left_to_the_handlers() -> None:
    canary()
    info = failure("an ordinary failure")
    built = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", (), info)
    scrub_record(built)
    assert (built.exc_info, built.exc_text) == (info, None)


def test_preformatted_tracebacks_and_stacks_are_scrubbed() -> None:
    held = canary()
    built = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "m", (), None, sinfo=f"Stack: {held.value}"
    )
    built.exc_text = f"Traceback: {held.value}"
    scrub_record(built)
    assert (built.exc_text, built.stack_info) == (
        f"Traceback: {MASK}",
        f"Stack: {MASK}",
    )


def test_a_traceback_that_cannot_be_formatted_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary()

    def broken(_error: BaseException) -> list[str]:
        raise RecursionError

    monkeypatch.setattr(traceback, "format_exception", broken)
    built = logging.LogRecord(
        "x",
        logging.ERROR,
        __file__,
        1,
        "m",
        (),
        failure("x"),
    )
    scrub_record(built)
    assert (built.exc_info, built.exc_text) == (
        None,
        "[traceback dropped: it could not be formatted]",
    )


def test_describe_exception_scrubs_and_bounds_the_message() -> None:
    held = canary()
    error = OSError(
        f"GET https://u:p@api.example.org/v1?api_key={held.value} {held.value}"
    )
    assert (
        describe_exception(error) == f"OSError: GET https://api.example.org/v1 {MASK}"
    )
    assert describe_exception(RuntimeError()) == "RuntimeError"
    long = describe_exception(RuntimeError("x" * (MAX_MESSAGE_LENGTH + 10)))
    assert long == "RuntimeError: " + "x" * MAX_MESSAGE_LENGTH + "..."


def test_call_scrubbed_returns_or_raises_with_nothing_chained() -> None:
    held = canary()
    assert call_scrubbed(lambda: 42, RuntimeError) == 42

    def fetch() -> None:
        message = f"GET /series?api_key={held.value} failed: {held.value}"
        raise ConnectionError(message)

    with pytest.raises(TransportError) as raised:
        call_scrubbed(fetch, lambda message: TransportError(message, provider="toy"))
    error = raised.value
    assert (error.__context__, error.__cause__, error.provider) == (None, None, "toy")
    assert str(error) == f"ConnectionError: GET /series?api_key={MASK} failed: {MASK}"
    check = LeakCheck(held)
    check.exception(error)
    check.assert_clean()


def test_call_scrubbed_lets_other_exceptions_through_unchanged() -> None:
    def interrupted() -> None:
        missing = "series"
        raise KeyError(missing)

    with pytest.raises(KeyError):
        call_scrubbed(interrupted, RuntimeError, catch=(ConnectionError,))
