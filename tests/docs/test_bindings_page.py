# tests/docs/test_bindings_page.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data guide's example of a model page's "Data" section is the real thing.

No registered model declares bindings yet, so the documentation preview has no
bound model page to show; the guide carries an example, and this test holds it to
what the card generator writes, so it cannot drift from it.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import bound_support as bs

from pyeconomics.core import Binding, Model, VintagePolicy
from pyeconomics.core.cards import ModelCard

PAGE = Path(__file__).resolve().parents[2] / "docs" / "data" / "bindings.md"


def example_model() -> Model[Any, Any]:
    spec = dataclasses.replace(
        bs.unemployment.spec,
        id="macro.example_rule",
        bindings=(
            Binding("unemployment", "us.unemployment.rate"),
            Binding(
                "unemployment",
                "us.unemployment.rate",
                vintage=VintagePolicy.LATEST,
                profile="revised",
            ),
        ),
    )
    return Model(spec, bs.unemployment.compute)


def test_the_guides_example_is_what_the_card_generator_writes() -> None:
    page = PAGE.read_text(encoding="utf-8")
    (shown,) = re.findall(r"```markdown\n(## Data\n.*?)```", page, flags=re.DOTALL)
    card = ModelCard.from_model(example_model()).to_markdown()
    written = "## Data\n" + card.split("## Data\n", 1)[1].split("\n## ", 1)[0]
    assert shown.rstrip("\n") == written.rstrip("\n")
