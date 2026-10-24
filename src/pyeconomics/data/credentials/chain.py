# src/pyeconomics/data/credentials/chain.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The key chain: where a provider's key is looked up, in order.

ADR-0011 decision 12. :func:`resolve_key` takes the first key it finds:

1. an explicit argument;
2. the provider's environment variable, ``<PROVIDER>_API_KEY``
   (:func:`key_variable`: ``FRED_API_KEY``, ``BLS_API_KEY``, ...);
3. that variable in the ``.env`` file in the user's configuration directory
   (:func:`~pyeconomics.data.config.config_dir`), parsed strictly
   (:mod:`~pyeconomics.data.credentials.dotenv`). A variable set in the real
   environment always wins over the file, and the file is never loaded into
   the environment;
4. the OS keyring, service ``pyeconomics`` and user the provider id, when
   the ``keyring`` extra is installed.

An empty value counts as unset. The key comes back as a
:class:`~pyeconomics.data.credentials.Secret`, and the first resolution in a
process installs the redacting log-record factory
(:func:`pyeconomics.data.redaction.install`). The chain logs, at DEBUG, only
which kind of source answered. :func:`has_key` answers the same question
without creating a secret, so a presence check prints only ``True`` or
``False``, and :func:`key_source` names the kind of source that would answer.
Inside :func:`withheld`, the chain finds no key for the named providers, so a
source whose key is optional runs keyless.

:func:`store_key` and :func:`delete_key` write the keyring step, the one
source pyeconomics writes: ``pyeconomics keys set`` and ``keys delete`` call
them (Phase 4 Step 4), and nothing else does.

Examples
--------
>>> key_variable("fred")
'FRED_API_KEY'
>>> sorted(source.value for source in KeySource)
['argument', 'dotenv', 'environment', 'keyring']

"""

from __future__ import annotations

import contextlib
import logging
import os
import stat
import warnings
from contextvars import ContextVar
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pyeconomics.core._fields import identifier
from pyeconomics.core._optional import import_optional
from pyeconomics.core.errors import InputError, MissingOptionalDependencyError
from pyeconomics.data import redaction
from pyeconomics.data.config import DOTENV_FILE, GUIDE_URL, config_dir
from pyeconomics.data.credentials.dotenv import (
    DOTENV_LOCATION,
    MAX_DOTENV_CHARACTERS,
    parse_dotenv,
)
from pyeconomics.data.credentials.secret import Secret, key_problem
from pyeconomics.data.errors import ConfigError, CredentialError, DataWarning

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import ModuleType

__all__ = [
    "KEYRING_SERVICE",
    "KeySource",
    "delete_key",
    "has_key",
    "key_source",
    "key_variable",
    "resolve_key",
    "store_key",
    "withheld",
]

#: The keyring service every key is stored under; the user is the provider id.
KEYRING_SERVICE: Final = "pyeconomics"

_logger = logging.getLogger(__name__)
# Warnings point at the first frame outside the package: the caller's code.
_PACKAGE_DIR: Final = str(Path(__file__).parents[2])
# The providers whose keys the chain does not find in this context.
_WITHHELD: ContextVar[frozenset[str]] = ContextVar("withheld", default=frozenset())


class KeySource(StrEnum):
    """The kinds of source the chain reads a key from, in lookup order."""

    ARGUMENT = "argument"
    ENVIRONMENT = "environment"
    DOTENV = "dotenv"
    KEYRING = "keyring"


_DESCRIBED: Final = {
    KeySource.ARGUMENT: "the argument",
    KeySource.ENVIRONMENT: "the environment variable {variable}",
    KeySource.DOTENV: f"{{variable}} in {DOTENV_LOCATION}",
    KeySource.KEYRING: f"the OS keyring (service {KEYRING_SERVICE!r})",
}


def key_variable(provider_id: str) -> str:
    """Return the environment variable that holds a provider's key.

    Raises
    ------
    InputError
        If the provider id is not snake_case.
    """
    return f"{identifier(provider_id, 'provider_id').upper()}_API_KEY"


def _warn(code: str, message: str) -> None:
    warnings.warn(
        DataWarning(code, message), stacklevel=2, skip_file_prefixes=(_PACKAGE_DIR,)
    )


def _readable_by_others(mode: int) -> bool:
    """Return whether a file mode lets the group or other users read it."""
    return bool(mode & (stat.S_IRGRP | stat.S_IROTH))


def _read_dotenv(path: Path, *, posix: bool) -> str | None:
    """Return the ``.env`` file's text, or ``None`` when there is none."""
    failure = ""
    data: bytes | None = None
    mode = 0
    try:
        if path.is_file():
            with path.open("rb") as handle:
                data = handle.read(4 * MAX_DOTENV_CHARACTERS + 1)
            mode = path.stat().st_mode
    except OSError as error:
        failure = type(error).__name__
    if failure:
        msg = f"{DOTENV_LOCATION} cannot be read ({failure})"
        raise ConfigError(msg)
    if data is None:
        return None
    if posix and _readable_by_others(mode):
        _warn(
            "credentials_file_permissions",
            f"{DOTENV_LOCATION} can be read by other users; make it readable "
            "by its owner only (chmod 600)",
        )
    text: str | None = None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is None:
        msg = f"{DOTENV_LOCATION} is not UTF-8 text"
        raise ConfigError(msg)
    return text


def _from_dotenv(variable: str, *, posix: bool) -> str:
    text = _read_dotenv(config_dir() / DOTENV_FILE, posix=posix)
    if text is None:
        return ""
    return parse_dotenv(text).get(variable, "").strip()


def _backend_name(keyring: ModuleType) -> str:
    try:
        backend = keyring.get_keyring()
    except Exception:  # noqa: BLE001 - a broken backend still gets a name
        return "unknown"
    kind = type(backend)
    return f"{kind.__module__}.{kind.__qualname__}"


def _from_keyring(provider: str) -> str:
    try:
        keyring = import_optional("keyring", extra="keyring")
    except MissingOptionalDependencyError:
        _logger.debug(
            "the keyring step is skipped: install pyeconomics[keyring] to use it"
        )
        return ""
    failure = ""
    found: object = None
    try:
        found = keyring.get_password(KEYRING_SERVICE, provider)
    except Exception as error:  # noqa: BLE001 - any backend failure skips the step
        failure = type(error).__name__
    if failure:
        _warn(
            "keyring_backend_failed",
            f"the {_backend_name(keyring)} keyring backend failed ({failure}); "
            f"the keyring step was skipped for {provider}",
        )
        return ""
    return found.strip() if isinstance(found, str) else ""


@contextlib.contextmanager
def withheld(provider_id: str) -> Generator[None]:
    """Find no key for a provider inside the block, wherever one is stored.

    A source whose key is optional (BLS) then runs keyless, as it does for a
    user without a key; the recorder and the live suite use it for a keyless
    case. An explicit argument still counts.

    Examples
    --------
    >>> with withheld("bls"):
    ...     has_key("bls")
    False

    """
    provider = identifier(provider_id, "provider_id")
    token = _WITHHELD.set(_WITHHELD.get() | {provider})
    try:
        yield
    finally:
        _WITHHELD.reset(token)


def _first(provider: str, *, posix: bool | None) -> tuple[KeySource, str] | None:
    """Return the first non-empty value in the chain after the argument."""
    if provider in _WITHHELD.get():
        return None
    posix = os.name == "posix" if posix is None else posix
    variable = key_variable(provider)
    value = os.environ.get(variable, "").strip()
    if value:
        return KeySource.ENVIRONMENT, value
    value = _from_dotenv(variable, posix=posix)
    if value:
        return KeySource.DOTENV, value
    value = _from_keyring(provider)
    if value:
        return KeySource.KEYRING, value
    return None


def _missing(provider: str) -> str:
    variable = key_variable(provider)
    return (
        f"no {provider} key was found. Set the {variable} environment variable, "
        f"add {variable} to {DOTENV_LOCATION}, store it in the OS keyring with "
        f"`pyeconomics keys set {provider}` (pyeconomics[keyring]), or "
        f"pass it as an argument; see {GUIDE_URL}"
    )


def resolve_key(
    provider_id: str,
    explicit: str | Secret | None = None,
    *,
    posix: bool | None = None,
) -> Secret:
    """Return a provider's key from the first source in the chain that has one.

    Parameters
    ----------
    provider_id
        The provider whose key to find, such as ``"fred"``.
    explicit
        A key passed by the caller, as text or a :class:`Secret`; it wins
        over every other source.
    posix
        Whether to check the ``.env`` file's permissions, as on Linux and
        macOS; ``None``, the default, follows the operating system.

    Returns
    -------
    Secret
        The key.

    Raises
    ------
    CredentialError
        If no source has a key, or the first key found is not usable. The
        message names the provider, its environment variable, the keyring
        command and the guide, never a value.
    ConfigError
        If the ``.env`` file cannot be read or breaks its format.
    """
    provider = identifier(provider_id, "provider_id")
    redaction.install()
    if isinstance(explicit, Secret):
        if explicit.provider != provider:
            msg = (
                f"the key given as an argument is for {explicit.provider}, "
                f"not {provider}"
            )
            raise CredentialError(msg, provider=provider)
        _logger.debug("%s key read from the argument", provider)
        return explicit
    found = (
        (KeySource.ARGUMENT, explicit.strip())
        if isinstance(explicit, str)
        else _first(provider, posix=posix)
    )
    if found is None:
        raise CredentialError(_missing(provider), provider=provider)
    source, value = found
    problem = key_problem(value)
    if problem is not None:
        where = _DESCRIBED[source].format(variable=key_variable(provider))
        msg = f"the {provider} key from {where} {problem}"
        raise CredentialError(msg, provider=provider)
    _logger.debug("%s key read from the %s", provider, source.value)
    return Secret(provider, value)


def has_key(provider_id: str, *, posix: bool | None = None) -> bool:
    """Return whether the chain holds a usable key for a provider.

    It reads the same sources as :func:`resolve_key`, after the argument,
    without creating a :class:`Secret`; it returns ``False`` when the first
    key found is not usable.

    Raises
    ------
    ConfigError
        If the ``.env`` file cannot be read or breaks its format.
    """
    found = _first(identifier(provider_id, "provider_id"), posix=posix)
    return found is not None and key_problem(found[1]) is None


def key_source(provider_id: str, *, posix: bool | None = None) -> KeySource | None:
    """Return the kind of source the chain would read a provider's key from.

    It reads the same sources as :func:`resolve_key`, after the argument, and
    returns only the kind of the first that holds a value: never the value. A
    value there that is not a usable key still names its source, and
    :func:`resolve_key` then says what is wrong with it. ``None`` means no
    source holds one.

    Raises
    ------
    ConfigError
        If the ``.env`` file cannot be read or breaks its format.

    Examples
    --------
    >>> key_source("fred") is None
    True

    """
    found = _first(identifier(provider_id, "provider_id"), posix=posix)
    return None if found is None else found[0]


def _keyring_failure(
    keyring: ModuleType, action: str, provider: str, failure: str
) -> CredentialError:
    msg = (
        f"the {_backend_name(keyring)} keyring backend could not {action} the "
        f"{provider} key ({failure})"
    )
    return CredentialError(msg, provider=provider)


def store_key(provider_id: str, secret: Secret) -> None:
    """Store a provider's key in the OS keyring, the chain's last step.

    The key goes under service ``pyeconomics`` and the provider id as the user,
    where :func:`resolve_key` looks for it when no environment variable or
    ``.env`` entry holds one. Only the type of a backend's failure is reported,
    never its message.

    Parameters
    ----------
    provider_id
        The provider the key belongs to, such as ``"fred"``.
    secret
        The key, already checked by :class:`Secret`.

    Raises
    ------
    MissingOptionalDependencyError
        Without the keyring extra: ``pip install 'pyeconomics[keyring]'``.
    CredentialError
        If the secret is another provider's, or the keyring backend fails.
    InputError
        If the provider id is not snake_case, or ``secret`` is not a Secret.
    """
    provider = identifier(provider_id, "provider_id")
    held: object = secret  # a caller may pass something that is no Secret
    if not isinstance(held, Secret):
        msg = f"a key is stored as a Secret, not {type(held).__name__}"
        raise InputError(msg)
    if secret.provider != provider:
        msg = f"the key is for {secret.provider}, not {provider}"
        raise CredentialError(msg, provider=provider)
    keyring = import_optional("keyring", extra="keyring")
    failure = ""
    try:
        keyring.set_password(KEYRING_SERVICE, provider, secret.reveal())
    except Exception as error:  # noqa: BLE001 - any backend failure is reported by type
        failure = type(error).__name__
    if failure:
        raise _keyring_failure(keyring, "store", provider, failure)
    _logger.debug("%s key stored in the keyring", provider)


def delete_key(provider_id: str) -> bool:
    """Delete a provider's key from the OS keyring; return whether one was there.

    Only the keyring step changes: a key in the environment or the ``.env``
    file stays where it is, and :func:`key_source` still finds it.

    Raises
    ------
    MissingOptionalDependencyError
        Without the keyring extra: ``pip install 'pyeconomics[keyring]'``.
    CredentialError
        If the keyring backend fails.
    InputError
        If the provider id is not snake_case.
    """
    provider = identifier(provider_id, "provider_id")
    keyring = import_optional("keyring", extra="keyring")
    failure = ""
    removed = False
    try:
        if keyring.get_password(KEYRING_SERVICE, provider) is not None:
            keyring.delete_password(KEYRING_SERVICE, provider)
            removed = True
    except Exception as error:  # noqa: BLE001 - any backend failure is reported by type
        failure = type(error).__name__
    if failure:
        raise _keyring_failure(keyring, "delete", provider, failure)
    _logger.debug("%s key deleted from the keyring: %s", provider, removed)
    return removed
