# src/pyeconomics/data/credentials/secret.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The secret type: one provider's key, held so nothing prints or stores it.

ADR-0011 decisions 12 and 13. A key is a :class:`Secret` from the moment it is
read. Its ``repr``, ``str`` and ``format`` show only a mask naming the
provider; it refuses pickling, ``json`` and canonical JSON; it compares in
constant time. Creating one registers its value, and the value's URL-encoded
forms, with :mod:`~pyeconomics.data.redaction`, which scrubs them from every
log record, URL, header and exception message until :meth:`Secret.forget`.

Only the credential and transport modules call :meth:`Secret.reveal`; the
``secret-reveal`` semgrep rule refuses it anywhere else.

Examples
--------
>>> import secrets
>>> key = Secret("fred", secrets.token_hex(16))
>>> key
<Secret fred: redacted>
>>> f"{key}" == str(key) == repr(key)
True
>>> key.forget()

"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING, Final, NoReturn, final

from pyeconomics.core._fields import identifier
from pyeconomics.data import redaction
from pyeconomics.data.errors import CredentialError

if TYPE_CHECKING:
    from typing import Self, SupportsIndex

__all__ = ["MAX_KEY_LENGTH", "MIN_KEY_LENGTH", "Secret", "key_problem"]

#: The shortest key accepted: scrubbing a shorter one would mangle logs.
MIN_KEY_LENGTH: Final = redaction.MIN_SECRET_LENGTH
#: The longest key accepted.
MAX_KEY_LENGTH: Final = 1_024


def key_problem(value: object) -> str | None:
    """Say what is wrong with a key, without its value, or return ``None``.

    A key is text of :data:`MIN_KEY_LENGTH` to :data:`MAX_KEY_LENGTH`
    printable ASCII characters with no spaces, which is what every supported
    source issues and what a request header can carry safely.

    Examples
    --------
    >>> key_problem("short")
    'is shorter than 8 characters'
    >>> key_problem(12345678)
    'must be text, not int'

    """
    if not isinstance(value, str):
        return f"must be text, not {type(value).__name__}"
    if not value:
        return "is empty"
    if len(value) < MIN_KEY_LENGTH:
        return f"is shorter than {MIN_KEY_LENGTH} characters"
    if len(value) > MAX_KEY_LENGTH:
        return f"is longer than {MAX_KEY_LENGTH} characters"
    if not all("!" <= character <= "~" for character in value):
        return "holds a space, a control character or a non-ASCII character"
    return None


@final
class Secret:
    """One provider's key.

    Parameters
    ----------
    provider
        The provider id the key belongs to (snake_case).
    value
        The key: :data:`MIN_KEY_LENGTH` to :data:`MAX_KEY_LENGTH` printable
        ASCII characters with no spaces.

    Raises
    ------
    CredentialError
        If the value is not a usable key; the message says why, never what.
    InputError
        If the provider id is not snake_case.
    """

    __slots__ = ("_provider", "_registered", "_value")

    _provider: str
    _registered: bool
    _value: str

    def __init__(self, provider: str, value: str) -> None:
        checked = identifier(provider, "a secret's provider")
        problem = key_problem(value)
        if problem is not None:
            msg = f"a {checked} key {problem}"
            raise CredentialError(msg, provider=checked)
        object.__setattr__(self, "_provider", checked)
        object.__setattr__(self, "_value", value)
        redaction.register(value)
        object.__setattr__(self, "_registered", True)

    def __init_subclass__(cls) -> NoReturn:
        """Refuse subclasses, which could override the mask."""
        msg = "Secret cannot be subclassed"
        raise TypeError(msg)

    @property
    def provider(self) -> str:
        """The provider id the key belongs to."""
        return self._provider

    def reveal(self) -> str:
        """Return the key itself.

        Only the credential and transport modules call this (the
        ``secret-reveal`` semgrep rule).
        """
        return self._value

    def forget(self) -> None:
        """Withdraw the key from redaction, once it can no longer be printed.

        The secret still holds the key; only the scrubbers stop looking for
        it. Calling this again does nothing.
        """
        if self._registered:
            object.__setattr__(self, "_registered", False)
            redaction.unregister(self._value)

    def __repr__(self) -> str:
        """Return the mask: the provider's name and nothing of the key."""
        return f"<Secret {self._provider}: redacted>"

    __str__ = __repr__

    def __format__(self, format_spec: str) -> str:
        """Return the mask, whatever the format specification."""
        return repr(self)

    def __eq__(self, other: object) -> bool:
        """Compare two secrets' providers, then their keys in constant time."""
        if not isinstance(other, Secret):
            return NotImplemented
        return self._provider == other._provider and hmac.compare_digest(
            self._value.encode("utf-8"), other._value.encode("utf-8")
        )

    def __hash__(self) -> int:
        """Hash the provider only, so no hash depends on the key."""
        return hash((Secret, self._provider))

    def __setattr__(self, name: str, value: object) -> NoReturn:
        """Refuse every assignment: a secret is immutable."""
        msg = "a Secret is immutable"
        raise AttributeError(msg)

    def __delattr__(self, name: str) -> NoReturn:
        """Refuse every deletion: a secret is immutable."""
        msg = "a Secret is immutable"
        raise AttributeError(msg)

    def __reduce__(self) -> NoReturn:
        """Refuse pickling: a pickle would hold the key in plain text."""
        msg = "a Secret cannot be pickled"
        raise TypeError(msg)

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        """Refuse pickling under every protocol."""
        msg = "a Secret cannot be pickled"
        raise TypeError(msg)

    def __getstate__(self) -> NoReturn:
        """Refuse to give up the state a pickle or a copy would hold."""
        msg = "a Secret cannot be pickled"
        raise TypeError(msg)

    def __copy__(self) -> Self:
        """Return the secret itself: it is immutable."""
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        """Return the secret itself: it is immutable."""
        return self
