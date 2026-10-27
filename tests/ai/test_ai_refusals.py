# tests/ai/test_ai_refusals.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every refusal of the narrative happens before any request (ADR-0012 decision 17).

The narrative is off by default, refuses hosted mode outright, refuses offline
mode, withholds a result whose data's terms keep it from a language model
(``forbidden``, or ``unclear`` without the user's out-of-band opt-in) and names
a missing key's variable without any value. Each refusal is an error-table row,
and a scripted transport proves no request was sent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ai_support import (
    Scripted,
    answer,
    enable,
    narrated,
    ok,
    replay,
    with_records,
)
from leakcheck import LeakCheck, canary

from pyeconomics.ai import (
    PROVIDERS,
    NarrativeDisabledError,
    NarrativeHostedError,
    narrate,
)
from pyeconomics.core.provenance import LlmUse
from pyeconomics.data import (
    CredentialError,
    LicenceError,
    LlmUseError,
    OfflineError,
    configure,
)
from pyeconomics.surfaces.problems import problem_for

if TYPE_CHECKING:
    from config_isolation import Home, Isolation

pytestmark = pytest.mark.usefixtures("isolated")


@pytest.fixture
def keyed(isolated: Isolation) -> None:
    for provider in PROVIDERS:
        isolated.keyring.set_password("pyeconomics", provider, canary(provider).value)


def test_the_narrative_is_off_by_default() -> None:
    transport = Scripted()
    with pytest.raises(NarrativeDisabledError) as caught:
        narrate(narrated(), transport=transport)
    assert transport.sent == []
    problem = problem_for(caught.value)
    assert (problem.slug, problem.status, problem.exit_code) == (
        "narrative-disabled",
        403,
        6,
    )
    assert "PYECONOMICS_AI_ENABLED" in problem.detail


@pytest.mark.parametrize("variable", ["PYECONOMICS_AI_ENABLED"])
def test_the_environment_turns_it_on(
    variable: str, monkeypatch: pytest.MonkeyPatch, keyed: None
) -> None:
    del keyed
    monkeypatch.setenv(variable, "1")
    narrative = narrate(narrated(), transport=Scripted(ok(answer("openai"))))
    assert narrative.provider == "openai"


def test_the_settings_file_turns_it_on(home: Home, keyed: None) -> None:
    del keyed
    home.write_config('ai_enabled = true\nai_provider = "gemini"\n')
    narrative = narrate(narrated(), transport=Scripted(ok(answer("gemini"))))
    assert narrative.provider == "gemini"


def test_hosted_mode_refuses_before_anything_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Not even enabled: hosted mode is refused first, whatever the settings.
    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    transport = Scripted()
    with pytest.raises(NarrativeHostedError) as caught:
        narrate(narrated(), transport=transport)
    assert transport.sent == []
    problem = problem_for(caught.value)
    assert (problem.slug, problem.status, problem.exit_code) == (
        "narrative-not-hosted",
        403,
        6,
    )


def test_hosted_mode_refuses_even_when_enabled() -> None:
    enable()
    configure(mode="hosted")
    transport = Scripted()
    with pytest.raises(NarrativeHostedError):
        narrate(narrated(), transport=transport)
    assert transport.sent == []


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_the_transport_would_refuse_hosted_mode_too(provider: str) -> None:
    """A second line: every AI provider is declared library-only."""
    from ai_support import narrative_request  # noqa: PLC0415

    configure(mode="hosted")
    with pytest.raises(LicenceError):
        replay().send(PROVIDERS[provider].info, narrative_request(provider))


def test_offline_mode_refuses_before_any_request(keyed: None) -> None:
    del keyed
    enable()
    configure(offline=True)
    transport = Scripted()
    with pytest.raises(OfflineError, match="a narrative needs openai") as caught:
        narrate(narrated(), transport=transport)
    assert transport.sent == []
    assert problem_for(caught.value).exit_code == 7


def test_forbidden_data_never_reaches_a_provider(keyed: None) -> None:
    del keyed
    enable()
    transport = Scripted()
    result = with_records(narrated(), LlmUse.ALLOWED, LlmUse.FORBIDDEN)
    with pytest.raises(LlmUseError) as caught:
        narrate(result, transport=transport)
    assert transport.sent == []
    assert caught.value.provider == "toy_forbidden"
    assert "the result carries data from toy_forbidden" in str(caught.value)
    assert problem_for(caught.value).slug == "llm-use-forbidden"


def test_forbidden_data_is_refused_even_with_the_opt_in(
    monkeypatch: pytest.MonkeyPatch, keyed: None
) -> None:
    del keyed
    monkeypatch.setenv("PYECONOMICS_ALLOW_UNCLEAR_LLM_USE", "1")
    enable()
    transport = Scripted()
    with pytest.raises(LlmUseError):
        narrate(with_records(narrated(), LlmUse.FORBIDDEN), transport=transport)
    assert transport.sent == []


def test_unclear_data_is_refused_without_the_opt_in(keyed: None) -> None:
    del keyed
    enable()
    transport = Scripted()
    with pytest.raises(LlmUseError, match="allowed-only policy"):
        narrate(with_records(narrated(), LlmUse.UNCLEAR), transport=transport)
    assert transport.sent == []


def test_unclear_data_is_narrated_with_the_out_of_band_opt_in(
    monkeypatch: pytest.MonkeyPatch, keyed: None
) -> None:

    del keyed
    monkeypatch.setenv("PYECONOMICS_ALLOW_UNCLEAR_LLM_USE", "1")
    enable()
    transport = Scripted(ok(answer("openai")))
    result = with_records(narrated(), LlmUse.UNCLEAR, LlmUse.ALLOWED)
    narrative = narrate(result, transport=transport)
    assert narrative.text
    assert len(transport.sent) == 1


def test_allowed_data_is_narrated(keyed: None) -> None:
    del keyed
    enable()
    transport = Scripted(ok(answer("openai")))
    narrate(with_records(narrated(), LlmUse.ALLOWED), transport=transport)
    assert len(transport.sent) == 1


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_a_missing_key_names_its_variable_and_no_value(provider: str) -> None:
    enable()
    planted = canary(provider)
    check = LeakCheck(planted)
    transport = Scripted()
    with pytest.raises(CredentialError) as caught:
        narrate(narrated(), provider=provider, transport=transport)
    assert transport.sent == []
    variable = PROVIDERS[provider].info.key_variable
    assert variable == f"{provider.upper()}_API_KEY"
    assert variable in str(caught.value)
    check.exception(caught.value)
    check.add("problem", problem_for(caught.value).to_json())
    check.assert_clean()
    assert problem_for(caught.value).exit_code == 7
