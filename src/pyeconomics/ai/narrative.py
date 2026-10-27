# src/pyeconomics/ai/narrative.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``narrate``: a plain-language narrative of one result, with its cost.

ADR-0012 decision 17. :func:`narrate` refuses, before any request:

1. hosted mode (:class:`~pyeconomics.ai.errors.NarrativeHostedError`), until
   Phase 8 adds a ledger and a cap;
2. the default setting, ``ai_enabled = false``
   (:class:`~pyeconomics.ai.errors.NarrativeDisabledError`);
3. offline mode (:class:`~pyeconomics.data.errors.OfflineError`);
4. a result that carries data whose terms keep it from a language model,
   ``forbidden``, or ``unclear`` without the user's out-of-band opt-in
   (:class:`~pyeconomics.data.errors.LlmUseError`, through
   :func:`pyeconomics.surfaces.gate.check_records`);
5. a provider with no key in the chain
   (:class:`~pyeconomics.data.errors.CredentialError`, naming the variable).

It then sends the fixed prompt (:mod:`pyeconomics.ai.prompt`) through the data
layer's HTTPS transport and returns a :class:`Narrative`: the text, the
provider and model, the tokens, the cost from the dated price table
(:mod:`pyeconomics.ai.prices`) and the notice. A narrative is never stored: it
is not part of the result, so no export, bundle or cache holds it.
"""

from __future__ import annotations

import functools
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.ai.defaults import DEFAULT_PROVIDER, PROVIDER_MODELS
from pyeconomics.ai.errors import NarrativeDisabledError, NarrativeHostedError
from pyeconomics.ai.prices import PRICES_READ_ON, cost, price_for
from pyeconomics.ai.prompt import SYSTEM_PROMPT, render_prompt
from pyeconomics.ai.providers import PROVIDERS
from pyeconomics.core.errors import InputError
from pyeconomics.data import modes
from pyeconomics.data.config import settings
from pyeconomics.data.credentials import resolve_key
from pyeconomics.data.errors import OfflineError
from pyeconomics.surfaces.gate import check_records

if TYPE_CHECKING:
    import datetime as dt
    from decimal import Decimal

    from pyeconomics.ai.providers import AiProvider
    from pyeconomics.core.results import Result
    from pyeconomics.data.transport.base import Transport

__all__ = ["MAX_NARRATIVE_CHARACTERS", "NOT_ADVICE", "Narrative", "narrate"]

#: The notice every narrative carries.
NOT_ADVICE: Final = (
    "Written by a language model from this result alone: it may be wrong, and "
    "it is not investment advice."
)
#: The longest narrative kept, in characters.
MAX_NARRATIVE_CHARACTERS: Final = 8_000
#: The smallest cost the cost line shows; anything less reads as below it.
_SMALLEST: Final = "0.0001"
# Control characters a terminal could act on; a newline and a tab stay.
_CONTROL: Final = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class Narrative:
    """A narrative of one result, what wrote it and what it cost.

    Examples
    --------
    >>> import datetime as dt
    >>> from decimal import Decimal
    >>> narrative = Narrative(
    ...     text="The bond is worth 98.2.", provider="openai", model="gpt-6.1-sol",
    ...     input_tokens=1_200, output_tokens=300, cost_usd=Decimal("0.0054"),
    ...     prices_read_on=dt.date(2026, 10, 26), result_sha256="ab" * 32,
    ... )
    >>> print(narrative.cost_line())
    Cost: $0.0054 (openai gpt-6.1-sol: 1,200 input and 300 output tokens at list prices read 2026-10-26)
    """  # noqa: E501 - doctest output cannot wrap

    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal | None
    """The cost in US dollars, or ``None`` when the price table lacks the model."""
    prices_read_on: dt.date
    result_sha256: str
    """The result the narrative describes."""
    truncated: bool = False
    """Whether the model stopped at the output limit."""
    notice: str = NOT_ADVICE

    def cost_line(self) -> str:
        """Say what the narrative cost, or that the price table cannot say."""
        tokens = (
            f"{self.provider} {self.model}: {self.input_tokens:,} input and "
            f"{self.output_tokens:,} output tokens"
        )
        if self.cost_usd is None:
            return (
                f"Cost: unknown ({tokens}; the price table read "
                f"{self.prices_read_on} has no price for this model)"
            )
        shown = (
            f"less than ${_SMALLEST}"
            if self.cost_usd < type(self.cost_usd)(_SMALLEST)
            else f"${self.cost_usd:.4f}"
        )
        return f"Cost: {shown} ({tokens} at list prices read {self.prices_read_on})"

    def render(self) -> str:
        """Return the narrative as text: itself, the notice, then the cost line."""
        lines = [self.text]
        if self.truncated:
            lines.append("(The model stopped at its output limit.)")
        lines += ["", self.notice, self.cost_line()]
        return "\n".join(lines)


@functools.cache
def _transport() -> Transport:
    """Return the process's narrative transport: patient reads, few retries.

    A model can take a minute to answer, and a retried request after a read
    timeout may be billed twice, so it reads for longer and retries less than
    the data layer's default transport.
    """
    from pyeconomics.data.transport.http import HttpTransport  # noqa: PLC0415

    return HttpTransport(max_attempts=3, read_timeout=120.0, max_duration=180.0)


def _provider(name: str) -> AiProvider:
    chosen = PROVIDERS.get(name)
    if chosen is None:
        msg = (
            f"{name!r} is not an AI provider; the providers are "
            f"{', '.join(sorted(PROVIDERS))}"
        )
        raise InputError(msg)
    return chosen


def _clean(text: str) -> str:
    kept = _CONTROL.sub("", text).strip()
    return kept[:MAX_NARRATIVE_CHARACTERS]


def narrate(
    result: Result[Any, Any],
    *,
    provider: str | None = None,
    model: str | None = None,
    transport: Transport | None = None,
) -> Narrative:
    """Write a plain-language narrative of a result with the user's own key.

    Parameters
    ----------
    result
        The result to narrate.
    provider
        ``"anthropic"``, ``"gemini"``, ``"openai"`` or ``"openrouter"``; the
        ``ai_provider`` setting, or :data:`~pyeconomics.ai.defaults.
        DEFAULT_PROVIDER`, when ``None``.
    model
        The provider's model id; the ``ai_model`` setting when it belongs to the
        same provider, or the provider's default, when ``None``.
    transport
        The transport to send through; tests pass a replaying one.

    Returns
    -------
    Narrative
        The narrative, with its tokens, cost and notice.

    Raises
    ------
    NarrativeHostedError
        In hosted mode.
    NarrativeDisabledError
        When the ``ai_enabled`` setting is off, as it is by default.
    OfflineError
        In offline mode.
    LlmUseError
        If the result carries data whose terms keep it from a language model.
    InputError
        For an unknown provider, a model id a request cannot carry, a model
        the provider refuses, or a result too large to narrate.
    CredentialError
        If the chain holds no key for the provider, or the provider refuses
        it; the message names the variable, never a value.
    TransportError, RateLimitError, ResponseError
        If the provider cannot be reached, limits the request, or answers in a
        way that cannot be read.
    """
    if modes.current_mode() is modes.Mode.HOSTED:
        raise NarrativeHostedError
    configured = settings()
    if not configured.ai_enabled:
        raise NarrativeDisabledError
    name = provider or configured.ai_provider or DEFAULT_PROVIDER
    chosen = _provider(name)
    if configured.offline:
        msg = f"offline mode sends no request: a narrative needs {name}"
        raise OfflineError(msg, provider=name)
    check_records(
        result.manifest.data_sources,
        configured.llm_use_policy,
        subject="the result",
    )
    configured_provider = configured.ai_provider or DEFAULT_PROVIDER
    model_id = (
        model
        or (configured.ai_model if name == configured_provider else None)
        or PROVIDER_MODELS[name]
    )
    request = chosen.request(model_id, SYSTEM_PROMPT, render_prompt(result))
    key = resolve_key(name)
    response = (transport or _transport()).send(chosen.info, request, key=key)
    reply = chosen.read(response, model_id)
    price = price_for(name, model_id, response.retrieved_at.date())
    spent = (
        None
        if price is None
        else cost(
            price, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens
        )
    )
    # Counts only: the credential-logging rule reads "token" in a name as a key.
    sent, written = reply.input_tokens, reply.output_tokens
    _logger.info(
        "narrative from %s %s: %d input and %d output units",
        name,
        model_id,
        sent,
        written,
    )
    return Narrative(
        text=_clean(reply.text),
        provider=name,
        model=model_id,
        input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens,
        cost_usd=spent,
        prices_read_on=PRICES_READ_ON,
        result_sha256=result.manifest.result_sha256,
        truncated=reply.truncated,
    )
