# src/pyeconomics/cli/key_commands.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics keys``: store, list and delete providers' keys (the Credential rule).

A key is never an argument, an option value or an echo. ``keys set`` reads it
from a hidden prompt, or with ``--stdin`` from the first line of standard input,
wraps it in a :class:`~pyeconomics.data.credentials.Secret` at once and stores it
in the OS keyring through :func:`~pyeconomics.data.credentials.store_key`, the
only code that reveals it. ``keys list`` names the kind of source each key would
be read from (environment, dotenv, keyring or none), never a value, and ``keys
delete`` removes the keyring's copy. These commands call nothing else that
touches a key: :func:`~pyeconomics.data.credentials.store_key`,
:func:`~pyeconomics.data.credentials.delete_key` and
:func:`~pyeconomics.data.credentials.key_source`.

Storing and deleting need the keyring extra (``pyeconomics[keyring]``); without
it the command exits with code 8 and says so.
"""

from pathlib import Path
from typing import Annotated, Any, Final

from cyclopts import Parameter

from pyeconomics.cli.context import Context, ContextParameter, UsageError
from pyeconomics.cli.output import Format, Grid, emit_json, show
from pyeconomics.core.errors import InputError

__all__ = ["delete_key", "list_keys", "set_key"]

#: The most bytes read from standard input for one key: room for the longest
#: key the checks accept, so a longer one is refused as too long.
_MAX_READ: Final = 4 * 1024 + 2


def _keyed(provider: str) -> Any:  # noqa: ANN401 - a provider's info
    """Return the info of a registered provider that uses a key."""
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415
    from pyeconomics.data.providers.base import AuthKind  # noqa: PLC0415

    info = provider_registry.installed().provider_class(provider).info
    if info.auth.kind is not AuthKind.KEY:
        msg = f"{provider} takes no key"
        raise InputError(msg)
    return info


def _read_value(context: Context, provider: str, *, from_stdin: bool) -> str:
    """Read the key's text from standard input or a hidden prompt."""
    streams = context.streams
    if not from_stdin:
        if not streams.interactive:
            msg = (
                "standard input is not a terminal, so there is no hidden prompt; "
                "pass --stdin to read the key from standard input"
            )
            raise UsageError(msg)
        return streams.ask_secret(f"{provider} key (input hidden): ")
    data = streams.stdin.read(_MAX_READ)
    failed = False
    text = ""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        failed = True
    if failed:
        msg = "the key read from standard input is not UTF-8 text"
        raise InputError(msg)
    lines = text.splitlines()
    return lines[0] if lines else ""


def _secret(provider: str, value: str) -> Any:  # noqa: ANN401 - a Secret
    """Wrap the value in a Secret; a value that is no usable key is invalid input."""
    from pyeconomics.data.credentials import Secret  # noqa: PLC0415
    from pyeconomics.data.errors import CredentialError  # noqa: PLC0415

    problem = ""
    try:
        return Secret(provider, value.strip())
    except CredentialError as error:
        problem = str(error)
    raise InputError(problem)


def _where(source: Any, variable: str) -> str:  # noqa: ANN401 - a KeySource
    from pyeconomics.data.credentials import KeySource  # noqa: PLC0415

    if source is KeySource.ENVIRONMENT:
        return f"the environment variable {variable}"
    return f"{variable} in the .env file"


def set_key(
    provider: str,
    /,
    *,
    stdin: Annotated[bool, Parameter(negative="")] = False,
    context: ContextParameter,
) -> None:
    """Store a provider's key in the OS keyring.

    The key is read from a hidden prompt, or with --stdin from the first line
    of standard input: never from an argument, which shell history would keep.
    It is checked before it is stored, and it needs the keyring extra.

    Parameters
    ----------
    provider
        The provider id, such as fred.
    stdin
        Read the key from standard input instead of a hidden prompt.
    """
    from pyeconomics.data.credentials import (  # noqa: PLC0415
        KEYRING_SERVICE,
        KeySource,
        key_source,
        store_key,
    )

    info = _keyed(provider)
    secret = _secret(info.id, _read_value(context, info.id, from_stdin=stdin))
    store_key(info.id, secret)
    message = (
        f"Stored the {info.id} key in the OS keyring (service {KEYRING_SERVICE!r})."
    )
    source = key_source(info.id)
    if source is not None and source is not KeySource.KEYRING:
        message += f" {_where(source, info.key_variable)} still takes precedence."
    context.streams.write(f"{message}\n".encode())


def list_keys(
    *,
    output_format: Annotated[Format, Parameter(name="--format")] = "table",
    out: Annotated[Path | None, Parameter(name="--out")] = None,
    context: ContextParameter,
) -> None:
    """List the providers that use a key, and where each key would be read from.

    The source is the kind of place the key chain would read the key from
    (environment, dotenv, keyring) or none; a key's value is never shown.

    Parameters
    ----------
    output_format
        table, or json for the same fields.
    out
        Write the output to this file instead.
    """
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415
    from pyeconomics.data.credentials import key_source  # noqa: PLC0415
    from pyeconomics.data.providers.base import AuthKind  # noqa: PLC0415

    entries = []
    for info in provider_registry.installed().infos():
        if info.auth.kind is not AuthKind.KEY:
            continue
        source = key_source(info.id)
        entries.append(
            {
                "provider": info.id,
                "variable": info.key_variable,
                "required": info.auth.required,
                "source": "none" if source is None else source.value,
            }
        )
    if output_format == "json":
        emit_json(context.streams, entries, out)
        return
    grid = Grid(
        "Keys",
        ("Provider", "Variable", "Required", "Source"),
        tuple(
            (
                str(entry["provider"]),
                str(entry["variable"]),
                "yes" if entry["required"] else "no",
                str(entry["source"]),
            )
            for entry in entries
        ),
    )
    show(context.streams, [grid], out)


def delete_key(provider: str, /, *, context: ContextParameter) -> None:
    """Delete a provider's key from the OS keyring.

    A key in the environment or the .env file is left where it is. It needs the
    keyring extra.

    Parameters
    ----------
    provider
        The provider id, such as fred.
    """
    from pyeconomics.data.credentials import delete_key as delete  # noqa: PLC0415

    info = _keyed(provider)
    if delete(info.id):
        message = f"Deleted the {info.id} key from the OS keyring."
    else:
        message = f"The OS keyring held no {info.id} key."
    context.streams.write(f"{message}\n".encode())
