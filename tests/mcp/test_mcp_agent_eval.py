# tests/mcp/test_mcp_agent_eval.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the live agent evaluation tells its agent behind a local gateway.

scripts/mcp_agent_eval.py gives a real agent the MCP server's tools and nothing
else. On a machine whose model requests pass a de-identifying gateway on
loopback, the agent sees a long number in a tool's answer as a placeholder and
took it for missing data (2026-11-17). There, and only there, the script adds
one sentence about placeholders, and the page says that it did. No test here
starts an agent.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "mcp_agent_eval.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mcp_agent_eval_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


agent_eval = load_script()


def record(*, gateway: bool) -> dict[str, Any]:
    return {
        "date": "2026-11-17",
        "agent": "Claude Code 0.0.0, headless (claude -p)",
        "gateway": gateway,
        "model": "a-model",
        "server_version": "1.0.0",
        "commit": "0000000",
        "tools": 21,
        "tools_list_bytes": 1,
        "baseline_tokens": 1,
        "first_request_tokens": 2,
        "runs": [],
    }


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        ("http://127.0.0.1:47821", True),
        ("http://127.0.0.1:47821/openrouter", True),
        ("http://localhost:8080", True),
        ("https://api.anthropic.com", False),
        ("https://127.0.0.1.example.com", False),
        ("", False),
    ],
)
def test_a_gateway_is_a_base_address_on_loopback(
    monkeypatch: pytest.MonkeyPatch, *, base: str, expected: bool
) -> None:
    monkeypatch.setenv("ANTHROPIC_BASE_URL", base)
    assert agent_eval.gateway() is expected


def test_no_base_address_is_no_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    assert agent_eval.gateway() is False


def test_the_agent_is_told_of_placeholders_only_behind_a_gateway(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = tmp_path / "mcp.json"
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    plain = agent_eval.agent_command("claude", config, "sonnet")
    assert "--append-system-prompt" not in plain
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:47821")
    behind = agent_eval.agent_command("claude", config, "sonnet")
    assert behind[: len(plain)] == plain
    assert behind[len(plain) :] == ["--append-system-prompt", agent_eval.GATEWAY_NOTE]


def test_the_note_says_nothing_of_the_server_or_its_tools() -> None:
    from pyeconomics import registry  # noqa: PLC0415
    from pyeconomics.mcp.tools import tool_name  # noqa: PLC0415

    note = agent_eval.GATEWAY_NOTE.lower()
    assert "pyeconomics" not in note
    for model in registry.models():
        assert model.spec.id not in note
        assert tool_name(model.spec.id) not in note
    for word in ("run_model", "search_models", "describe_model", "get_series"):
        assert word not in note
    # It tells the agent what a placeholder is and where to write it.
    assert "[[number_abcde]]" in note
    assert "answer line" in note


def test_the_page_says_when_a_gateway_stood_between() -> None:
    behind = agent_eval.markdown(record(gateway=True))
    plain = agent_eval.markdown(record(gateway=False))
    assert agent_eval.GATEWAY_LINE in behind.split("\n")
    assert "Gateway" not in plain
    # A record written before the field existed reads as no gateway.
    old = record(gateway=False)
    del old["gateway"]
    assert agent_eval.markdown(old) == plain
