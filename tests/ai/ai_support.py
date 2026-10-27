# tests/ai/ai_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the AI narrative's tests share (tests/ai, tests/cli).

- :func:`black_scholes` is the result every test narrates, and :func:`with_records`
  gives it data records under any ``llm_use`` class.
- :func:`answer` writes a provider's answer in the shape its API returns
  (read from each API's reference and checked by the live run on 2026-10-26),
  with synthetic text: :data:`MARKER` and the provider's id, so a test can
  search any sink for the narrative.
- :func:`build_cassette` records that answer to the narrative's request for
  :func:`black_scholes`; ``uv run --no-sync python tests/ai/build_ai_cassettes.py``
  writes one cassette per provider under ``tests/ai/cassettes/``, and
  ``test_ai_cassettes.py`` fails if they drift. :func:`replay` serves them.
- :class:`Scripted` is a transport that answers from a script and records what
  it was sent, for status codes and refusals.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pyeconomics
from pyeconomics.ai.defaults import PROVIDER_MODELS
from pyeconomics.ai.prompt import SYSTEM_PROMPT, render_prompt
from pyeconomics.ai.providers import PROVIDERS
from pyeconomics.core.provenance import DataSource, LicenceClass, LlmUse
from pyeconomics.data import configure
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.replay import ReplayTransport

if TYPE_CHECKING:
    from pyeconomics.core.results import Result
    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo

__all__ = [
    "CASSETTES",
    "INPUTS",
    "MARKER",
    "RECORDED_ON",
    "TOKENS",
    "Scripted",
    "answer",
    "black_scholes",
    "build_cassette",
    "enable",
    "ok",
    "replay",
    "with_records",
]

#: The directory the providers' cassettes live in.
CASSETTES: Final = Path(__file__).parent / "cassettes"
#: When the synthetic answers were recorded.
RECORDED_ON: Final = dt.datetime(2026, 10, 26, 12, 0, tzinfo=dt.UTC)
#: The text every synthetic narrative starts with.
MARKER: Final = "SYNTHETIC-NARRATIVE"
#: The input and output tokens each synthetic answer reports.
TOKENS: Final = {
    "anthropic": (1_131, 897),
    "gemini": (893, 1_271),
    "openai": (782, 190),
    "openrouter": (782, 185),
}
#: The Black-Scholes-Merton inputs every test narrates.
INPUTS: Final = {
    "calculation": "price",
    "spot": 42,
    "strike": 40,
    "years": 0.5,
    "risk_free_rate": 0.1,
    "volatility": 0.2,
}


def enable() -> None:
    """Turn the narrative on for the rest of the test."""
    configure(ai_enabled=True)


def black_scholes() -> Result[Any, Any]:
    """Return the result every test narrates."""
    return pyeconomics.run("derivatives.black_scholes_merton", INPUTS)


def with_records(result: Result[Any, Any], *uses: LlmUse) -> Result[Any, Any]:
    """Return the result carrying one data record per ``llm_use`` class given."""
    records = tuple(
        DataSource(
            provider=f"toy_{use.value}",
            series_id="RATE",
            field="risk_free_rate",
            licence=LicenceClass.LIBRARY_ONLY,
            attribution="Source: a toy source.",
            terms_url="https://www.example.org/terms",
            llm_use=use,
        )
        for use in uses
    )
    manifest = dataclasses.replace(result.manifest, data_sources=records)
    return dataclasses.replace(result, manifest=manifest)


def narrative_text(provider: str) -> str:
    """The synthetic narrative a provider's cassette answers."""
    return (
        f"{MARKER} {provider}: the call is worth about 4.76, mostly because the "
        "asset already trades above the strike."
    )


def answer(  # noqa: PLR0913 - one answer's facts
    provider: str,
    text: str | None = None,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    truncated: bool = False,
    model: str | None = None,
) -> dict[str, Any]:
    """Return a provider's answer, in its API's shape, with synthetic text."""
    words = narrative_text(provider) if text is None else text
    tokens_in, tokens_out = TOKENS[provider]
    tokens_in = tokens_in if input_tokens is None else input_tokens
    tokens_out = tokens_out if output_tokens is None else output_tokens
    name = model or PROVIDER_MODELS[provider]
    if provider == "anthropic":
        return {
            "id": "msg_synthetic",
            "type": "message",
            "role": "assistant",
            "model": name,
            "content": [{"type": "text", "text": words}],
            "stop_reason": "max_tokens" if truncated else "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": tokens_in, "output_tokens": tokens_out},
        }
    if provider == "openai":
        return {
            "id": "resp_synthetic",
            "object": "response",
            "model": name,
            "status": "incomplete" if truncated else "completed",
            "incomplete_details": (
                {"reason": "max_output_tokens"} if truncated else None
            ),
            "output": [
                {"type": "reasoning", "id": "rs_synthetic", "summary": []},
                {
                    "type": "message",
                    "id": "msg_synthetic",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": words, "annotations": []}
                    ],
                },
            ],
            "usage": {
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "output_tokens_details": {"reasoning_tokens": tokens_out // 2},
            },
        }
    if provider == "gemini":
        thoughts = tokens_out // 2
        return {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": words}]},
                    "finishReason": "MAX_TOKENS" if truncated else "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": tokens_in,
                "candidatesTokenCount": tokens_out - thoughts,
                "thoughtsTokenCount": thoughts,
                "totalTokenCount": tokens_in + tokens_out,
            },
            "modelVersion": name,
        }
    return {
        "id": "gen-synthetic",
        "object": "chat.completion",
        "model": name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": words},
                "finish_reason": "length" if truncated else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
    }


def ok(document: dict[str, Any], status: int = 200) -> Response:
    """Return a JSON response."""
    return Response(
        status,
        json.dumps(document).encode("utf-8"),
        RECORDED_ON,
        (("content-type", "application/json"),),
    )


def narrative_request(provider: str) -> Request:
    """The request the narrative of :func:`black_scholes` sends to a provider."""
    return PROVIDERS[provider].request(
        PROVIDER_MODELS[provider], SYSTEM_PROMPT, render_prompt(black_scholes())
    )


def build_cassette(provider: str) -> Cassette:
    """Record the provider's synthetic answer to the narrative's request."""
    return Cassette.from_exchanges(
        provider,
        RECORDED_ON,
        [(narrative_request(provider), ok(answer(provider)))],
        synthetic=True,
    )


def replay() -> ReplayTransport:
    """Serve every provider's cassette."""
    return ReplayTransport.from_directory(CASSETTES)


class Scripted:
    """A transport that answers from a script and records what it was sent."""

    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses)
        self.sent: list[tuple[str, Request, object]] = []

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Record the request and return the next scripted response."""
        self.sent.append((info.id, request, key))
        if not self.responses:
            msg = "the transport was not expected to be called"
            raise AssertionError(msg)
        return self.responses.pop(0)
