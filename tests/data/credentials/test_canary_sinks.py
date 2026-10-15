# tests/data/credentials/test_canary_sinks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The canary suite: no key reaches a log, an exception, a warning or an export.

ADR-0011 decision 13 and the Phase 3 Step 3 acceptance criteria. Each test
plants a random canary (tests/data/leakcheck.py) where a careless path would
pick it up, collects the sinks, and asserts the list of sinks that hold it is
empty. A failure names sinks, never the canary. The harness's own tests at
the end prove each kind of sink would catch a leak.

Steps 4, 5 and 12 add the transport, the cache file and bound manifests.
"""

from __future__ import annotations

import logging
import secrets
import warnings
from typing import TYPE_CHECKING

import pytest
import toy_models as tm
from leakcheck import (
    LOGGERS,
    TOY_PROVIDER,
    Canary,
    LeakCheck,
    canary,
    contact_canary,
    log_urllib3_request,
)

from pyeconomics.core import run_model
from pyeconomics.data import (
    ConfigError,
    CredentialError,
    DataError,
    DataWarning,
    ResponseError,
    TransportError,
    has_key,
    key_variable,
    redaction,
    resolve_key,
    settings,
)
from pyeconomics.data.credentials import parse_dotenv

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from config_isolation import Home


def special_canary() -> Canary:
    """A canary whose URL-encoded forms differ from it."""
    return canary(value=f"{secrets.token_hex(10)}/+={secrets.token_hex(10)}")


def resolved_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, planted: Canary
) -> None:
    """Put the canary in its provider's variable and read it through the chain."""
    monkeypatch.setenv(key_variable(TOY_PROVIDER), planted.value)
    resolve_key(TOY_PROVIDER)


# --- Log records -----------------------------------------------------------


@pytest.mark.parametrize("make", [canary, special_canary], ids=["hex", "special"])
@pytest.mark.usefixtures("home")
def test_no_log_record_from_any_logger_carries_the_key(
    monkeypatch: pytest.MonkeyPatch, make: Callable[[], Canary]
) -> None:
    planted = make()
    resolved_from_the_environment(monkeypatch, planted)
    value = planted.value
    encoded = planted.needles()[-1]
    check = LeakCheck(planted)
    with check.logs():
        root = logging.getLogger()
        package = logging.getLogger("pyeconomics.data.providers")
        root.debug("key %s", value)
        root.info(f"inline {value}")
        package.debug("encoded %s and %r", encoded, planted.held)
        package.warning("mapping %(key)s", {"key": value})
        package.error("no placeholder", value)
        package.debug("stack", stack_info=True)
        failure = f"request failed for {value}"
        try:
            raise ValueError(failure)  # noqa: TRY301 - planted inside the handler
        except ValueError:
            package.exception("fetch failed")
        log_urllib3_request(f"/fred/series/observations?series_id=GDP&api_key={value}")
        log_urllib3_request(f"/v1/series/{encoded}/data?registrationkey={value}")
    expected = {f"log:{name}" for name in ("root", "pyeconomics.data.providers")}
    assert expected | {"log:urllib3.connectionpool"} <= set(check.sinks)
    check.assert_clean()


@pytest.mark.usefixtures("home")
def test_the_harness_reads_every_logger_it_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planted = canary()
    resolved_from_the_environment(monkeypatch, planted)
    check = LeakCheck(planted)
    with check.logs():
        for name in LOGGERS:
            logging.getLogger(name or None).debug("%s", planted.value)
    assert sorted(check.sinks) == ["log:pyeconomics", "log:root", "log:urllib3"]
    check.assert_clean()


# --- Exceptions and their tracebacks ----------------------------------------


@pytest.mark.usefixtures("home")
def test_data_errors_and_scrubbed_raises_carry_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planted = special_canary()
    resolved_from_the_environment(monkeypatch, planted)
    value, encoded = planted.value, planted.needles()[-1]
    check = LeakCheck(planted)
    check.exception(
        ResponseError(
            f"bad body from https://api.example.org/x?api_key={value} {value}"
        )
    )
    check.exception(DataError(f"encoded {encoded}", provider=TOY_PROVIDER))

    def request() -> None:
        message = f"GET /x?api_key={value}: reset; key {encoded}"
        raise ConnectionError(message)

    with pytest.raises(TransportError) as raised:
        redaction.call_scrubbed(
            request, lambda message: TransportError(message, provider=TOY_PROVIDER)
        )
    assert (raised.value.__context__, raised.value.__cause__) == (None, None)
    check.exception(raised.value)
    assert sorted(check.sinks) == [
        "exception:DataError",
        "exception:ResponseError",
        "exception:TransportError",
    ]
    check.assert_clean()


def test_credential_and_config_errors_carry_no_key(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    planted = canary()
    check = LeakCheck(planted)
    value = planted.value
    variable = key_variable(TOY_PROVIDER)

    def collect(error_type: type[Exception], call: object) -> None:
        assert callable(call)
        with pytest.raises(error_type) as raised:
            call()
        check.exception(raised.value)

    monkeypatch.setenv(variable, f"{value} with a space")
    collect(CredentialError, lambda: resolve_key(TOY_PROVIDER))
    collect(CredentialError, lambda: resolve_key(TOY_PROVIDER, f"{value}\n{value}"))
    monkeypatch.delenv(variable)
    home.write_dotenv(f"{variable}='{value}\n")
    collect(ConfigError, lambda: resolve_key(TOY_PROVIDER))
    collect(ConfigError, lambda: parse_dotenv(f"export {variable}={value}"))
    collect(ConfigError, lambda: parse_dotenv(f"{variable}={value} {value}"))
    home.write_dotenv("")
    home.write_config(f'[fred]\napi_key = "{value}"\n')
    collect(ConfigError, settings)
    home.write_config(f'mode = "{value}"\n')
    collect(ConfigError, settings)
    home.write_config(f'mode = "{value}\n')
    collect(ConfigError, settings)
    home.write_config("")
    monkeypatch.setenv("PYECONOMICS_FRED_TOKEN", value)
    collect(ConfigError, settings)
    monkeypatch.delenv("PYECONOMICS_FRED_TOKEN")
    monkeypatch.setenv("PYECONOMICS_OFFLINE", value)
    collect(ConfigError, settings)
    assert len(check.sinks) == 2  # CredentialError, ConfigError
    check.assert_clean()


# --- Warnings ---------------------------------------------------------------


class LeakyKeyring:
    """A keyring backend whose failure message holds the key."""

    def __init__(self, value: str) -> None:
        self.value = value

    def get_password(self, service: str, username: str) -> str | None:
        message = f"{service}/{username} failed with {self.value}"
        raise OSError(message)


def test_no_warning_carries_the_key(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    import keyring.core  # noqa: PLC0415 - the test group installs the extra

    planted = canary()
    resolved_from_the_environment(monkeypatch, planted)
    monkeypatch.delenv(key_variable(TOY_PROVIDER))
    check = LeakCheck(planted)
    with check.warnings():
        warnings.warn(
            DataWarning("planted", f"a warning naming {planted.value}"), stacklevel=1
        )
        home.write_dotenv(f"OTHER=1\n# {planted.value}\n", private=False)
        has_key(TOY_PROVIDER, posix=True)
        monkeypatch.setattr(
            keyring.core, "_keyring_backend", LeakyKeyring(planted.value)
        )
        has_key(TOY_PROVIDER, posix=False)
    assert set(check.sinks) == {"warning:DataWarning"}
    assert len(check.sinks["warning:DataWarning"]) == 6  # 3 warnings, 2 forms each
    check.assert_clean()


# --- Manifests and Result exports ------------------------------------------


def test_no_manifest_or_export_carries_the_key_or_the_contact(
    home: Home, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    planted = canary()
    contact = contact_canary()
    resolved_from_the_environment(monkeypatch, planted)
    home.write_dotenv(f"{key_variable('other_toy')}={planted.value}\n")
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", contact.value)
    assert settings().sec_contact is not None
    result = run_model(tm.zero_coupon, face_value=100, rate=0.05, years=10)
    for needles in (planted, contact):
        check = LeakCheck(needles)
        check.result(result, tmp_path)
        assert sorted(check.sinks) == [
            "manifest",
            "result:to_dict",
            "result:to_json",
            "result:to_pandas",
            "result:to_parquet",
        ]
        check.assert_clean()


@pytest.mark.usefixtures("home")
def test_the_contact_reaches_no_log_message_or_printed_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contact = contact_canary()
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", contact.value)
    current = settings()
    redaction.install()
    check = LeakCheck(contact)
    check.add("settings", repr(current))
    check.add("settings", str(current))
    check.add("settings", current.model_dump_json())
    with check.logs():
        logging.getLogger("pyeconomics.data").debug("User-Agent: x %s", contact.value)
    check.exception(DataError(f"EDGAR refused {contact.value}"))
    check.assert_clean()


# --- The harness catches what it is built to catch --------------------------


@pytest.mark.usefixtures("home")
def test_the_harness_reports_only_the_names_of_leaking_sinks() -> None:
    planted = canary()
    check = LeakCheck(planted)
    check.add("clean", "nothing here")
    check.add("plain", f"x {planted.value} y")
    check.add("bytes", f"{planted.value}".encode())
    assert check.leaks() == ["bytes", "plain"]
    with pytest.raises(AssertionError) as failed:
        check.assert_clean()
    message = str(failed.value)
    assert message == "the canary reached 2 sink(s): bytes, plain"
    assert check.found_in({"assertion": [message]}) == []
    with pytest.raises(AssertionError, match="collected no sink"):
        LeakCheck(planted).assert_clean()


@pytest.mark.usefixtures("home")
def test_without_redaction_the_log_and_exception_sinks_see_a_leak() -> None:
    planted = canary()
    assert not redaction.installed()
    check = LeakCheck(planted)
    control = logging.getLogger("leakcheck.control")
    control.propagate = False
    try:
        with check.logs("leakcheck.control"):
            control.debug("raw %s", planted.value)
    finally:
        control.propagate = True
    try:
        try:
            raise KeyError(planted.value)  # noqa: TRY301 - planted
        except KeyError as inner:
            raise RuntimeError("wrapped") from inner  # noqa: EM101
    except RuntimeError as chained:
        check.exception(chained)
    assert check.leaks() == ["exception:RuntimeError", "log:leakcheck.control"]


@pytest.mark.usefixtures("home")
def test_the_warning_and_export_sinks_see_a_leak(tmp_path: Path) -> None:
    planted = canary()
    check = LeakCheck(planted)
    with check.warnings():
        warnings.warn(f"plain {planted.value}", UserWarning, stacklevel=1)
    result = run_model(tm.zero_coupon, face_value=100, rate=0.05, years=10)
    check.result(result, tmp_path)
    check.add("manifest", planted.value)
    assert check.leaks() == ["manifest", "warning:UserWarning"]
