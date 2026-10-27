# tests/ai/test_ai_narrate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``narrate`` from each provider's recorded answer: text, tokens, cost, notice.

Every provider's synthetic cassette is replayed offline through the data
layer's replaying transport, which applies the hosted-mode and host checks the
real one does. The provider and model come from the argument, then the
settings, then the recorded default; each status a provider can answer maps to
the error taxonomy.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from ai_support import (
    MARKER,
    TOKENS,
    Scripted,
    answer,
    black_scholes,
    enable,
    ok,
    replay,
)
from leakcheck import canary

from pyeconomics.ai import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    NOT_ADVICE,
    PROVIDER_MODELS,
    PROVIDERS,
    narrate,
)
from pyeconomics.ai.prices import PRICES_READ_ON, cost, price_for
from pyeconomics.ai.prompt import SYSTEM_PROMPT
from pyeconomics.ai.providers import MAX_OUTPUT_TOKENS
from pyeconomics.core.errors import InputError
from pyeconomics.data import (
    CredentialError,
    RateLimitError,
    ResponseError,
    TransportError,
    configure,
)
from pyeconomics.data.transport.base import Response

if TYPE_CHECKING:
    from config_isolation import Isolation

PROVIDER_IDS = sorted(PROVIDERS)


@pytest.fixture(autouse=True)
def keys(isolated: Isolation) -> None:
    """Every provider has a (canary) key in the chain; the narrative is on."""
    for provider in PROVIDER_IDS:
        isolated.keyring.set_password("pyeconomics", provider, canary(provider).value)
    enable()


@pytest.mark.parametrize("provider", PROVIDER_IDS)
def test_each_provider_narrates_from_its_recorded_answer(provider: str) -> None:
    result = black_scholes()
    narrative = narrate(result, provider=provider, transport=replay())

    tokens_in, tokens_out = TOKENS[provider]
    assert narrative.text.startswith(f"{MARKER} {provider}:")
    assert narrative.provider == provider
    assert narrative.model == PROVIDER_MODELS[provider]
    assert (narrative.input_tokens, narrative.output_tokens) == (tokens_in, tokens_out)
    price = price_for(provider, narrative.model, dt.date(2026, 10, 26))
    assert price is not None
    assert narrative.cost_usd == cost(
        price, input_tokens=tokens_in, output_tokens=tokens_out
    )
    assert narrative.notice == NOT_ADVICE
    assert narrative.prices_read_on == PRICES_READ_ON
    assert narrative.result_sha256 == result.manifest.result_sha256
    assert not narrative.truncated
    rendered = narrative.render()
    assert rendered.startswith(narrative.text)
    assert NOT_ADVICE in rendered
    assert narrative.cost_line() in rendered


def test_the_cost_is_each_kind_of_token_at_its_list_price() -> None:
    narrative = narrate(black_scholes(), provider="openai", transport=replay())
    # gpt-6.1-sol: $2 per million input tokens and $10 per million output.
    assert (
        narrative.cost_usd
        == Decimal(782) * 2 / 1_000_000 + Decimal(190) * 10 / 1_000_000
    )
    assert narrative.cost_line() == (
        "Cost: $0.0035 (openai gpt-6.1-sol: 782 input and 190 output tokens at "
        "list prices read 2026-10-26)"
    )


def test_gemini_bills_thinking_tokens_as_output() -> None:
    narrative = narrate(black_scholes(), provider="gemini", transport=replay())
    assert narrative.output_tokens == TOKENS["gemini"][1]


def test_the_default_is_the_recorded_choice() -> None:
    transport = Scripted(ok(answer("openai")))
    narrative = narrate(black_scholes(), transport=transport)
    assert (narrative.provider, narrative.model) == (DEFAULT_PROVIDER, DEFAULT_MODEL)
    provider, request, _ = transport.sent[0]
    assert provider == "openai"
    assert request.body["model"] == "gpt-6.1-sol"


def test_the_settings_choose_the_provider_and_model() -> None:
    configure(ai_provider="anthropic", ai_model="claude-sonnet-5-5")
    transport = Scripted(ok(answer("anthropic", model="claude-sonnet-5-5")))
    narrative = narrate(black_scholes(), transport=transport)
    assert (narrative.provider, narrative.model) == ("anthropic", "claude-sonnet-5-5")
    assert narrative.cost_usd == Decimal(1_131 * 2 + 897 * 10) / 1_000_000


def test_a_provider_argument_ignores_another_providers_model_setting() -> None:
    configure(ai_provider="anthropic", ai_model="claude-sonnet-5-5")
    transport = Scripted(ok(answer("gemini")))
    narrative = narrate(black_scholes(), provider="gemini", transport=transport)
    assert narrative.model == PROVIDER_MODELS["gemini"]


def test_a_model_argument_wins() -> None:
    transport = Scripted(ok(answer("openai", model="gpt-6-luna")))
    narrative = narrate(black_scholes(), model="gpt-6-luna", transport=transport)
    assert narrative.model == "gpt-6-luna"


def test_a_model_the_table_lacks_has_no_cost() -> None:
    transport = Scripted(ok(answer("openai")))
    narrative = narrate(black_scholes(), model="gpt-7-preview", transport=transport)
    assert narrative.cost_usd is None
    assert narrative.cost_line().startswith("Cost: unknown (openai gpt-7-preview:")
    assert "has no price for this model" in narrative.cost_line()


def test_a_tiny_cost_reads_as_below_the_smallest_shown() -> None:
    transport = Scripted(ok(answer("openai", input_tokens=10, output_tokens=5)))
    narrative = narrate(black_scholes(), transport=transport)
    assert narrative.cost_line().startswith("Cost: less than $0.0001 (")


@pytest.mark.parametrize("provider", PROVIDER_IDS)
def test_an_answer_cut_at_the_output_limit_says_so(provider: str) -> None:
    transport = Scripted(ok(answer(provider, truncated=True)))
    narrative = narrate(black_scholes(), provider=provider, transport=transport)
    assert narrative.truncated
    assert "(The model stopped at its output limit.)" in narrative.render()


def test_each_request_is_one_post_to_the_declared_host_without_a_key() -> None:
    for provider in PROVIDER_IDS:
        transport = Scripted(ok(answer(provider)))
        narrate(black_scholes(), provider=provider, transport=transport)
        sent_to, request, key = transport.sent[0]
        info = PROVIDERS[provider].info
        assert sent_to == provider
        assert request.method == "POST"
        assert request.host in info.hosts
        assert info.terms.cache.value == "forbidden"
        assert key is not None  # a Secret from the chain, for the transport
        assert SYSTEM_PROMPT in str(request.body)
        assert str(MAX_OUTPUT_TOKENS) in str(request.body)


def test_the_request_shapes() -> None:
    bodies = {}
    for provider in PROVIDER_IDS:
        transport = Scripted(ok(answer(provider)))
        narrate(black_scholes(), provider=provider, transport=transport)
        bodies[provider] = transport.sent[0][1]
    assert bodies["anthropic"].path == "/v1/messages"
    assert ("anthropic-version", "2023-06-01") in bodies["anthropic"].headers
    assert bodies["anthropic"].body["system"] == SYSTEM_PROMPT
    assert bodies["openai"].path == "/v1/responses"
    assert bodies["openai"].body["store"] is False
    assert bodies["openai"].body["input"][0]["role"] == "developer"
    assert bodies["gemini"].path == "/v1beta/models/gemini-3.8-flash:generateContent"
    assert bodies["openrouter"].path == "/api/v1/chat/completions"
    assert bodies["openrouter"].body["messages"][0]["role"] == "system"


def test_a_narrative_drops_control_characters_and_keeps_its_length_bounded() -> None:
    text = "Safe\x1b[31m text\x07 here\n" + "x" * 9_000
    narrative = narrate(
        black_scholes(), transport=Scripted(ok(answer("openai", text=text)))
    )
    assert "\x1b" not in narrative.text
    assert "\x07" not in narrative.text
    assert narrative.text.startswith("Safe[31m text here\n")
    assert len(narrative.text) == 8_000


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, CredentialError),
        (403, CredentialError),
        (429, RateLimitError),
        (500, TransportError),
        (503, TransportError),
        (400, InputError),
        (404, InputError),
        (422, InputError),
        (302, ResponseError),
    ],
)
def test_each_status_maps_to_the_taxonomy(status: int, error: type[Exception]) -> None:
    response = ok({"error": {"message": "no"}}, status=status)
    with pytest.raises(error) as caught:
        narrate(black_scholes(), transport=Scripted(response))
    if status in {401, 403}:
        assert "OPENAI_API_KEY" in str(caught.value)
    if status in {400, 404, 422}:
        assert "gpt-6.1-sol" in str(caught.value)


def test_a_rate_limit_carries_the_providers_advice() -> None:
    response = Response(429, b"{}", ok({}).retrieved_at, (("retry-after", "7"),))
    with pytest.raises(RateLimitError) as caught:
        narrate(black_scholes(), transport=Scripted(response))
    assert caught.value.retry_after == 7.0


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[1, 2]",
        b"{}",
        b'{"usage": {"input_tokens": -1, "output_tokens": 3}}',
        b'{"usage": {"input_tokens": true, "output_tokens": 3}}',
    ],
    ids=["text", "array", "no-usage", "negative", "boolean"],
)
def test_an_unreadable_answer_is_a_response_error(body: bytes) -> None:
    response = Response(200, body, ok({}).retrieved_at)
    with pytest.raises(ResponseError) as caught:
        narrate(black_scholes(), transport=Scripted(response))
    assert body.decode() not in str(caught.value) or body == b"{}"


@pytest.mark.parametrize("provider", PROVIDER_IDS)
def test_an_answer_without_text_is_a_response_error(provider: str) -> None:
    transport = Scripted(ok(answer(provider, text="   ")))
    with pytest.raises(ResponseError, match="returned no text"):
        narrate(black_scholes(), provider=provider, transport=transport)


def test_a_gemini_answer_blocked_before_any_candidate_has_no_text() -> None:
    document = {
        "promptFeedback": {"blockReason": "SAFETY"},
        "usageMetadata": {"promptTokenCount": 10},
    }
    transport = Scripted(ok(document))
    with pytest.raises(ResponseError, match="returned no text"):
        narrate(black_scholes(), provider="gemini", transport=transport)


def test_an_unknown_provider_is_invalid_input() -> None:
    with pytest.raises(InputError, match="the providers are anthropic, gemini"):
        narrate(black_scholes(), provider="acme", transport=Scripted())


@pytest.mark.parametrize("model", ["bad model", "../x", "", "a" * 200])
def test_a_model_id_a_request_cannot_carry_is_invalid_input(model: str) -> None:
    with pytest.raises(InputError):
        narrate(black_scholes(), model=model or "-", transport=Scripted())


def test_a_gemini_model_id_must_be_a_plain_name() -> None:
    with pytest.raises(InputError, match="not a Gemini model name"):
        narrate(
            black_scholes(),
            provider="gemini",
            model="models/gemini:x",
            transport=Scripted(),
        )


def test_the_narrative_transport_reads_patiently_and_retries_little() -> None:
    import pyeconomics.ai.narrative as narrative_module  # noqa: PLC0415
    from pyeconomics.data.transport.http import HttpTransport  # noqa: PLC0415

    narrative_module._transport.cache_clear()  # noqa: SLF001
    transport = narrative_module._transport()  # noqa: SLF001
    assert isinstance(transport, HttpTransport)
    assert transport is narrative_module._transport()  # noqa: SLF001
    assert transport._max_attempts == 3  # noqa: SLF001
    assert transport._read_timeout == 120.0  # noqa: SLF001
    narrative_module._transport.cache_clear()  # noqa: SLF001


def test_the_base_provider_declares_no_request_shape() -> None:
    from pyeconomics.ai.providers import AiProvider  # noqa: PLC0415

    base = AiProvider()
    with pytest.raises(NotImplementedError):
        base.body("m", "s", "p")
    with pytest.raises(NotImplementedError):
        base.reply({})
