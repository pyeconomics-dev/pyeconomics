# tests/cli/test_cli_narrate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``models run ... --narrate`` (Phase 4 Step 11).

The narrative follows a table on standard output; with ``--format json``, an
export or ``--out`` it goes to standard error, so standard output stays the
canonical bytes. No narrative reaches an export, a bundle or the cache. A
narrated run binds under the user's ``llm_use`` policy, and a refused narrative
prints nothing but its problem. The providers answer from their cassettes.
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING, Any

import pytest
from ai_support import MARKER, black_scholes, replay
from cli_support import cli
from leakcheck import canary

import pyeconomics.ai.narrative as narrative_module
from pyeconomics.ai import NOT_ADVICE, PROVIDERS
from pyeconomics.cli import model_commands
from pyeconomics.surfaces.envelope import canonical_bytes
from pyeconomics.surfaces.invoke import invoke

if TYPE_CHECKING:
    from pathlib import Path

RUN = (
    "models",
    "run",
    "derivatives.black_scholes_merton",
    "--calculation",
    "price",
    "--spot",
    "42",
    "--strike",
    "40",
    "--years",
    "0.5",
    "--risk-free-rate",
    "0.1",
    "--volatility",
    "0.2",
)


@pytest.fixture
def narrating(isolated: Any, monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: ANN401
    """Keys in the chain, the narrative on, and the cassettes as the transport."""
    for provider in PROVIDERS:
        isolated.keyring.set_password("pyeconomics", provider, canary(provider).value)
    monkeypatch.setenv("PYECONOMICS_AI_ENABLED", "1")
    monkeypatch.setattr(narrative_module, "_transport", replay)
    return isolated


def _files_holding(directory: Path, text: str) -> list[str]:
    if not directory.exists():
        return []
    return sorted(
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and text.encode() in path.read_bytes()
    )


@pytest.mark.usefixtures("narrating")
def test_json_keeps_stdout_canonical_and_narrates_to_stderr() -> None:
    plain = cli(*RUN)
    narrated = cli(*RUN, "--narrate")
    assert narrated.code == 0, narrated.stderr
    assert narrated.stdout == plain.stdout
    assert narrated.stdout == canonical_bytes(black_scholes()) + b"\n"
    assert MARKER.encode() not in narrated.stdout
    assert narrated.stderr.startswith(f"{MARKER} openai:")
    assert NOT_ADVICE in narrated.stderr
    assert "Cost: $0.0035 (openai gpt-6.1-sol:" in narrated.stderr


@pytest.mark.usefixtures("narrating")
def test_a_table_is_followed_by_the_narrative_on_stdout() -> None:
    outcome = cli(*RUN, "--format", "table", "--narrate")
    assert outcome.code == 0, outcome.stderr
    text = outcome.text
    assert text.index("Outputs") < text.index("Narrative") < text.index(MARKER)
    assert NOT_ADVICE in text
    assert "Cost: $" in text
    assert outcome.stderr == ""


@pytest.mark.usefixtures("narrating")
def test_a_table_written_to_a_file_leaves_the_narrative_on_stderr(
    tmp_path: Path,
) -> None:
    path = tmp_path / "result.txt"
    outcome = cli(*RUN, "--format", "table", "--out", str(path), "--narrate")
    assert outcome.code == 0, outcome.stderr
    assert MARKER.encode() not in path.read_bytes()
    assert MARKER in outcome.stderr


@pytest.mark.usefixtures("narrating")
@pytest.mark.parametrize("export_format", ["csv", "xlsx", "parquet", "arrow"])
def test_no_narrative_reaches_an_export(tmp_path: Path, export_format: str) -> None:
    path = tmp_path / f"result.{export_format}"
    outcome = cli(*RUN, "--format", export_format, "--out", str(path), "--narrate")
    assert outcome.code == 0, outcome.stderr
    assert MARKER.encode() not in path.read_bytes()
    assert MARKER in outcome.stderr


@pytest.mark.usefixtures("narrating")
def test_no_narrative_reaches_a_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "run.zip"
    outcome = cli(*RUN, "--bundle", str(bundle), "--narrate")
    assert outcome.code == 0, outcome.stderr
    with zipfile.ZipFile(io.BytesIO(bundle.read_bytes())) as archive:
        holding = [
            name for name in archive.namelist() if MARKER.encode() in archive.read(name)
        ]
    assert holding == []
    assert MARKER in outcome.stderr


def test_no_narrative_reaches_the_cache(narrating: Any) -> None:  # noqa: ANN401
    outcome = cli(*RUN, "--narrate")
    assert outcome.code == 0, outcome.stderr
    assert _files_holding(narrating.cache_dir, MARKER) == []
    assert _files_holding(narrating.config_dir, MARKER) == []


def test_a_narrated_run_binds_under_the_users_policy(
    narrating: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del narrating
    seen: list[object] = []
    real = invoke

    def spy(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        seen.append(kwargs.get("llm_use"))
        return real(*args, **kwargs)

    monkeypatch.setattr(model_commands, "invoke", spy)
    assert cli(*RUN).code == 0
    assert cli(*RUN, "--narrate").code == 0
    assert [getattr(policy, "value", policy) for policy in seen] == [
        None,
        "allowed-only",
    ]


def test_a_disabled_narrative_prints_only_its_problem(
    isolated: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del isolated
    monkeypatch.setattr(narrative_module, "_transport", replay)
    outcome = cli(*RUN, "--narrate")
    assert outcome.code == 6
    assert outcome.stdout == b""
    assert "AI narrative is off" in outcome.stderr


@pytest.mark.usefixtures("narrating")
def test_hosted_mode_refuses_the_narrative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    outcome = cli(*RUN, "--narrate")
    assert outcome.code == 6
    assert outcome.stdout == b""
    assert "hosted mode does not write AI narratives" in outcome.stderr


@pytest.mark.usefixtures("narrating")
def test_a_missing_key_exits_7_naming_its_variable(isolated: Any) -> None:  # noqa: ANN401
    isolated.keyring.delete_password("pyeconomics", "openai")
    outcome = cli(*RUN, "--narrate")
    assert outcome.code == 7
    assert "OPENAI_API_KEY" in outcome.stderr
    assert outcome.stdout == b""


@pytest.mark.usefixtures("narrating")
def test_batch_cannot_narrate() -> None:
    outcome = cli(
        "models",
        "run",
        "derivatives.black_scholes_merton",
        "--batch",
        "-",
        "--narrate",
        stdin=b'{"spot": 42}\n',
    )
    assert outcome.code == 2
    assert "--narrate" in outcome.stderr


def test_narrate_is_a_reserved_option() -> None:
    assert "--narrate" in model_commands.RESERVED_OPTIONS
