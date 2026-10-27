# tests/ai/test_ai_prompt.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The prompt holds the result's own facts and nothing else (the Step 11 gate).

It names the model, its inputs and outputs with their units, its warnings and
the card's assumptions and limitations. It holds no key, path, host,
environment value or manifest field: a result laden with a canary key, file
paths, a URL, an environment value and data records is rendered and scanned.
"""

from __future__ import annotations

import dataclasses
import secrets

import pytest
from ai_support import black_scholes, with_records
from leakcheck import LeakCheck, canary

from pyeconomics.ai.prompt import (
    MAX_ARRAY_VALUES,
    MAX_PROMPT_CHARACTERS,
    SYSTEM_PROMPT,
    render_prompt,
)
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import LlmUse
from pyeconomics.core.results import ResultWarning

pytestmark = pytest.mark.usefixtures("isolated")


def test_the_prompt_names_the_model_and_every_input_and_output_with_units() -> None:
    result = black_scholes()
    prompt = render_prompt(result)
    spec = result.model.spec
    assert prompt.startswith(
        f"Model: {spec.title} (derivatives.black_scholes_merton, version 1)\n"
    )
    assert f"Summary: {spec.summary}" in prompt
    assert "- spot = 42 (unit: money): Price of the underlying asset now" in prompt
    assert "- risk_free_rate = 0.1 (unit: rate):" in prompt
    assert "- volatility = 0.2 (unit: volatility):" in prompt
    assert "- price = 4.759422392871528 (unit: money): Option price" in prompt
    assert "- delta = 0.7791312909426689 (unit: ratio):" in prompt
    assert "Warnings: none" in prompt
    for assumption in spec.assumptions:
        assert f"- {assumption}" in prompt
    for limitation in spec.limitations:
        assert f"- {limitation}" in prompt


def test_the_prompt_holds_no_manifest_field() -> None:
    result = with_records(black_scholes(), LlmUse.ALLOWED)
    prompt = render_prompt(result)
    manifest = result.manifest
    for value in (
        manifest.result_sha256,
        manifest.inputs_sha256,
        "toy_allowed",
        "https://www.example.org/terms",
        "Source: a toy source.",
        "pyeconomics_version",
        "manifest",
    ):
        assert value not in prompt


def test_the_prompt_lists_the_results_warnings() -> None:
    result = dataclasses.replace(
        black_scholes(),
        warnings=(ResultWarning("revised_data", "The rate is revised data."),),
    )
    assert "Warnings:\n- revised_data: The rate is revised data." in render_prompt(
        result
    )


def test_an_array_shows_its_first_values_and_how_many_follow() -> None:
    import pyeconomics  # noqa: PLC0415

    returns = [0.01 * (index % 7 - 3) for index in range(40)]
    result = pyeconomics.run(
        "foundations.risk_statistics",
        {"calculation": "volatility", "returns": returns, "periods_per_year": 12},
    )
    prompt = render_prompt(result)
    line = next(line for line in prompt.splitlines() if line.startswith("- returns"))
    assert f"... and {40 - MAX_ARRAY_VALUES} more]" in line
    assert line.split("]", maxsplit=1)[0].count(",") == MAX_ARRAY_VALUES


def test_a_canary_laden_result_reaches_the_prompt_scrubbed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = canary("openai")
    folder = f"u{secrets.token_hex(6)}"
    host = f"h{secrets.token_hex(6)}"
    environment = f"e{secrets.token_hex(8)}"
    monkeypatch.setenv("PYECONOMICS_TEST_VALUE", environment)
    laden = (
        f"read C:\\Users\\{folder}\\.env and /home/{folder}/.config/x.toml via "
        f"https://api.{host}.example.org/v1?api_key={key.value} "
        f"(host='api.{host}.example.org') with {key.value}"
    )
    result = dataclasses.replace(
        with_records(black_scholes(), LlmUse.ALLOWED),
        warnings=(ResultWarning("planted", laden),),
    )

    class Needles:
        def needles(self) -> tuple[str, ...]:
            return (*key.needles(), folder, host, environment)

    check = LeakCheck(Needles())
    prompt = render_prompt(result)
    check.add("prompt", prompt)
    check.add("system", SYSTEM_PROMPT)
    check.assert_clean()
    assert "- planted: read" in prompt


def test_a_result_too_large_to_narrate_is_invalid_input() -> None:
    long = "x" * 900
    result = dataclasses.replace(
        black_scholes(),
        warnings=tuple(ResultWarning(f"w{index}", long) for index in range(40)),
    )
    with pytest.raises(InputError, match=str(MAX_PROMPT_CHARACTERS)):
        render_prompt(result)


def test_the_system_prompt_asks_for_plain_facts_and_no_advice() -> None:
    assert "Use only the facts given" in SYSTEM_PROMPT
    assert "do not give investment advice" in SYSTEM_PROMPT
    assert "0.05 means 5%" in SYSTEM_PROMPT


def test_a_model_without_calculations_lists_its_fields_with_units() -> None:
    import pyeconomics  # noqa: PLC0415
    from pyeconomics.core.registry import installed  # noqa: PLC0415

    model = installed().get("accounting.financial_ratios")
    result = pyeconomics.run(model.id, dict(model.spec.examples[0].inputs))
    prompt = render_prompt(result)
    assert "- current_assets = 200 (unit: money):" in prompt
    assert "Outputs:\n- " in prompt
