# tests/data/credentials/test_settings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Settings: three layers, overrides, and no secret in pyeconomics.toml.

Every test runs in its own configuration home (the ``home`` fixture): an
isolated configuration directory and an empty working directory.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from pyeconomics.data import ConfigError, Settings, configure, redaction, settings
from pyeconomics.data.config import (
    GUIDE_URL,
    MAX_CONFIG_BYTES,
    MAX_TTL_SECONDS,
    cache_dir,
    config_dir,
    reset,
)

if TYPE_CHECKING:
    from config_isolation import Home

ABSOLUTE = str(Path.cwd().anchor or "/")


@pytest.fixture(autouse=True)
def _no_cache_variable(isolated: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Compare settings against their defaults: drop the isolated cache variable."""
    assert isolated
    monkeypatch.delenv("PYECONOMICS_CACHE_DIR")


def contact() -> str:
    """A random SEC contact: personal data, so never a fixed literal."""
    return f"pyeconomics tester {secrets.token_hex(6)}@example.org"


@pytest.mark.usefixtures("home")
def test_defaults_when_nothing_is_configured() -> None:
    current = settings()
    assert current == Settings()
    assert (current.mode, current.offline, current.cache_dir) == (
        "library",
        False,
        None,
    )
    assert (current.sec_contact, current.ttl) == (None, {})


def test_layers_override_key_by_key(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_cache = Path(ABSOLUTE, "user-cache")
    home.write_config(
        f'mode = "hosted"\noffline = true\ncache_dir = {str(user_cache)!r}\n'
        "[ttl]\nbls = 60\nbea = 120\n"
    )
    home.write_config("offline = false\n[ttl]\nbea = 240\ncensus = 360\n", working=True)
    monkeypatch.setenv("PYECONOMICS_TTL_CENSUS", "480")
    monkeypatch.setenv("PYECONOMICS_TTL_HOU_XUE_ZHANG", "600")
    current = settings()
    assert current.mode == "hosted"
    assert current.offline is False
    assert current.cache_dir == user_cache
    assert current.ttl == {"bls": 60, "bea": 240, "census": 480, "hou_xue_zhang": 600}


def test_environment_settings(home: Home, monkeypatch: pytest.MonkeyPatch) -> None:
    home.write_config('mode = "hosted"\n')
    cache = Path(ABSOLUTE, "env-cache")
    monkeypatch.setenv("PYECONOMICS_MODE", " Library ")
    monkeypatch.setenv("PYECONOMICS_OFFLINE", "yes")
    monkeypatch.setenv("PYECONOMICS_CACHE_DIR", str(cache))
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", contact())
    monkeypatch.setenv("PYECONOMICS_LIVE_SOMETHING", "1")
    current = settings()
    assert (current.mode, current.offline, current.cache_dir) == (
        "library",
        True,
        cache,
    )
    assert current.sec_contact is not None
    assert cache_dir() == cache


@pytest.mark.parametrize(
    ("value", "flag"),
    [("1", True), ("TRUE", True), ("on", True), ("0", False), ("No", False)],
)
@pytest.mark.usefixtures("home")
def test_offline_flags(
    monkeypatch: pytest.MonkeyPatch, value: str, *, flag: bool
) -> None:
    monkeypatch.setenv("PYECONOMICS_OFFLINE", value)
    assert settings().offline is flag


@pytest.mark.usefixtures("home")
def test_empty_variables_are_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MODE", "OFFLINE", "CACHE_DIR", "SEC_CONTACT", "TTL_BLS"):
        monkeypatch.setenv(f"PYECONOMICS_{name}", " ")
    assert settings() == Settings()


@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("PYECONOMICS_OFFLINE", "maybe", "must be one of 1, true, yes, on, 0"),
        ("PYECONOMICS_TTL_BLS", "-5", "whole number of seconds"),
        ("PYECONOMICS_TTL_BLS", "1h", "whole number of seconds"),
        ("PYECONOMICS_TTL_BLS", str(MAX_TTL_SECONDS + 1), "less than or equal"),
        ("PYECONOMICS_TTL_9BLS", "60", "snake_case"),
        ("PYECONOMICS_MODE", "server", "'library' or 'hosted'"),
        ("PYECONOMICS_CACHE_DIR", "relative/cache", "must be an absolute path"),
        ("PYECONOMICS_SEC_CONTACT", "no-address-here", "must include an email"),
        ("PYECONOMICS_SEC_CONTACT", "a@b.c", "8 to 256 characters"),
        ("PYECONOMICS_SEC_CONTACT", "tab\there tester@example.org", "printable ASCII"),
    ],
)
@pytest.mark.usefixtures("home")
def test_invalid_environment_settings_name_the_problem_not_the_value(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, problem: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=problem) as invalid:
        settings()
    assert isinstance(invalid.value, ValueError)
    if len(value) > 2:  # a value long enough not to be found by accident
        leaked = [
            n for n, text in {"message": str(invalid.value)}.items() if value in text
        ]
        assert leaked == []


@pytest.mark.parametrize(
    "toml",
    [
        'fred_api_key = "{value}"\n',
        '[fred]\napi_key = "{value}"\n',
        '[providers.bls]\nregistration_token = "{value}"\n',
        '[[profiles]]\nname = "work"\npassword = "{value}"\n',
        'Authorization = "{value}"\n',
        '[ttl]\nsecret_provider = 5\nnote = "{value}"\n',
    ],
)
def test_a_credential_named_setting_is_refused_naming_the_key(
    home: Home, toml: str
) -> None:
    value = secrets.token_hex(16)
    home.write_config(toml.format(value=value))
    with pytest.raises(ConfigError, match="named like a credential") as refused:
        settings()
    message = str(refused.value)
    assert GUIDE_URL in message
    leaked = [name for name, text in {"message": message}.items() if value in text]
    assert leaked == []


def test_the_refused_names_are_listed_dotted(home: Home) -> None:
    home.write_config('[fred]\napi_key = "x"\n[[sets]]\ntoken = "y"\n', working=True)
    with pytest.raises(ConfigError) as refused:
        settings()
    assert str(refused.value).startswith(
        "pyeconomics.toml in the working directory sets 'fred.api_key', "
        "'sets.token', named like a credential."
    )


@pytest.mark.usefixtures("home")
def test_a_credential_named_variable_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = secrets.token_hex(16)
    monkeypatch.setenv("PYECONOMICS_FRED_API_KEY", value)
    with pytest.raises(
        ConfigError, match="PYECONOMICS_FRED_API_KEY is named like"
    ) as bad:
        settings()
    leaked = [
        name for name, text in {"message": str(bad.value)}.items() if value in text
    ]
    assert leaked == []


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b'mode = "library\n', r"is not valid TOML \(line 1\)"),
        (b"\xff\xfe = 1\n", "is not UTF-8 text"),
        (b"a" * (MAX_CONFIG_BYTES + 1), "is larger than"),
        (b'colour = "blue"\n', r"colour: Extra inputs are not permitted"),
        (b"offline = 1\n", "offline: Input should be a valid boolean"),
        (b'cache_dir = "relative"\n', "cache_dir: Value error, must be an absolute"),
        (b'cache_dir = "/x\\u0000y"\n', "must not contain a NUL"),
        (b"[ttl]\nbls = true\n", "ttl.bls: Input should be a valid integer"),
        (b"ttl = 5\n", "ttl: Input should be a valid dictionary"),
        (b"cache_dir = 5\n", "cache_dir: "),
        (b"sec_contact = 5\n", "sec_contact: "),
        (b'tags = ["a", 1]\n', "tags: Extra inputs are not permitted"),
    ],
    ids=[
        "toml",
        "utf8",
        "size",
        "unknown",
        "offline",
        "relative",
        "nul",
        "ttl-value",
        "ttl-table",
        "cache-dir-type",
        "contact-type",
        "list",
    ],
)
def test_invalid_files_name_the_layer_and_setting(
    home: Home, content: bytes, problem: str
) -> None:
    home.write_config(content)
    with pytest.raises(ConfigError, match=problem) as invalid:
        settings()
    message = str(invalid.value)
    assert message.startswith("pyeconomics.toml in the user configuration directory")
    assert str(home.config_dir) not in message


def test_toml_errors_without_a_line_number(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tomllib  # noqa: PLC0415 - patched for this test only

    def fail(_text: str) -> object:
        raise tomllib.TOMLDecodeError("no position")  # noqa: EM101, TRY003 - a test double

    home.write_config(b"mode = 'library'\n")
    monkeypatch.setattr(tomllib, "loads", fail)
    with pytest.raises(ConfigError, match=r"is not valid TOML$"):
        settings()


def test_an_unreadable_file_names_the_error_class_only(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.write_config(b"offline = true\n")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(13, "denied", str(home.config_dir))

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", refuse)
        with pytest.raises(
            ConfigError, match=r"cannot be read \(PermissionError\)"
        ) as bad:
            settings()
    assert bad.value.__context__ is None
    assert str(home.config_dir) not in str(bad.value)


def test_the_working_directory_is_read_once_when_it_is_the_config_dir(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.write_config("[ttl]\nbls = 60\n")
    monkeypatch.chdir(home.config_dir)
    assert settings().ttl == {"bls": 60}


@pytest.mark.usefixtures("home")
def test_a_removed_working_directory_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def gone() -> Path:
        raise FileNotFoundError(2, "gone")

    monkeypatch.setattr(Path, "cwd", staticmethod(gone))
    assert settings() == Settings()


def test_configure_overrides_until_reset(home: Home) -> None:
    home.write_config('mode = "hosted"\n')
    assert configure() == Settings(mode="hosted")
    assert configure(offline=True) == Settings(mode="hosted", offline=True)
    assert configure(mode="library").mode == "library"
    assert settings().offline is True
    reset()
    assert settings() == Settings(mode="hosted")


@pytest.mark.usefixtures("home")
def test_configure_refuses_invalid_values() -> None:
    with pytest.raises(ConfigError, match="configure\\(\\) has invalid settings: mode"):
        configure(mode="server")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    with pytest.raises(ConfigError, match="offline: Input should be a valid boolean"):
        configure(offline="yes")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    assert settings() == Settings()


def test_settings_are_read_once_per_process_until_reset(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert settings().offline is False
    monkeypatch.setenv("PYECONOMICS_OFFLINE", "1")
    home.write_config('mode = "hosted"\n')
    assert settings() == Settings()
    reset()
    assert settings() == Settings(mode="hosted", offline=True)


@pytest.mark.usefixtures("home")
def test_the_sec_contact_is_masked_and_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    address = contact()
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", f"  {address}  ")
    current = settings()
    held = current.sec_contact
    assert held is not None
    shown = {
        "repr": [repr(current), repr(held)],
        "str": [str(current), str(held)],
        "json": [current.model_dump_json()],
        "scrubbed": [redaction.scrub_text(f"User-Agent: pyeconomics {address}")],
    }
    leaked = [name for name, texts in shown.items() if any(address in t for t in texts)]
    assert leaked == []
    same = held.get_secret_value() == address
    assert same
    reset()
    unregistered = redaction.scrub_text(address) == address
    assert unregistered


def test_settings_are_frozen_and_refuse_unknown_fields() -> None:
    current = Settings()
    with pytest.raises(ValidationError):
        current.mode = "hosted"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
    with pytest.raises(ValidationError):
        Settings(colour="blue")  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    held = Settings.model_validate({"sec_contact": contact()}).sec_contact
    assert Settings(sec_contact=held).sec_contact == held


def test_config_dir_comes_from_the_variable_or_platformdirs(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert config_dir() == home.config_dir
    monkeypatch.setenv("PYECONOMICS_CONFIG_DIR", "relative")
    with pytest.raises(ConfigError, match="PYECONOMICS_CONFIG_DIR must be an absolute"):
        config_dir()
    monkeypatch.delenv("PYECONOMICS_CONFIG_DIR")
    default = config_dir()
    assert default.is_absolute()
    assert default.name == "pyeconomics"


@pytest.mark.usefixtures("home")
def test_cache_dir_defaults_to_the_users_cache() -> None:
    default = cache_dir()
    assert default.is_absolute()
    assert "pyeconomics" in default.parts
    assert not os.path.exists(default / "pyeconomics.sqlite3")  # noqa: PTH110 - nothing created
