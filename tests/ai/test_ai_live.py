# tests/ai/test_ai_live.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""One live narrative per AI provider, with the maintainer's own key (opt-in).

Run locally only, never in CI:
``uv run pytest -m live --force-enable-socket tests/ai -s``. Each test reads
the provider's key through the credential chain (``<PROVIDER>_API_KEY``, the
``.env`` file or the keyring), narrates one Black-Scholes-Merton result with
the provider's default model, and prints the cost line the pull request records.
A provider with no key in the chain fails: the run is only asked for when the
key is there.
"""

from __future__ import annotations

import sys

import pytest

import pyeconomics
from pyeconomics.ai import PROVIDER_MODELS, PROVIDERS, narrate
from pyeconomics.data import configure

pytestmark = pytest.mark.live

INPUTS = {
    "calculation": "price",
    "spot": 42,
    "strike": 40,
    "years": 0.5,
    "risk_free_rate": 0.1,
    "volatility": 0.2,
}


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_a_live_narrative_has_text_tokens_and_a_cost(provider: str) -> None:
    configure(ai_enabled=True)
    result = pyeconomics.run("derivatives.black_scholes_merton", INPUTS)

    narrative = narrate(result, provider=provider)

    assert narrative.provider == provider
    assert narrative.model == PROVIDER_MODELS[provider]
    assert narrative.text
    assert narrative.input_tokens > 0
    assert narrative.output_tokens > 0
    assert narrative.cost_usd is not None
    assert narrative.result_sha256 == result.manifest.result_sha256
    # The record the PR keeps; a model may write characters a Windows console's
    # code page lacks, so the text is shown with those replaced.
    encoding = sys.stdout.encoding or "utf-8"
    shown = narrative.render().encode(encoding, "replace").decode(encoding)
    print(f"\n{shown}\n")  # noqa: T201
