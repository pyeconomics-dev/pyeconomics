# src/pyeconomics/data/modes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Library and hosted mode, and the refusal hosted mode makes (ADR-0005, ADR-0011).

``Mode.LIBRARY`` is the default: the library, CLI, local app and MCP server run
under the user's own credentials and their acceptance of each source's terms.
``Mode.HOSTED`` is the public service: it serves only sources classed
``hosted-safe`` or ``user-supplied`` (ADR-0005 rule 1). Set it with
``pyeconomics.data.configure(mode="hosted")`` or ``PYECONOMICS_MODE=hosted``.

:func:`require_allowed` is the refusal. Every public operation of
:class:`~pyeconomics.data.providers.base.DataProvider` calls it before any
request, and so does every transport, so no route bypasses it; the catalog's
resolver (Step 11) checks the same rule earlier, to choose another source
instead of failing.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import CachePolicy, LicenceClass, LlmUse, Terms
>>> terms = Terms(
...     licence=LicenceClass.LIBRARY_ONLY,
...     terms_url="https://example.org/terms",
...     checked=dt.date(2026, 10, 15),
...     attribution="Source: Example.",
...     llm_use=LlmUse.FORBIDDEN,
...     cache=CachePolicy.FORBIDDEN,
... )
>>> require_allowed(terms, provider="demo", mode=Mode.LIBRARY)
>>> try:
...     require_allowed(terms, provider="demo", mode=Mode.HOSTED)
... except PermissionError as error:
...     print(error)
demo is library-only (terms: https://example.org/terms): hosted mode serves only hosted-safe and user-supplied data

"""  # noqa: E501 - doctest output lines cannot wrap

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pyeconomics.data.config import settings
from pyeconomics.data.errors import LicenceError

if TYPE_CHECKING:
    from pyeconomics.data.terms import Terms

__all__ = ["Mode", "current_mode", "require_allowed"]


class Mode(StrEnum):
    """Where pyeconomics runs: on the user's machine, or as the hosted service."""

    LIBRARY = "library"
    """The user's machine, under the user's own credentials."""
    HOSTED = "hosted"
    """The hosted service: only ``hosted-safe`` and ``user-supplied`` data."""


def current_mode() -> Mode:
    """Return the mode the settings select (``PYECONOMICS_MODE`` or ``configure``)."""
    return Mode(settings().mode)


def require_allowed(terms: Terms, *, provider: str, mode: Mode | None = None) -> None:
    """Refuse a source hosted mode may not serve, before anything is requested.

    Parameters
    ----------
    terms
        The terms the data would come under: a provider's, or a series' own
        where its source marks it differently.
    provider
        The provider id, for the message.
    mode
        The mode to judge by; the current one by default.

    Raises
    ------
    LicenceError
        In hosted mode, for a class other than ``hosted-safe`` and
        ``user-supplied``; the message names the class and the terms page.
    """
    if (mode or current_mode()) is Mode.HOSTED and not terms.licence.hosted_allowed:
        reason = "hosted mode serves only hosted-safe and user-supplied data"
        raise LicenceError(
            reason,
            provider=provider,
            licence=terms.licence,
            terms_url=terms.terms_url,
        )
