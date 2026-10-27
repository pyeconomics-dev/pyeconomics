# src/pyeconomics/ai/providers.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The AI providers, declared like data providers (ADR-0012 decision 17).

Each :class:`AiProvider` holds a :class:`~pyeconomics.data.providers.base.
ProviderInfo`: its exact HTTPS host, its key slot (an
:class:`~pyeconomics.data.providers.base.Authentication` the transport fills from
the key chain, ``<PROVIDER>_API_KEY``), a rate limit and a response size cap.
It builds one :class:`~pyeconomics.data.transport.base.Request`, which carries
no key, and reads the answer with :meth:`~pyeconomics.data.transport.base.
Response.json`. The data layer's HTTPS transport sends it, so no client library
is installed and no key leaves ``data/credentials/`` and ``data/transport/``.

The four providers and the APIs they call, read on 2026-10-26:

- ``anthropic``: the Messages API, ``POST api.anthropic.com/v1/messages``, the
  key in ``x-api-key`` and ``anthropic-version: 2023-06-01``; ``usage`` gives
  ``input_tokens`` and ``output_tokens``.
- ``openai``: the Responses API, ``POST api.openai.com/v1/responses``, a bearer
  key, ``store: false`` so the answer is not kept for later retrieval;
  ``usage`` gives ``input_tokens`` and ``output_tokens`` (reasoning included).
- ``gemini``: the Gemini API's ``generateContent``, ``POST
  generativelanguage.googleapis.com/v1beta/models/<model>:generateContent``,
  the key in ``x-goog-api-key``; ``usageMetadata`` gives
  ``promptTokenCount``, ``candidatesTokenCount`` and ``thoughtsTokenCount``,
  the last two both billed as output.
- ``openrouter``: OpenRouter's chat completions, ``POST
  openrouter.ai/api/v1/chat/completions``, a bearer key; ``usage`` gives
  ``prompt_tokens`` and ``completion_tokens`` (reasoning included).

The providers' terms are declared library-only with storage forbidden, so the
transport would refuse them in hosted mode even if the narrative did not, and
nothing writes an answer to the cache.

Examples
--------
>>> sorted(PROVIDERS)
['anthropic', 'gemini', 'openai', 'openrouter']
>>> PROVIDERS["gemini"].info.key_variable
'GEMINI_API_KEY'
>>> request = PROVIDERS["anthropic"].request("claude-haiku-5-5", "Be brief.", "Hi.")
>>> request.host, request.path, request.method
('api.anthropic.com', '/v1/messages', 'POST')
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final

from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    CredentialError,
    RateLimitError,
    ResponseError,
    TransportError,
)
from pyeconomics.data.providers.base import (
    Authentication,
    KeyPlacement,
    ProviderInfo,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, retry_after_seconds

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "MAX_OUTPUT_TOKENS",
    "MAX_RESPONSE_BYTES",
    "MODEL_PATTERN",
    "PROVIDERS",
    "AiProvider",
    "Anthropic",
    "Gemini",
    "OpenAI",
    "OpenRouter",
    "Reply",
]

#: The most tokens a narrative may produce, reasoning included: the ceiling on
#: what one narrative can cost.
MAX_OUTPUT_TOKENS: Final = 4_096
#: The largest answer the transport reads, in bytes.
MAX_RESPONSE_BYTES: Final = 1_048_576
#: A model id: letters, digits and ``.``, ``_``, ``:``, ``/``, ``-`` (OpenRouter
#: names a model ``<maker>/<model>``).
MODEL_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
# The narrative's own ceiling, below every provider's lowest paid tier.
_RATE: Final = (RateLimit(requests=30, per="minute"),)
_TERMS_CHECKED: Final = dt.date(2026, 10, 26)
_HTTP_OK: Final = 200
_CLIENT_ERRORS: Final = frozenset({400, 404, 422})
_SERVER_ERROR: Final = 500
_REPOSITORY: Final = "https://github.com/pyeconomics-dev/pyeconomics"


@dataclass(frozen=True, slots=True)
class Reply:
    """What a provider answered: the text, the tokens and whether it finished."""

    text: str
    input_tokens: int
    output_tokens: int
    truncated: bool = False
    """Whether the answer stopped at the output limit."""


def _terms(name: str, url: str) -> Terms:
    return Terms(
        licence=LicenceClass.LIBRARY_ONLY,
        terms_url=url,
        checked=_TERMS_CHECKED,
        attribution=f"Narrative written by a {name} model.",
        llm_use=LlmUse.ALLOWED,
        cache=CachePolicy.FORBIDDEN,
    )


def _info(  # noqa: PLR0913, PLR0917 - one provider's declaration, field by field
    provider_id: str,
    name: str,
    homepage: str,
    terms_url: str,
    host: str,
    auth: Authentication,
) -> ProviderInfo:
    return ProviderInfo(
        id=provider_id,
        name=name,
        homepage=homepage,
        terms=_terms(name, terms_url),
        auth=auth,
        hosts=(host,),
        rate_limits=_RATE,
        max_response_bytes=MAX_RESPONSE_BYTES,
        follow_redirects=False,
    )


def _count(value: object, what: str, provider: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        msg = f"{provider}'s answer has no usable {what}"
        raise ResponseError(msg, provider=provider)
    return value


def _mapping(value: object, what: str, provider: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        msg = f"{provider}'s answer has no {what}"
        raise ResponseError(msg, provider=provider)
    return value


def _texts(parts: object, kind: str | None) -> str:
    """Join the text of content parts, keeping only those of ``kind`` if given."""
    if not isinstance(parts, list):
        return ""
    texts = [
        part["text"]
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("text"), str)
        and (kind is None or part.get("type") == kind)
        and not part.get("thought")
    ]
    return "".join(texts)


class AiProvider:
    """One AI provider: its declaration, its request and how to read its answer.

    A subclass sets :attr:`info` and :attr:`path` and implements :meth:`body`
    and :meth:`reply`. :meth:`read` checks the status first: 401 and 403 are a
    refused key, 429 a rate limit, 5xx an outage, and 400, 404 and 422 a model
    or request the provider would not take.
    """

    info: ClassVar[ProviderInfo]
    path: ClassVar[str]
    headers: ClassVar[tuple[tuple[str, str], ...]] = ()

    @property
    def id(self) -> str:
        """The provider's id."""
        return self.info.id

    def request_path(self, model: str) -> str:  # noqa: ARG002 - one provider needs it
        """Return the request's path for a model."""
        return self.path

    def body(self, model: str, system: str, prompt: str) -> dict[str, object]:
        """Return the JSON body that asks the model for the narrative."""
        raise NotImplementedError

    def reply(self, document: Mapping[str, Any]) -> Reply:
        """Read the answer's text and token counts."""
        raise NotImplementedError

    def request(self, model: str, system: str, prompt: str) -> Request:
        """Build the request: no key, which the transport attaches.

        Raises
        ------
        InputError
            If the model id is not one a request may carry.
        """
        if not MODEL_PATTERN.fullmatch(model):
            msg = f"{model!r} is not a model id"
            raise InputError(msg)
        return Request(
            host=self.info.hosts[0],
            path=self.request_path(model),
            method="POST",
            body=self.body(model, system, prompt),
            headers=self.headers,
        )

    def read(self, response: Response, model: str) -> Reply:
        """Check the status, then read the answer.

        Raises
        ------
        CredentialError
            For 401 or 403, naming the key's variable, never its value.
        RateLimitError
            For 429.
        TransportError
            For a 5xx.
        InputError
            For 400, 404 or 422: the provider refused the model or the request.
        ResponseError
            For any other status, or an answer that cannot be read. No message
            repeats the body.
        """
        status, provider = response.status, self.id
        if status in {401, 403}:
            msg = (
                f"{provider} refused the key (HTTP {status}); check "
                f"{self.info.key_variable}"
            )
            raise CredentialError(msg, provider=provider)
        if status == 429:  # noqa: PLR2004 - HTTP too many requests
            wait = retry_after_seconds(
                response.header("retry-after"), response.retrieved_at
            )
            msg = f"{provider} is rate limiting requests (HTTP 429)"
            raise RateLimitError(msg, provider=provider, retry_after=wait)
        if status >= _SERVER_ERROR:
            msg = f"{provider} failed with HTTP {status}"
            raise TransportError(msg, provider=provider)
        if status in _CLIENT_ERRORS:
            msg = (
                f"{provider} refused the request for model {model!r} "
                f"(HTTP {status}); check the ai_model setting"
            )
            raise InputError(msg)
        if status != _HTTP_OK:
            msg = (
                f"{provider} answered HTTP {status}, which a narrative does not expect"
            )
            raise ResponseError(msg, provider=provider)
        reply = self.reply(_mapping(response.json(provider=provider), "body", provider))
        if not reply.text.strip():
            msg = f"{provider} returned no text"
            raise ResponseError(msg, provider=provider)
        return reply


class Anthropic(AiProvider):
    """Anthropic's Messages API."""

    info = _info(
        "anthropic",
        "Anthropic",
        "https://www.anthropic.com",
        "https://www.anthropic.com/legal/commercial-terms",
        "api.anthropic.com",
        Authentication.key("x-api-key", KeyPlacement.HEADER),
    )
    path = "/v1/messages"
    headers = (("anthropic-version", "2023-06-01"),)

    def body(self, model: str, system: str, prompt: str) -> dict[str, object]:
        """Ask for one message: the prompt as the user's turn."""
        return {
            "model": model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }

    def reply(self, document: Mapping[str, Any]) -> Reply:
        """Read the text blocks and ``usage``."""
        usage = _mapping(document.get("usage"), "usage", self.id)
        return Reply(
            text=_texts(document.get("content"), "text"),
            input_tokens=_count(usage.get("input_tokens"), "input tokens", self.id),
            output_tokens=_count(usage.get("output_tokens"), "output tokens", self.id),
            truncated=document.get("stop_reason") == "max_tokens",
        )


class OpenAI(AiProvider):
    """OpenAI's Responses API."""

    info = _info(
        "openai",
        "OpenAI",
        "https://openai.com",
        "https://openai.com/policies/services-agreement",
        "api.openai.com",
        Authentication.key("Authorization", KeyPlacement.HEADER, scheme="Bearer"),
    )
    path = "/v1/responses"

    def body(self, model: str, system: str, prompt: str) -> dict[str, object]:
        """Ask for one response, not stored for later retrieval."""
        return {
            "model": model,
            "input": [
                {"role": "developer", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "store": False,
        }

    def reply(self, document: Mapping[str, Any]) -> Reply:
        """Read the message items' ``output_text`` and ``usage``."""
        usage = _mapping(document.get("usage"), "usage", self.id)
        output = document.get("output")
        items = output if isinstance(output, list) else []
        text = "".join(
            _texts(item.get("content"), "output_text")
            for item in items
            if isinstance(item, dict) and item.get("type") == "message"
        )
        details = document.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        return Reply(
            text=text,
            input_tokens=_count(usage.get("input_tokens"), "input tokens", self.id),
            output_tokens=_count(usage.get("output_tokens"), "output tokens", self.id),
            truncated=reason == "max_output_tokens",
        )


class Gemini(AiProvider):
    """Google's Gemini API (``generateContent``)."""

    info = _info(
        "gemini",
        "Google Gemini",
        "https://ai.google.dev",
        "https://ai.google.dev/gemini-api/terms",
        "generativelanguage.googleapis.com",
        Authentication.key("x-goog-api-key", KeyPlacement.HEADER),
    )
    path = "/v1beta/models"
    _MODEL: ClassVar[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}")

    def request_path(self, model: str) -> str:
        """Return ``/v1beta/models/<model>:generateContent``.

        Raises
        ------
        InputError
            If the model id is not a plain Gemini model name.
        """
        if not self._MODEL.fullmatch(model):
            msg = f"{model!r} is not a Gemini model name"
            raise InputError(msg)
        return f"{self.path}/{model}:generateContent"

    def body(self, model: str, system: str, prompt: str) -> dict[str, object]:  # noqa: ARG002 - the model is in the path
        """Ask for one candidate."""
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
        }

    def reply(self, document: Mapping[str, Any]) -> Reply:
        """Read the first candidate's parts and ``usageMetadata``."""
        usage = _mapping(document.get("usageMetadata"), "usage metadata", self.id)
        candidates = document.get("candidates")
        first = candidates[0] if isinstance(candidates, list) and candidates else {}
        content = first.get("content") if isinstance(first, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        visible = _count(usage.get("candidatesTokenCount", 0), "output tokens", self.id)
        thoughts = _count(
            usage.get("thoughtsTokenCount", 0), "thinking tokens", self.id
        )
        return Reply(
            text=_texts(parts, None),
            input_tokens=_count(usage.get("promptTokenCount"), "input tokens", self.id),
            output_tokens=visible + thoughts,
            truncated=isinstance(first, dict)
            and first.get("finishReason") == "MAX_TOKENS",
        )


class OpenRouter(AiProvider):
    """OpenRouter's chat completions, which reach many makers' models."""

    info = _info(
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai",
        "https://openrouter.ai/terms",
        "openrouter.ai",
        Authentication.key("Authorization", KeyPlacement.HEADER, scheme="Bearer"),
    )
    path = "/api/v1/chat/completions"
    headers = (("HTTP-Referer", _REPOSITORY), ("X-Title", "pyeconomics"))

    def body(self, model: str, system: str, prompt: str) -> dict[str, object]:
        """Ask for one completion."""
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": MAX_OUTPUT_TOKENS,
        }

    def reply(self, document: Mapping[str, Any]) -> Reply:
        """Read the first choice's message and ``usage``."""
        usage = _mapping(document.get("usage"), "usage", self.id)
        choices = document.get("choices")
        first = choices[0] if isinstance(choices, list) and choices else {}
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        return Reply(
            text=content if isinstance(content, str) else "",
            input_tokens=_count(usage.get("prompt_tokens"), "input tokens", self.id),
            output_tokens=_count(
                usage.get("completion_tokens"), "output tokens", self.id
            ),
            truncated=isinstance(first, dict)
            and first.get("finish_reason") == "length",
        )


#: The declared providers, by id.
PROVIDERS: Final[Mapping[str, AiProvider]] = {
    provider.id: provider
    for provider in (Anthropic(), Gemini(), OpenAI(), OpenRouter())
}
