# src/pyeconomics/ai/defaults.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The narrative's default provider and model, as chosen with the model selector.

The choice is configuration: ``ai_provider`` and ``ai_model`` in
``pyeconomics.toml``, or ``PYECONOMICS_AI_PROVIDER`` and
``PYECONOMICS_AI_MODEL``, replace it. It was made on :data:`CHOSEN_ON` by
running :data:`SELECTOR` (roadmodel 0.2.98) for the narrative's task, a short
plain-language explanation of one result (knowledge, low complexity). Its
Balanced column, the one that runs by default, picked GPT-6.1 Sol at Medium;
the runner-up was Claude Haiku 5.5 and the backup Gemini 3.8 Flash. Each
provider's own default is that ladder's model the provider serves, so a user
who names only a provider gets the selector's choice there too.

Every model runs at its own default reasoning level: GPT-6.1 Sol's is Medium,
the level the selector ranked.

Examples
--------
>>> DEFAULT_PROVIDER, DEFAULT_MODEL
('openai', 'gpt-6.1-sol')
>>> PROVIDER_MODELS["anthropic"]
'claude-haiku-5-5'
"""

from __future__ import annotations

import datetime as dt
from typing import Final

__all__ = [
    "CHOSEN_ON",
    "DEFAULT_MODEL",
    "DEFAULT_PROVIDER",
    "PROVIDER_MODELS",
    "SELECTOR",
]

#: The date the default was chosen.
CHOSEN_ON: Final = dt.date(2026, 10, 26)
#: The model-selector command whose ladder made the choice.
SELECTOR: Final = (
    "roadmodel ladder --category knowledge --complexity low "
    "--user-context planning/user-context.md"
)
#: The provider a narrative uses when no setting or argument names one.
DEFAULT_PROVIDER: Final = "openai"
#: The model of :data:`DEFAULT_PROVIDER` the narrative uses by default.
DEFAULT_MODEL: Final = "gpt-6.1-sol"
#: Each provider's default model: the ladder's choice that the provider serves.
PROVIDER_MODELS: Final = {
    "anthropic": "claude-haiku-5-5",
    "gemini": "gemini-3.8-flash",
    "openai": DEFAULT_MODEL,
    "openrouter": "openai/gpt-6.1-sol",
}
