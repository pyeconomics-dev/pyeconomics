# src/pyeconomics/ai/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The optional AI narrative: a plain-language reading of one result.

ADR-0012 decision 17. :func:`narrate` asks a language model, with the user's own
key, to explain a result in plain words, and returns a :class:`Narrative` with
the provider, the model, the tokens, the cost from a dated price table and a
"not investment advice" notice. It is off by default (the ``ai_enabled``
setting), refuses hosted mode, offline mode and data whose terms keep it from a
language model, and sends only the result's own facts through a fixed prompt.

The providers (``anthropic``, ``gemini``, ``openai``, ``openrouter``) are
declared like data providers and called through the data layer's HTTPS
transport, so the ``[ai]`` extra installs nothing and a key never leaves the
credential chain and the transport. No MCP tool or hosted route narrates; the
command line's ``models run ... --narrate`` does.

Examples
--------
>>> from pyeconomics import ai
>>> sorted(ai.PROVIDERS)
['anthropic', 'gemini', 'openai', 'openrouter']
"""

from __future__ import annotations

from pyeconomics.ai.defaults import DEFAULT_MODEL, DEFAULT_PROVIDER, PROVIDER_MODELS
from pyeconomics.ai.errors import NarrativeDisabledError, NarrativeHostedError
from pyeconomics.ai.narrative import NOT_ADVICE, Narrative, narrate
from pyeconomics.ai.providers import PROVIDERS

__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_PROVIDER",
    "NOT_ADVICE",
    "PROVIDERS",
    "PROVIDER_MODELS",
    "Narrative",
    "NarrativeDisabledError",
    "NarrativeHostedError",
    "narrate",
]
