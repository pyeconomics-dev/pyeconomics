# src/pyeconomics/data/config.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Settings: the layered ``pyeconomics.toml`` and ``PYECONOMICS_*`` variables.

ADR-0011 decision 12. Settings come from three layers, each overriding the
one before it, key by key:

1. ``pyeconomics.toml`` in the user's configuration directory
   (:func:`config_dir`: ``PYECONOMICS_CONFIG_DIR`` if set, else
   ``platformdirs.user_config_dir("pyeconomics")``);
2. ``pyeconomics.toml`` in the working directory;
3. the environment: ``PYECONOMICS_MODE``, ``PYECONOMICS_OFFLINE``,
   ``PYECONOMICS_CACHE_DIR``, ``PYECONOMICS_SEC_CONTACT`` and
   ``PYECONOMICS_TTL_<PROVIDER>``.

:func:`configure` then sets process-wide overrides on top, and
:func:`settings` returns the result as a frozen :class:`Settings`.

The files hold settings only. Any key named like a credential (``key``,
``token``, ``secret``, ``password``, ``credential``, ``auth``) raises
:class:`~pyeconomics.data.errors.ConfigError` naming the key, never its
value; keys belong to the key chain
(:mod:`pyeconomics.data.credentials`). No message names a path or repeats a
value: an error says which layer and which setting.

The SEC contact (``sec_contact``) is personal data. EDGAR's User-Agent
carries it (Phase 3 Step 7), and nothing else: it is held as a pydantic
``SecretStr``, which prints as asterisks, and registered with
:mod:`~pyeconomics.data.redaction`, so no log record, message or export
carries it either.

The files and the environment are read once per process, at the first call
to :func:`settings`; :func:`reset` forgets them and every override.

Examples
--------
>>> Settings(offline=True, ttl={"bls": 3600})
Settings(mode='library', offline=True, enable_yfinance=False, cache_dir=None, ttl={'bls': 3600})

"""  # noqa: E501 - doctest representation cannot wrap

from __future__ import annotations

import os
import re
import threading
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
)

from pyeconomics.core._fields import identifier
from pyeconomics.core.errors import InputError
from pyeconomics.data import redaction
from pyeconomics.data.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = [
    "APP_NAME",
    "CONFIG_FILE",
    "DOTENV_FILE",
    "ENV_PREFIX",
    "GUIDE_URL",
    "MAX_TTL_SECONDS",
    "Settings",
    "cache_dir",
    "config_dir",
    "configure",
    "reset",
    "settings",
]

#: The application name the configuration and cache directories are named after.
APP_NAME: Final = "pyeconomics"
#: The settings file, read from the configuration and working directories.
CONFIG_FILE: Final = "pyeconomics.toml"
#: The key file, read from the configuration directory only.
DOTENV_FILE: Final = ".env"
#: The prefix of every environment variable that holds a setting.
ENV_PREFIX: Final = "PYECONOMICS_"
#: The "Keys and configuration" guide.
GUIDE_URL: Final = "https://pyeconomics.readthedocs.io/en/main/data/keys.html"
#: The longest time-to-live a setting may give, in seconds: ten years.
MAX_TTL_SECONDS: Final = 3_650 * 86_400
#: The largest settings file read, in bytes.
MAX_CONFIG_BYTES: Final = 64 * 1024

# A name that says it holds a credential.
_CREDENTIAL_NAME: Final = re.compile(
    r"(?i)key|token|secret|passw|credential|auth|cookie"
)
_EMAIL: Final = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_TOML_LINE: Final = re.compile(r"at line (\d+)")
_FLAGS: Final = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}
_MIN_CONTACT: Final = redaction.MIN_SECRET_LENGTH
_MAX_CONTACT: Final = 256


class Settings(BaseModel):
    """The data layer's settings, after every layer and override.

    Attributes
    ----------
    mode
        ``"library"`` (the default) or ``"hosted"``, which serves only
        sources classed hosted-safe or user-supplied (Phase 3 Step 4).
    offline
        Serve only cached data and never send a request (Phase 3 Step 5).
    cache_dir
        Where the cache lives, as an absolute path; ``None`` for the user's
        cache directory (:func:`cache_dir`).
    sec_contact
        The name and email address SEC EDGAR requires in its User-Agent, or
        ``None``. Personal data: masked when printed, never logged.
    ttl
        A time-to-live in seconds per provider id, overriding the provider's
        own for what the cache keeps.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    mode: Literal["library", "hosted"] = "library"
    offline: StrictBool = False
    enable_yfinance: StrictBool = False
    """Explicit personal-use opt-in; installing the extra does not enable it."""
    cache_dir: Path | None = None
    sec_contact: SecretStr | None = Field(default=None, repr=False)
    ttl: dict[str, Annotated[StrictInt, Field(ge=0, le=MAX_TTL_SECONDS)]] = Field(
        default_factory=dict
    )

    @field_validator("cache_dir", mode="before")
    @classmethod
    def _absolute(cls, value: object) -> object:
        if isinstance(value, str | Path):
            if "\x00" in str(value):
                msg = "must not contain a NUL character"
                raise ValueError(msg)
            if not Path(value).is_absolute():
                msg = "must be an absolute path"
                raise ValueError(msg)
        return value

    @field_validator("sec_contact", mode="before")
    @classmethod
    def _contact(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not _MIN_CONTACT <= len(text) <= _MAX_CONTACT:
            msg = f"must be {_MIN_CONTACT} to {_MAX_CONTACT} characters long"
            raise ValueError(msg)
        if not all(" " <= character <= "~" for character in text):
            msg = "must be printable ASCII on one line"
            raise ValueError(msg)
        if not _EMAIL.search(text):
            msg = "must include an email address"
            raise ValueError(msg)
        return text

    @field_validator("ttl")
    @classmethod
    def _provider_ids(cls, value: dict[str, int]) -> dict[str, int]:
        for name in value:
            try:
                identifier(name, "each provider id in ttl")
            except InputError as error:
                raise ValueError(str(error)) from None
        return value


def config_dir() -> Path:
    r"""Return the directory that holds ``pyeconomics.toml`` and ``.env``.

    ``PYECONOMICS_CONFIG_DIR``, when set, must be an absolute path; otherwise
    the user's configuration directory: ``~/.config/pyeconomics`` on Linux,
    ``~/Library/Application Support/pyeconomics`` on macOS and
    ``%LOCALAPPDATA%\pyeconomics`` on Windows.

    Raises
    ------
    ConfigError
        If ``PYECONOMICS_CONFIG_DIR`` is not an absolute path.
    """
    override = os.environ.get(f"{ENV_PREFIX}CONFIG_DIR", "").strip()
    if override:
        path = Path(override)
        if not path.is_absolute():
            msg = f"{ENV_PREFIX}CONFIG_DIR must be an absolute path"
            raise ConfigError(msg)
        return path
    import platformdirs  # noqa: PLC0415 - imported when first needed

    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False))


def cache_dir() -> Path:
    r"""Return the cache directory: the ``cache_dir`` setting, or the user's.

    The user's cache directory is ``~/.cache/pyeconomics`` on Linux,
    ``~/Library/Caches/pyeconomics`` on macOS and
    ``%LOCALAPPDATA%\pyeconomics\Cache`` on Windows. Nothing here creates
    it.
    """
    configured = settings().cache_dir
    if configured is not None:
        return configured
    import platformdirs  # noqa: PLC0415 - imported when first needed

    return Path(platformdirs.user_cache_dir(APP_NAME, appauthor=False))


def _credential_names(data: Mapping[str, object], prefix: str = "") -> list[str]:
    """Return every key, nested ones dotted, whose name says credential."""
    found: list[str] = []
    for name, value in data.items():
        dotted = f"{prefix}{name}"
        if _CREDENTIAL_NAME.search(name):
            found.append(dotted)
        if isinstance(value, dict):
            found += _credential_names(value, f"{dotted}.")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    found += _credential_names(item, f"{dotted}.")
    return found


def _refuse_credentials(data: Mapping[str, object], origin: str) -> None:
    names = _credential_names(data)
    if names:
        listed = ", ".join(repr(name) for name in names)
        msg = (
            f"{origin} sets {listed}, named like a credential. pyeconomics.toml "
            "holds settings only: give a key through its environment variable, "
            f"the .env file or the OS keyring ({GUIDE_URL})"
        )
        raise ConfigError(msg)


def _read_bytes(path: Path, origin: str) -> bytes | None:
    """Read a file of at most :data:`MAX_CONFIG_BYTES`, or ``None`` if absent."""
    failure = ""
    data: bytes | None = None
    try:
        if path.is_file():
            with path.open("rb") as handle:
                data = handle.read(MAX_CONFIG_BYTES + 1)
    except OSError as error:
        failure = type(error).__name__
    if failure:
        msg = f"{origin} cannot be read ({failure})"
        raise ConfigError(msg)
    if data is not None and len(data) > MAX_CONFIG_BYTES:
        msg = f"{origin} is larger than {MAX_CONFIG_BYTES} bytes"
        raise ConfigError(msg)
    return data


def _read_toml(path: Path, origin: str) -> dict[str, object]:
    data = _read_bytes(path, origin)
    if data is None:
        return {}
    problem = ""
    parsed: dict[str, object] = {}
    try:
        parsed = tomllib.loads(data.decode("utf-8"))
    except UnicodeDecodeError:
        problem = "is not UTF-8 text"
    except tomllib.TOMLDecodeError as error:
        line = _TOML_LINE.search(str(error))
        problem = "is not valid TOML" + (f" (line {line.group(1)})" if line else "")
    if problem:
        msg = f"{origin} {problem}"
        raise ConfigError(msg)
    _refuse_credentials(parsed, origin)
    return parsed


def _flag(name: str, value: str) -> bool:
    flag = _FLAGS.get(value.lower())
    if flag is None:
        msg = f"{name} must be one of {', '.join(_FLAGS)}"
        raise ConfigError(msg)
    return flag


def _seconds(name: str, value: str) -> int:
    if not value.isdecimal():
        msg = f"{name} must be a whole number of seconds"
        raise ConfigError(msg)
    return int(value)


# Each PYECONOMICS_* setting and how its text becomes a value. CONFIG_DIR
# locates the files instead; other PYECONOMICS_* variables belong to the test
# suite and tools, not to these settings.
_ENVIRONMENT: Final[dict[str, tuple[str, Callable[[str, str], object]]]] = {
    "MODE": ("mode", lambda _name, value: value.lower()),
    "OFFLINE": ("offline", _flag),
    "CACHE_DIR": ("cache_dir", lambda _name, value: value),
    "SEC_CONTACT": ("sec_contact", lambda _name, value: value),
}


def _environment_layer() -> dict[str, object]:
    """Read the ``PYECONOMICS_*`` settings; empty variables are unset."""
    layer: dict[str, object] = {}
    ttl: dict[str, int] = {}
    for name, raw in sorted(os.environ.items()):
        if not name.startswith(ENV_PREFIX):
            continue
        setting = name.removeprefix(ENV_PREFIX)
        if _CREDENTIAL_NAME.search(setting):
            msg = (
                f"the environment variable {name} is named like a credential; "
                "pyeconomics reads a provider's key from its own variable, such "
                f"as FRED_API_KEY ({GUIDE_URL})"
            )
            raise ConfigError(msg)
        value = raw.strip()
        if not value:
            continue
        if setting in _ENVIRONMENT:
            field, convert = _ENVIRONMENT[setting]
            layer[field] = convert(name, value)
        elif setting.startswith("TTL_"):
            ttl[setting.removeprefix("TTL_").lower()] = _seconds(name, value)
    if ttl:
        layer["ttl"] = ttl
    return layer


def _validate(data: Mapping[str, object], origin: str) -> Settings:
    problems = ""
    try:
        return Settings.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, detail['loc']))}: {detail['msg']}"
            for detail in error.errors(include_url=False, include_input=False)
        )
    msg = f"{origin} has invalid settings: {problems}"
    raise ConfigError(msg)


def _working_file() -> Path | None:
    try:
        return Path.cwd() / CONFIG_FILE
    except OSError:  # the working directory was removed
        return None


def _load() -> Settings:
    user_file = config_dir() / CONFIG_FILE
    origin = f"{CONFIG_FILE} in the user configuration directory"
    layers = [(origin, _read_toml(user_file, origin))]
    work_file = _working_file()
    if work_file is not None and work_file != user_file:
        origin = f"{CONFIG_FILE} in the working directory"
        layers.append((origin, _read_toml(work_file, origin)))
    layers.append((f"the {ENV_PREFIX}* environment variables", _environment_layer()))
    merged: dict[str, object] = {}
    for origin, layer in layers:
        _validate(layer, origin)
        for name, value in layer.items():
            previous = merged.get(name)
            if isinstance(previous, dict) and isinstance(value, dict):
                merged[name] = {**previous, **value}
            else:
                merged[name] = value
    return _validate(merged, "the merged configuration")


_LOCK: Final = threading.Lock()
_STATE: dict[str, object] = {}
_OVERRIDES: dict[str, object] = {}


def _register_contact(loaded: Settings) -> None:
    contact = loaded.sec_contact
    if contact is not None:
        value = contact.get_secret_value()
        redaction.register(value)
        _STATE["contact"] = value


def settings() -> Settings:
    """Return the current settings: the layers, then :func:`configure`'s overrides.

    The files and the environment are read at the first call in a process.

    Raises
    ------
    ConfigError
        If a file cannot be read or parsed, holds a key named like a
        credential, or a setting is invalid.
    """
    with _LOCK:
        loaded = _STATE.get("settings")
        if not isinstance(loaded, Settings):
            loaded = _load()
            _register_contact(loaded)
            _STATE["settings"] = loaded
        overrides = dict(_OVERRIDES)
    return loaded.model_copy(update=overrides) if overrides else loaded


def configure(
    *,
    mode: Literal["library", "hosted"] | None = None,
    offline: bool | None = None,
    enable_yfinance: bool | None = None,
) -> Settings:
    """Override settings for the rest of the process, and return the result.

    The overrides are process-wide by design: every thread and task sees them
    from the next read on. A surface that serves many requests (the REST API,
    the MCP server) configures once, at start (hosted mode, offline), and
    never per request, since one request's override would reach every other
    request in flight.

    Parameters
    ----------
    mode
        ``"library"`` or ``"hosted"``; ``None`` leaves it as it is.
    offline
        Whether to serve only cached data; ``None`` leaves it as it is.

    Raises
    ------
    ConfigError
        If a value is invalid, or the files and environment are.
    """
    update = {
        name: value
        for name, value in (
            ("mode", mode),
            ("offline", offline),
            ("enable_yfinance", enable_yfinance),
        )
        if value is not None
    }
    _validate(update, "configure()")
    with _LOCK:
        _OVERRIDES.update(update)
    return settings()


def reset() -> None:
    """Forget the loaded settings and every override; the next read reloads.

    The test suite calls this around every test.
    """
    with _LOCK:
        contact = _STATE.pop("contact", None)
        if isinstance(contact, str):
            redaction.unregister(contact)
        _STATE.clear()
        _OVERRIDES.clear()
