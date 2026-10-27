# src/pyeconomics/ai/errors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The narrative's own refusals (ADR-0012 decision 17).

Each class has its row in the error table
(:data:`pyeconomics.surfaces.problems.ROWS`). The other refusals reuse the data
layer's classes: :class:`~pyeconomics.data.errors.LlmUseError` for data whose
terms keep it from a language model, :class:`~pyeconomics.data.errors.OfflineError`
in offline mode and :class:`~pyeconomics.data.errors.CredentialError` for a
missing key.
"""

from __future__ import annotations

from pyeconomics.core.errors import PyeconomicsError

__all__ = ["NarrativeDisabledError", "NarrativeHostedError"]


class NarrativeDisabledError(PyeconomicsError):
    """The ``ai_enabled`` setting is off, as it is by default.

    Examples
    --------
    >>> print(NarrativeDisabledError())
    the AI narrative is off; turn it on with ai_enabled = true in pyeconomics.toml or PYECONOMICS_AI_ENABLED=1
    """  # noqa: E501 - doctest output cannot wrap

    def __init__(self) -> None:
        super().__init__(
            "the AI narrative is off; turn it on with ai_enabled = true in "
            "pyeconomics.toml or PYECONOMICS_AI_ENABLED=1"
        )


class NarrativeHostedError(PyeconomicsError):
    """Hosted mode never writes a narrative (until Phase 8 adds a ledger and a cap).

    Examples
    --------
    >>> print(NarrativeHostedError())
    hosted mode does not write AI narratives; run pyeconomics on your own machine with your own key
    """  # noqa: E501 - doctest output cannot wrap

    def __init__(self) -> None:
        super().__init__(
            "hosted mode does not write AI narratives; run pyeconomics on your "
            "own machine with your own key"
        )
