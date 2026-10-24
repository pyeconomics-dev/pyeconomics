# tests/cli/test_cli_models.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics models`` and ``registry export`` (Phase 4 Step 4).

``models run`` must print the bytes ``Result.to_json()`` gives, plus one
newline, however its inputs arrive: generated options, a file, standard input,
or a file with options overriding it. Its options are generated from the
model's input schema when the command line names the model.
"""

from __future__ import annotations

import json
import typing
from typing import TYPE_CHECKING, Any

import pytest
import toy_models as toys
from cli_support import cli

import pyeconomics
from pyeconomics import registry
from pyeconomics.cli import model_commands
from pyeconomics.core import RegistryError, VintagePolicy
from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces import listing

if TYPE_CHECKING:
    from pathlib import Path

TVM = "foundations.time_value"
PRESENT = {
    "calculation": "present_value",
    "rate": 0.05,
    "periods": 10,
    "future_value": 100,
}
OPTIONS = (
    "--calculation",
    "present_value",
    "--rate",
    "0.05",
    "--periods",
    "10",
    "--future-value",
    "100",
)


def expected(model_id: str, inputs: dict[str, Any]) -> bytes:
    return pyeconomics.run(model_id, inputs).to_json().encode("utf-8") + b"\n"


# --- list, search, describe --------------------------------------------------------


def test_models_list_prints_every_entry_as_json_or_a_table() -> None:
    as_json = cli("models", "list", "--format", "json")
    assert as_json.code == 0
    assert json.loads(as_json.stdout) == listing.list_models()
    assert as_json.stdout == canonical_json(listing.list_models()) + b"\n"
    table = cli("models", "list")
    assert table.code == 0
    assert TVM in table.text
    assert f"{len(registry.ids())} models." in table.text


def test_models_list_filters_by_domain() -> None:
    found = json.loads(
        cli("models", "list", "--domain", "macro", "--format", "json").stdout
    )
    assert found
    assert {entry["domain"] for entry in found} == {"macro"}
    unknown = cli("models", "list", "--domain", "nowhere")
    assert unknown.code == 3
    assert "the domains are" in unknown.stderr


def test_models_search_ranks_matches() -> None:
    found = cli(
        "models", "search", "present value annuity", "--format", "json", "--limit", "3"
    )
    assert found.code == 0
    assert json.loads(found.stdout) == listing.search_models("present value annuity", 3)
    table = cli("models", "search", "bond duration", "--limit", "2")
    assert "fixed_income.duration" in table.text
    assert cli("models", "search", "bond", "--limit", "0").code == 3


def test_models_describe_prints_the_card_or_the_description() -> None:
    card = cli("models", "describe", TVM)
    assert card.code == 0
    assert card.text == str(registry.describe(TVM)["card"]).rstrip("\n") + "\n"
    as_json = cli("models", "describe", TVM, "--format", "json")
    assert as_json.stdout == canonical_json(registry.describe(TVM)) + b"\n"
    assert cli("models", "describe", "foundations.nothing").code == 5


# --- run -------------------------------------------------------------------------


def test_a_run_prints_the_canonical_bytes_and_one_newline() -> None:
    outcome = cli("models", "run", TVM, *OPTIONS)
    assert (outcome.code, outcome.stderr) == (0, "")
    assert outcome.stdout == expected(TVM, PRESENT)


def test_inputs_come_from_a_file_or_standard_input_and_options_override(
    tmp_path: Path,
) -> None:
    path = tmp_path / "inputs.json"
    path.write_bytes(json.dumps(PRESENT).encode("utf-8"))
    assert cli("models", "run", TVM, "--inputs", str(path)).stdout == expected(
        TVM, PRESENT
    )
    piped = cli(
        "models", "run", TVM, "--inputs", "-", stdin=json.dumps(PRESENT).encode()
    )
    assert piped.stdout == expected(TVM, PRESENT)
    overridden = cli("models", "run", TVM, "--inputs", str(path), "--rate", "0.06")
    assert overridden.stdout == expected(TVM, {**PRESENT, "rate": 0.06})


def test_the_files_calculation_types_the_options() -> None:
    document = {"calculation": "present_value", "periods": 10, "future_value": 100}
    outcome = cli(
        "models",
        "run",
        TVM,
        "--inputs",
        "-",
        "--rate",
        "0.05",
        stdin=json.dumps(document).encode(),
    )
    assert outcome.stdout == expected(TVM, PRESENT)


def test_out_writes_the_same_bytes_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    outcome = cli("models", "run", TVM, *OPTIONS, "--out", str(target))
    assert (outcome.code, outcome.stdout) == (0, b"")
    assert target.read_bytes() == expected(TVM, PRESENT)
    listed = tmp_path / "models.txt"
    assert cli("models", "list", "--out", str(listed)).code == 0
    assert TVM in listed.read_text(encoding="utf-8")


def test_a_table_shows_inputs_outputs_units_and_the_hash() -> None:
    outcome = cli("models", "run", TVM, *OPTIONS, "--format", "table")
    assert outcome.code == 0
    result = pyeconomics.run(TVM, PRESENT)
    lines = outcome.text.splitlines()
    assert lines[0] == "Time value of money (foundations.time_value, version 2)"
    assert {"Inputs", "Outputs"} <= set(lines)
    assert any(
        line.split()[:1] == ["present_value"] and "money" in line for line in lines
    )
    assert lines[-1] == f"result_sha256 {result.manifest.result_sha256}"


def test_warnings_appear_in_the_table() -> None:
    outcome = cli(
        "models",
        "run",
        TVM,
        "--calculation",
        "irr",
        "--cash-flows",
        "[100, 50, 60]",
        "--format",
        "table",
    )
    assert "Warnings" in outcome.text.splitlines()
    assert "no_sign_change" in outcome.text


def test_the_run_help_lists_the_generated_and_the_run_options() -> None:
    outcome = cli("models", "run", TVM, "--help")
    assert outcome.code == 0
    for text in (
        "--present-value",
        "--cash-flows",
        "Unit: money",
        "--inputs",
        "--as-of",
        "--concept",
        "--param",
    ):
        assert text in outcome.text
    generic = cli("models", "run", "--help")
    assert generic.code == 0
    assert "MODEL_ID" in generic.text


def test_a_run_needs_the_model_named_first() -> None:
    assert cli("models", "run").code == 2
    late = cli("models", "run", "--", TVM)
    assert late.code == 2
    assert late.stderr.startswith(
        "usage-error: name the model straight after models run"
    )
    unknown = cli("models", "run", TVM, "--no-such-option", "1")
    assert unknown.code == 2
    assert unknown.stderr.startswith("usage-error:")


def test_an_unknown_model_is_not_found_with_close_matches() -> None:
    outcome = cli("models", "run", "foundations.time_valu")
    assert outcome.code == 5
    assert outcome.stderr.startswith("model-not-found:")
    assert TVM in outcome.stderr


@pytest.mark.filterwarnings("always::pyeconomics.core.PyeconomicsDeprecationWarning")
def test_an_alias_runs_its_model_and_warns_on_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_registry._CACHE, "registry", toys.toy_registry())  # noqa: SLF001
    inputs = {
        "calculation": "present_value",
        "future_value": 100,
        "rate": 0.05,
        "years": 1,
    }
    outcome = cli(
        "models",
        "run",
        "foundations.toy_tvm",
        "--inputs",
        "-",
        stdin=json.dumps(inputs).encode(),
    )
    assert outcome.code == 0
    assert json.loads(outcome.stdout)["model_id"] == "foundations.toy_time_value"
    assert outcome.stderr.startswith("PyeconomicsDeprecationWarning: ")


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--param", "meeting"), "--param takes NAME=VALUE"),
        (("--concept", "a=b", "--concept", "a=c"), "--concept names a twice"),
        (("--inputs", "missing-file.json"), "cannot be read (FileNotFoundError)"),
        (("--rate", "true"), "takes a number, not a boolean"),
        (("--as-of", "2024-13-01"), "as_of"),
    ],
    ids=["no-equals", "repeated", "missing-file", "boolean-rate", "bad-date"],
)
def test_invalid_options_are_invalid_input(
    arguments: tuple[str, ...], message: str
) -> None:
    outcome = cli("models", "run", TVM, "--calculation", "present_value", *arguments)
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: ")
    assert message in outcome.stderr
    assert "missing-file.json" not in outcome.stderr


def test_inputs_above_the_limit_are_refused_before_parsing() -> None:
    outcome = cli(
        "models", "run", TVM, "--inputs", "-", stdin=b" " * (16 * 1024 * 1024 + 1)
    )
    assert outcome.code == 3
    assert outcome.stderr.startswith("input-too-large: ")


def test_a_field_that_takes_a_run_options_name_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = {"properties": {"format": {"type": "string", "description": "A clash"}}}
    monkeypatch.setattr(model_commands, "input_schema", lambda _model: schema)
    model = registry.get(TVM)
    with pytest.raises(RegistryError, match="takes the command line's option --format"):
        model_commands.model_command(model, TVM)


def test_every_registered_model_builds_its_options() -> None:
    for model in registry.models():
        command = model_commands.model_command(model, model.id)
        assert command.__doc__
        assert command.__doc__.startswith(model.spec.title)


def test_the_vintage_choices_are_the_policies() -> None:
    assert typing.get_args(model_commands.Vintage) == tuple(
        p.value for p in VintagePolicy
    )


# --- registry export ---------------------------------------------------------------


def test_registry_export_writes_registry_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pyeconomics.surfaces import registry_export  # noqa: PLC0415

    calls: list[tuple[Path, bool]] = []
    monkeypatch.setattr(
        registry_export,
        "write_registry",
        lambda path, *, figures: calls.append((path, figures)),
    )
    target = tmp_path / "site" / "data"
    outcome = cli("registry", "export", "--out", str(target), "--no-figures")
    assert outcome.code == 0
    assert calls == [(target / "registry.json", False)]
    assert outcome.text == f"{target / 'registry.json'}\n"
    assert target.is_dir()
    cli("registry", "export", "--out", str(target))
    assert calls[-1] == (target / "registry.json", True)


def test_registry_export_failures_reach_the_error_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pyeconomics.surfaces import registry_export  # noqa: PLC0415

    def fail(_path: Path, *, figures: bool) -> None:
        msg = f"toy.model: its first example failed (figures={figures})"
        raise RegistryError(msg, problems=())

    monkeypatch.setattr(registry_export, "write_registry", fail)
    outcome = cli("registry", "export", "--out", str(tmp_path))
    assert outcome.code == 1
    assert outcome.stderr.startswith("registry-error: ")
    blocked = tmp_path / "a-file"
    blocked.write_bytes(b"")
    refused = cli("registry", "export", "--out", str(blocked))
    assert refused.code == 3
    assert "cannot be created" in refused.stderr
    assert "a-file" not in refused.stderr
    assert cli("registry", "export").code == 2
