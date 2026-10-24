# tests/data/credentials/test_key_chain.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The key chain: argument, environment, .env, keyring (ADR-0011 decision 12).

Every test runs in its own configuration home (the ``home`` fixture), with no
real key in the environment and an in-memory keyring. Keys are random; a
found key is checked by comparing Secrets, which print only a mask.
"""

from __future__ import annotations

import itertools
import logging
import os
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from leakcheck import LeakCheck, canary

from pyeconomics.core.errors import InputError
from pyeconomics.data import (
    ConfigError,
    CredentialError,
    DataWarning,
    KeySource,
    Secret,
    has_key,
    key_variable,
    redaction,
    resolve_key,
)
from pyeconomics.data.config import GUIDE_URL
from pyeconomics.data.credentials import chain

if TYPE_CHECKING:
    from config_isolation import Home

PROVIDER = "toy_chain"
VARIABLE = "TOY_CHAIN_API_KEY"
SOURCES = ("environment", "dotenv", "keyring")


def plant(
    home: Home, monkeypatch: pytest.MonkeyPatch, sources: tuple[str, ...]
) -> dict[str, str]:
    """Put a different random key in each named source; return them by source."""
    keys = {source: secrets.token_hex(16) for source in sources}
    if "environment" in keys:
        monkeypatch.setenv(VARIABLE, keys["environment"])
    if "dotenv" in keys:
        home.write_dotenv(f"# keys\n{VARIABLE}={keys['dotenv']}\n")
    if "keyring" in keys:
        home.keyring.set_password("pyeconomics", PROVIDER, keys["keyring"])
    return keys


def test_key_variable_is_the_upper_case_id_with_api_key() -> None:
    assert [key_variable(p) for p in ("fred", "bls", "bea", "census", "openfigi")] == [
        "FRED_API_KEY",
        "BLS_API_KEY",
        "BEA_API_KEY",
        "CENSUS_API_KEY",
        "OPENFIGI_API_KEY",
    ]
    with pytest.raises(InputError):
        key_variable("FRED")


@pytest.mark.parametrize(
    "sources",
    [
        combination
        for size in range(1, len(SOURCES) + 1)
        for combination in itertools.combinations(SOURCES, size)
    ],
    ids="+".join,
)
def test_the_first_source_in_order_answers(
    home: Home, monkeypatch: pytest.MonkeyPatch, sources: tuple[str, ...]
) -> None:
    keys = plant(home, monkeypatch, sources)
    expected = Secret(PROVIDER, keys[sources[0]])
    found = resolve_key(PROVIDER) == expected
    assert found
    assert has_key(PROVIDER)


@pytest.mark.parametrize(
    "sources", [(), ("environment",), ("environment", "dotenv", "keyring")]
)
def test_an_explicit_argument_beats_every_source(
    home: Home, monkeypatch: pytest.MonkeyPatch, sources: tuple[str, ...]
) -> None:
    plant(home, monkeypatch, sources)
    given = secrets.token_hex(16)
    as_text = resolve_key(PROVIDER, given) == Secret(PROVIDER, given)
    held = Secret(PROVIDER, secrets.token_hex(16))
    assert as_text
    assert resolve_key(PROVIDER, held) is held


@pytest.mark.usefixtures("home")
def test_an_explicit_secret_for_another_provider_is_refused() -> None:
    with pytest.raises(CredentialError, match="is for fred, not toy_chain"):
        resolve_key(PROVIDER, Secret("fred", secrets.token_hex(16)))


def test_an_empty_explicit_argument_is_refused_not_skipped(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    plant(home, monkeypatch, ("environment",))
    with pytest.raises(CredentialError, match="from the argument is empty"):
        resolve_key(PROVIDER, "  ")


def test_the_environment_beats_the_dotenv_file_and_is_never_overridden(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys = plant(home, monkeypatch, ("environment", "dotenv"))
    found = resolve_key(PROVIDER) == Secret(PROVIDER, keys["environment"])
    unchanged = os.environ[VARIABLE] == keys["environment"]
    assert (found, unchanged) == (True, True)


def test_the_dotenv_file_is_never_loaded_into_the_environment(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys = plant(home, monkeypatch, ("dotenv",))
    home.write_dotenv(f"{VARIABLE}={keys['dotenv']}\nOTHER_SETTING=1\n")
    found = resolve_key(PROVIDER) == Secret(PROVIDER, keys["dotenv"])
    assert found
    assert VARIABLE not in os.environ
    assert "OTHER_SETTING" not in os.environ


def test_empty_values_count_as_unset(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = secrets.token_hex(16)
    monkeypatch.setenv(VARIABLE, "   ")
    home.write_dotenv(f"{VARIABLE}=\n")
    home.keyring.set_password("pyeconomics", PROVIDER, f"  {key}\n")
    found = resolve_key(PROVIDER) == Secret(PROVIDER, key)
    assert found


def test_the_working_directorys_dotenv_file_is_never_read(home: Home) -> None:
    (home.work_dir / ".env").write_bytes(
        f"{VARIABLE}={secrets.token_hex(16)}\n".encode()
    )
    assert not has_key(PROVIDER)
    with pytest.raises(CredentialError):
        resolve_key(PROVIDER)


def test_a_broken_dotenv_file_is_an_error_only_when_it_is_read(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.write_dotenv("export SOMETHING=1\n")
    with pytest.raises(ConfigError, match=r"line 1 of the \.env file"):
        resolve_key(PROVIDER)
    with pytest.raises(ConfigError, match=r"line 1 of the \.env file"):
        has_key(PROVIDER)
    keys = plant(home, monkeypatch, ("environment",))
    found = resolve_key(PROVIDER) == Secret(PROVIDER, keys["environment"])
    assert found


def test_a_dotenv_file_that_is_not_utf8_or_cannot_be_read(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.write_dotenv(b"TOY_CHAIN_API_KEY=\xff\xfe\n")
    with pytest.raises(ConfigError, match="is not UTF-8 text"):
        resolve_key(PROVIDER)

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(13, "denied", str(home.config_dir / ".env"))

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", refuse)
        with pytest.raises(
            ConfigError, match=r"cannot be read \(PermissionError\)"
        ) as failed:
            resolve_key(PROVIDER)
    assert failed.value.__context__ is None
    assert str(home.config_dir) not in str(failed.value)


@pytest.mark.usefixtures("home")
def test_no_source_raises_naming_provider_variable_command_and_guide() -> None:
    assert not has_key(PROVIDER)
    with pytest.raises(CredentialError) as missing:
        resolve_key(PROVIDER)
    message = str(missing.value)
    assert isinstance(missing.value, PermissionError)
    assert missing.value.provider == PROVIDER
    for part in (
        f"no {PROVIDER} key was found",
        f"Set the {VARIABLE} environment variable",
        f"add {VARIABLE} to the .env file in the pyeconomics configuration directory",
        f"`pyeconomics keys set {PROVIDER}`",
        GUIDE_URL,
    ):
        assert part in message


@pytest.mark.parametrize(
    ("source", "where"),
    [
        ("environment", f"from the environment variable {VARIABLE} "),
        ("dotenv", f"from {VARIABLE} in the .env file"),
        ("keyring", "from the OS keyring (service 'pyeconomics') "),
    ],
)
def test_an_unusable_first_key_is_refused_naming_where_not_what(
    home: Home, monkeypatch: pytest.MonkeyPatch, source: str, where: str
) -> None:
    short = secrets.token_hex(2)
    if source == "environment":
        monkeypatch.setenv(VARIABLE, short)
    elif source == "dotenv":
        home.write_dotenv(f"{VARIABLE}={short}\n")
    else:
        home.keyring.set_password("pyeconomics", PROVIDER, short)
    assert not has_key(PROVIDER)
    with pytest.raises(CredentialError, match="is shorter than 8 characters") as bad:
        resolve_key(PROVIDER)
    message = str(bad.value)
    assert where in message
    leaked = [name for name, text in {"message": message}.items() if short in text]
    assert leaked == []


def test_without_the_keyring_extra_the_step_is_skipped_at_debug(
    home: Home, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    home.keyring.set_password("pyeconomics", PROVIDER, secrets.token_hex(16))
    monkeypatch.setitem(sys.modules, "keyring", None)
    caplog.set_level(logging.DEBUG, logger="pyeconomics.data.credentials.chain")
    assert not has_key(PROVIDER)
    assert [record.getMessage() for record in caplog.records] == [
        "the keyring step is skipped: install pyeconomics[keyring] to use it"
    ]


class FailingKeyring:
    """A keyring backend whose lookups fail with a message holding a key."""

    def __init__(self, planted: str) -> None:
        self.planted = planted

    def get_password(self, service: str, username: str) -> str | None:
        message = f"backend failed reading {service}/{username}: {self.planted}"
        raise RuntimeError(message)


@pytest.mark.usefixtures("home")
def test_a_failing_keyring_backend_is_skipped_with_a_named_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring.core  # noqa: PLC0415 - the test group installs the extra

    planted = canary()
    monkeypatch.setattr(keyring.core, "_keyring_backend", FailingKeyring(planted.value))
    check = LeakCheck(planted)
    with check.warnings(), pytest.raises(CredentialError, match="no toy_chain key"):
        resolve_key(PROVIDER)
    assert list(check.sinks) == ["warning:DataWarning"]
    check.assert_clean()
    shown = check.sinks["warning:DataWarning"][1]
    assert ".FailingKeyring keyring backend failed (RuntimeError)" in shown
    assert "skipped for toy_chain [keyring_backend_failed]" in shown


@pytest.mark.usefixtures("home")
def test_a_keyring_without_a_backend_is_named_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring  # noqa: PLC0415 - the test group installs the extra

    def broken(*_args: object) -> object:
        raise RuntimeError("no backend")  # noqa: EM101, TRY003 - a test double

    monkeypatch.setattr(keyring, "get_password", broken)
    monkeypatch.setattr(keyring, "get_keyring", broken)
    with pytest.warns(DataWarning, match="the unknown keyring backend failed"):
        assert not has_key(PROVIDER)


@pytest.mark.usefixtures("home")
def test_a_keyring_answer_that_is_not_text_is_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring  # noqa: PLC0415 - the test group installs the extra

    monkeypatch.setattr(keyring, "get_password", lambda *_: 12345678)
    assert not has_key(PROVIDER)


@pytest.mark.usefixtures("home")
def test_debug_logging_names_only_the_kind_of_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planted = canary(PROVIDER)
    monkeypatch.setenv(VARIABLE, planted.value)
    check = LeakCheck(planted)
    with check.logs():
        resolve_key(PROVIDER)
        resolve_key(PROVIDER, planted.held)
    check.assert_clean()
    assert check.sinks == {
        "log:pyeconomics.data.credentials.chain": [
            f"pyeconomics.data.credentials.chain DEBUG {PROVIDER} key read from "
            f"the {source}"
            for source in ("environment", "argument")
        ]
    }


def test_resolving_installs_redaction_and_has_key_does_not(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys = plant(home, monkeypatch, ("environment",))
    registered = len(redaction._REGISTRY)  # noqa: SLF001 - the registry's size
    assert has_key(PROVIDER)
    assert (redaction.installed(), len(redaction._REGISTRY)) == (False, registered)  # noqa: SLF001
    held = resolve_key(PROVIDER)
    assert redaction.installed()
    masked = redaction.scrub_text(keys["environment"]) == redaction.MASK
    held.forget()
    assert masked


def test_the_key_sources_are_named_in_lookup_order() -> None:
    assert [source.value for source in KeySource] == [
        "argument",
        "environment",
        "dotenv",
        "keyring",
    ]


def test_a_dotenv_file_others_can_read_draws_a_warning_on_posix(home: Home) -> None:
    key = secrets.token_hex(16)
    path = home.write_dotenv(f"{VARIABLE}={key}\n", private=False)
    with pytest.warns(DataWarning, match="can be read by other users") as caught:
        found = resolve_key(PROVIDER, posix=True) == Secret(PROVIDER, key)
    assert found
    assert [warning.filename for warning in caught] == [__file__]
    message = caught[0].message
    assert isinstance(message, DataWarning)
    assert message.code == "credentials_file_permissions"
    assert str(path) not in str(message)


def test_permissions_are_not_checked_off_posix(home: Home) -> None:
    key = secrets.token_hex(16)
    home.write_dotenv(f"{VARIABLE}={key}\n", private=False)
    found = resolve_key(PROVIDER, posix=False) == Secret(PROVIDER, key)
    assert found


def test_the_permission_check_reads_group_and_other_bits() -> None:
    assert [
        chain._readable_by_others(mode)  # noqa: SLF001 - the bit test itself
        for mode in (0o600, 0o400, 0o640, 0o604, 0o644, 0o700)
    ] == [False, False, True, True, True, False]


@pytest.mark.skipif(os.name != "posix", reason="Windows has no owner-only mode bits")
def test_an_owner_only_dotenv_file_draws_no_warning_on_posix(home: Home) -> None:
    key = secrets.token_hex(16)
    home.write_dotenv(f"{VARIABLE}={key}\n", private=True)
    found = resolve_key(PROVIDER) == Secret(PROVIDER, key)
    assert found
