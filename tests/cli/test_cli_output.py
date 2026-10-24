# tests/cli/test_cli_output.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""How the command line writes: UTF-8, tables, ``--debug`` and the log (Step 4).

Output is UTF-8 bytes whatever the platform's code page; a table is drawn by
rich on a terminal and laid out as plain text anywhere else; ``--debug`` adds a
traceback whose files are named by their place in their package and whose lines
are scrubbed; warnings become one line on standard error; and a run leaves the
logging configuration as it found it.
"""

from __future__ import annotations

import io
import logging
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from cli_support import FakeTerminal, cli
from leakcheck import LeakCheck, canary

from pyeconomics.cli import app as cli_app
from pyeconomics.cli import build_app
from pyeconomics.cli.output import Grid, Streams, Utf8Text, cell, render_plain, show
from pyeconomics.core import DomainError

if TYPE_CHECKING:
    import pytest

TVM = "foundations.time_value"
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


def test_utf8_text_writes_utf8_and_is_no_terminal() -> None:
    binary = io.BytesIO()
    text = Utf8Text(binary)
    assert text.write("± 5 €") == 5
    text.flush()
    assert binary.getvalue() == "± 5 €".encode()
    assert (text.encoding, text.isatty()) == ("utf-8", False)
    text.write("\udc80")
    assert binary.getvalue().endswith(b"?")


def test_cells_spell_values_as_json_does() -> None:
    values = [None, "text", True, 0.1, [1, 2.5]]
    assert [cell(value) for value in values] == [
        "",
        "text",
        "true",
        "0.1",
        "[1,2.5]",
    ]


def test_plain_text_is_aligned_and_has_no_box_or_escape() -> None:
    grid = Grid("Values", ("Name", "Value"), (("rate", "0.05"), ("growth ±", "1")))
    text = render_plain([grid, "Source: someone."])
    assert text.splitlines() == [
        "Values",
        "Name      Value",
        "rate      0.05",
        "growth ±  1",
        "",
        "Source: someone.",
    ]
    assert "\x1b" not in text
    assert "╭" not in text


def test_a_terminal_gets_a_rich_table_and_a_pipe_gets_utf8_bytes() -> None:
    terminal = FakeTerminal()
    outcome = cli(
        "models", "run", TVM, *OPTIONS, "--format", "table", terminal=terminal
    )
    assert (outcome.code, outcome.stdout) == (0, b"")
    # A rounded box, or a square one where rich takes the console for a legacy one.
    assert "─" in terminal.getvalue()
    assert "present_value" in terminal.getvalue()
    piped = cli("models", "run", TVM, *OPTIONS, "--format", "table")
    assert "─" not in piped.text
    assert piped.stdout.decode("utf-8") == piped.text


def test_out_on_a_terminal_still_writes_plain_text(tmp_path: Path) -> None:
    terminal = FakeTerminal()
    target = tmp_path / "table.txt"
    outcome = cli("models", "list", "--out", str(target), terminal=terminal)
    assert outcome.code == 0
    assert terminal.getvalue() == ""
    assert "╭" not in target.read_text(encoding="utf-8")


def test_non_ascii_text_is_utf8_bytes() -> None:
    out, err = io.BytesIO(), io.BytesIO()
    streams = Streams(stdin=io.BytesIO(), stdout=out, stderr=err)
    show(streams, [Grid(None, ("Unit",), (("± 1 € — ≥",),))], None)
    assert "± 1 € — ≥" in out.getvalue().decode("utf-8")
    streams.error("détail")
    assert err.getvalue() == "détail\n".encode()


def test_the_system_streams_are_the_process_buffers() -> None:
    streams = Streams.system()
    assert streams.stdout is sys.stdout.buffer
    assert streams.stderr is sys.stderr.buffer
    assert streams.stdin is sys.stdin.buffer


def test_help_and_completion_on_a_terminal_and_a_pipe() -> None:
    terminal = FakeTerminal()
    assert cli("--help", terminal=terminal).code == 0
    assert "models" in terminal.getvalue()
    piped = cli("models", "--help")
    assert "run" in piped.text
    for shell in ("bash", "zsh", "fish", "powershell"):
        script = cli("completion", shell)
        assert script.code == 0
        assert "pyeconomics" in script.text
    assert cli("completion", "tcsh").code == 2


def test_build_app_builds_the_tree() -> None:
    app = build_app(
        Streams(stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())
    )
    assert {"models", "data", "keys", "cache", "registry", "completion"} <= set(app)


def test_main_runs_the_process_arguments(
    monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    from pyeconomics.cli import main  # noqa: PLC0415

    monkeypatch.setattr(sys, "argv", ["pyeconomics", "--version"])
    assert main() == 0
    assert capsysbinary.readouterr().out.startswith(b"pyeconomics 1.0.0")


# --- --debug, warnings and the log --------------------------------------------


def test_debug_adds_a_scrubbed_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    key = canary("fred")

    def fail(*_args: object, **_kwargs: object) -> None:
        msg = f"failed with {key.value} reading C:\\Users\\someone\\x.toml"
        raise DomainError(msg)

    monkeypatch.setattr("pyeconomics.cli.model_commands.invoke", fail)
    plain = cli("models", "run", TVM, *OPTIONS)
    assert plain.code == 4
    assert plain.stderr.splitlines() == [plain.stderr.splitlines()[0]]
    debug = cli("--debug", "models", "run", TVM, *OPTIONS)
    assert debug.code == 4
    lines = debug.stderr.splitlines()
    assert "Traceback (most recent call last):" in lines
    assert any('File "pyeconomics/cli/model_commands.py"' in line for line in lines)
    assert any(
        line.startswith("pyeconomics.core.errors.DomainError: failed with")
        for line in lines
    )
    check = LeakCheck(key)
    check.add("stderr", debug.stderr)
    check.assert_clean()
    assert "someone" not in debug.stderr


def test_a_traceback_names_files_by_their_package(tmp_path: Path) -> None:
    name = cli_app._display_name  # noqa: SLF001
    root = Path(cli_app.__file__).resolve().parents[1]
    assert name(str(root / "cli" / "app.py")) == "pyeconomics/cli/app.py"
    site = tmp_path / "venv" / "lib" / "site-packages" / "cyclopts" / "core.py"
    assert name(str(site)) == "cyclopts/core.py"
    stdlib = tmp_path / "Python" / "Lib" / "json" / "decoder.py"
    assert name(str(stdlib)) == "json/decoder.py"
    assert name(str(tmp_path / "elsewhere" / "tool.py")) == "tool.py"
    assert name("<string>") == "<string>"


def _fail_inside() -> None:
    try:
        int("not a number")
    except ValueError as inner:
        msg = "outer"
        raise DomainError(msg) from inner


def _chained() -> DomainError:
    """Return a DomainError raised from a ValueError, as a failure would chain it."""
    try:
        _fail_inside()
    except DomainError as error:
        return error
    raise AssertionError  # pragma: no cover - _fail_inside always raises


def test_a_chained_errors_frames_are_renamed_too() -> None:
    lines = cli_app.debug_traceback(_chained())
    files = [line for line in lines if line.lstrip().startswith("File ")]
    assert len(files) == 3
    assert all('"tests/cli/test_cli_output.py"' not in line for line in files)
    assert all("test_cli_output.py" in line for line in files)
    assert any("direct cause" in line for line in lines)


def test_warnings_become_one_scrubbed_line_on_stderr() -> None:
    out, err = io.BytesIO(), io.BytesIO()
    streams = Streams(stdin=io.BytesIO(), stdout=out, stderr=err)
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        with cli_app._warnings(streams):  # noqa: SLF001
            warnings.warn(
                "see https://api.example.org/v1?id=1 now", UserWarning, stacklevel=1
            )
    assert err.getvalue() == b"UserWarning: see <url> now\n"


def test_a_run_restores_the_logging_configuration() -> None:
    logger = logging.getLogger("pyeconomics")
    handlers, level = list(logger.handlers), logger.level
    debug = cli("--debug", "models", "run", "foundations.nothing")
    assert debug.code == 5
    assert "INFO pyeconomics.surfaces: model-not-found (404" in debug.stderr
    assert cli("models", "run", "foundations.nothing").stderr.startswith(
        "model-not-found:"
    )
    assert (logger.handlers, logger.level) == (handlers, level)


def test_without_debug_a_failure_logs_through_report_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="pyeconomics"):
        outcome = cli("models", "run", "foundations.nothing")
    assert outcome.code == 5
    assert [record.name for record in caplog.records] == ["pyeconomics.surfaces"]
    assert (
        caplog.records[0]
        .getMessage()
        .startswith("model-not-found (404, ModelNotFoundError)")
    )
