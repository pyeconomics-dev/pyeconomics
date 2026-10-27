# tests/ai/test_ai_cassettes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The AI providers' cassettes: synthetic, scrubbed and up to date.

Each cassette records one synthetic answer to the narrative's request for the
shared result. A change to the prompt, a request or the narrated card changes
the request and so the cassette: rebuild them with
``uv run --no-sync python tests/ai/build_ai_cassettes.py``.
"""

from __future__ import annotations

import pytest
from ai_support import CASSETTES, build_cassette

from pyeconomics.ai.providers import PROVIDERS
from pyeconomics.data.transport.cassette import Cassette, scan_text

pytestmark = pytest.mark.usefixtures("isolated")


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_each_cassette_is_the_one_the_builder_writes(provider: str) -> None:
    path = CASSETTES / provider / "narrate.json"
    assert path.read_bytes() == build_cassette(provider).document(), (
        f"{path} is out of date: run uv run --no-sync python "
        "tests/ai/build_ai_cassettes.py"
    )


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_each_cassette_is_synthetic_and_holds_no_secret(provider: str) -> None:
    data = (CASSETTES / provider / "narrate.json").read_bytes()
    cassette = Cassette.from_json(data)
    assert cassette.provider == provider
    assert cassette.synthetic
    assert scan_text(data.decode("utf-8")) == []
    assert len(cassette.requests) == 1


def test_there_is_one_cassette_per_provider() -> None:
    found = sorted(path.parent.name for path in CASSETTES.glob("*/narrate.json"))
    assert found == sorted(PROVIDERS)
