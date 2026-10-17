# src/pyeconomics/data/errors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The exceptions the data layer raises (ADR-0011 decision 2).

Every one derives from :class:`DataError`, itself a
:class:`~pyeconomics.core.errors.PyeconomicsError`, and from the built-in
exception a caller would expect:

- :class:`ConceptNotFoundError` (``LookupError``): the catalog has no such concept;
- :class:`ProviderNotFoundError` (``LookupError``): no provider has the id;
- :class:`SeriesNotFoundError` (``LookupError``): the source has no such series;
- :class:`CredentialError` (``PermissionError``): a key is missing or refused;
- :class:`LicenceError` (``PermissionError``): a source's licence class bars
  the use, such as a library-only source in hosted mode;
- :class:`RateLimitError` (``RuntimeError``): the source's limit held after
  retries;
- :class:`TransportError` (``ConnectionError``): the request failed;
- :class:`OfflineError` (``ConnectionError``): offline mode has no cached
  copy;
- :class:`ResponseError` (``ValueError``): the source's response is malformed;
- :class:`ConfigError` (``ValueError``): a setting is invalid.

A message never carries a credential, a URL's query or a file path. Callers
pass identifiers, setting names and reasons; as a second line of defence,
every message has the user information, query and fragment of any URL in it
removed, so ``https://api.example.org/v1/x?api_key=...`` reads
``https://api.example.org/v1/x``, and every registered secret replaced
(:mod:`~pyeconomics.data.redaction`).

:class:`DataWarning` is the data layer's warning: a stable ``code`` and a
sentence, scrubbed the same way.

Examples
--------
>>> from pyeconomics.data import SeriesNotFoundError
>>> error = SeriesNotFoundError("fred", "NO_SUCH_SERIES")
>>> print(error)
fred has no series 'NO_SUCH_SERIES'
>>> isinstance(error, LookupError), error.provider
(True, 'fred')

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.core.warnings import PyeconomicsWarning
from pyeconomics.data.redaction import scrub_text, scrub_urls

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.core.provenance import LicenceClass

__all__ = [
    "ConceptNotFoundError",
    "ConfigError",
    "CredentialError",
    "DataError",
    "DataWarning",
    "LicenceError",
    "OfflineError",
    "ProviderNotFoundError",
    "RateLimitError",
    "ResponseError",
    "SeriesNotFoundError",
    "TransportError",
    "scrub_urls",
]

_CODE: Final = re.compile(r"[a-z][a-z0-9_]*")


def _clean(message: str) -> str:
    return scrub_text(scrub_urls(message))


class DataError(PyeconomicsError):
    """Base class of every exception the data layer raises on purpose.

    Parameters
    ----------
    message
        What went wrong. Name identifiers and settings, never a value read
        from the environment, a request URL or a path.
    provider
        The provider id the error concerns, if one.

    """

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(_clean(message))
        self.provider = provider


class ProviderNotFoundError(DataError, LookupError):
    """No registered provider has the requested id.

    Examples
    --------
    >>> print(ProviderNotFoundError("fredd", close_matches=("fred",)))
    no data provider is registered with id 'fredd'; did you mean 'fred'?

    """

    def __init__(self, provider_id: str, *, close_matches: Sequence[str] = ()) -> None:
        message = f"no data provider is registered with id {provider_id!r}"
        if close_matches:
            message += "; did you mean " + " or ".join(map(repr, close_matches)) + "?"
        super().__init__(message, provider=provider_id)
        self.close_matches = tuple(close_matches)


class ConceptNotFoundError(DataError, LookupError):
    """The catalog has no concept with the requested id.

    Examples
    --------
    >>> print(ConceptNotFoundError("us.inflation.pce", close_matches=("us.prices.pce",)))
    no catalog concept has id 'us.inflation.pce'; did you mean 'us.prices.pce'?
    """  # noqa: E501 - doctest output lines cannot wrap

    def __init__(self, concept_id: str, *, close_matches: Sequence[str] = ()) -> None:
        message = f"no catalog concept has id {concept_id!r}"
        if close_matches:
            message += "; did you mean " + " or ".join(map(repr, close_matches)) + "?"
        super().__init__(message)
        self.concept_id = concept_id
        self.close_matches = tuple(close_matches)


class SeriesNotFoundError(DataError, LookupError):
    """The source has no series, or table, with the requested id."""

    def __init__(self, provider: str, series_id: str) -> None:
        super().__init__(f"{provider} has no series {series_id!r}", provider=provider)
        self.series_id = series_id


class CredentialError(DataError, PermissionError):
    """A credential a source needs is missing, invalid or refused.

    The message names where a key may be set (an environment variable or a
    setting), never the key.
    """


class LicenceError(DataError, PermissionError):
    """A source's licence class bars the requested use.

    Examples
    --------
    >>> from pyeconomics.core.provenance import LicenceClass
    >>> print(LicenceError(
    ...     "hosted mode serves only hosted-safe and user-supplied data",
    ...     provider="fred",
    ...     licence=LicenceClass.LIBRARY_ONLY,
    ...     terms_url="https://fred.stlouisfed.org/docs/api/terms_of_use.html",
    ... ))
    fred is library-only (terms: https://fred.stlouisfed.org/docs/api/terms_of_use.html): hosted mode serves only hosted-safe and user-supplied data

    """  # noqa: E501 - doctest output lines cannot wrap

    def __init__(
        self,
        reason: str,
        *,
        provider: str,
        licence: LicenceClass,
        terms_url: str | None = None,
    ) -> None:
        terms = f" (terms: {terms_url})" if terms_url else ""
        super().__init__(
            f"{provider} is {licence.value}{terms}: {reason}", provider=provider
        )
        self.licence = licence
        self.terms_url = terms_url


class RateLimitError(DataError, RuntimeError):
    """The source's rate limit still held after the permitted retries.

    Parameters
    ----------
    message
        What was limited.
    provider
        The provider id.
    retry_after
        Seconds the source asked the caller to wait, when it said.

    """

    def __init__(
        self, message: str, *, provider: str, retry_after: float | None = None
    ) -> None:
        super().__init__(message, provider=provider)
        self.retry_after = retry_after


class TransportError(DataError, ConnectionError):
    """A request to a source failed: a timeout, a refused connection or a 5xx."""


class OfflineError(DataError, ConnectionError):
    """Offline mode was asked for data it has no cached copy of."""


class ResponseError(DataError, ValueError):
    """A source's response is malformed or does not match what was asked."""


class ConfigError(DataError, ValueError):
    """A setting is invalid, or a configuration file holds a secret."""


class DataWarning(PyeconomicsWarning):
    """A condition in the data layer a user should know about.

    Parameters
    ----------
    code
        A stable snake_case identifier, such as
        ``"credentials_file_permissions"``.
    message
        A sentence for people. Like an error's message, it is scrubbed of
        URL queries and registered secrets.

    Raises
    ------
    ValueError
        If ``code`` is not snake_case.

    Examples
    --------
    >>> warning = DataWarning("keyring_backend_failed", "the keyring step was skipped")
    >>> print(warning)
    the keyring step was skipped [keyring_backend_failed]
    >>> warning.code
    'keyring_backend_failed'

    """

    def __init__(self, code: str, message: str) -> None:
        if not _CODE.fullmatch(code):
            msg = f"a warning code is snake_case, not {code!r}"
            raise ValueError(msg)
        text = _clean(message)
        super().__init__(f"{text} [{code}]")
        self.code = code
        self.text = text
