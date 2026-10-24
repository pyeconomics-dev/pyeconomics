# tests/cli/test_cli_console_script.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The installed ``pyeconomics`` console script, run as a process (Step 4).

Every cell of the test matrix runs the script its environment installed: its
version, one model run whose bytes must equal ``Result.to_json()`` plus one
newline, and a card holding non-ASCII text, which must arrive as UTF-8 whatever
the platform's code page (the process runs with no UTF-8 mode or I/O encoding
set). A last test bounds the time ``pyeconomics --version`` takes; the
structural half of that bound (``--version`` discovers no model and loads no
data module) is in tests/surfaces/test_surface_layering.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404: runs the installed console script with fixed arguments
import sys
import time
from pathlib import Path

import pyeconomics

#: The longest ``pyeconomics --version`` may take, in seconds, on any CI cell:
#: the import of pyeconomics (pandas, NumPy, pydantic) dominates it.
VERSION_SECONDS = 15.0


def script() -> str:
    """The console script installed beside this interpreter; it must exist."""
    found = shutil.which("pyeconomics", path=str(Path(sys.executable).parent))
    assert found is not None, "the pyeconomics console script is not installed"
    return found


def run(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if name not in {"PYTHONUTF8", "PYTHONIOENCODING"}
    }
    return subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [script(), *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
        timeout=300,
    )


def test_the_console_script_reports_the_installed_version(tmp_path: Path) -> None:
    done = run("--version", cwd=tmp_path)
    assert (done.returncode, done.stderr) == (0, b"")
    assert done.stdout == f"pyeconomics {pyeconomics.__version__}\n".encode()


def test_the_console_script_runs_a_model_to_its_canonical_bytes(tmp_path: Path) -> None:
    done = run(
        "models",
        "run",
        "foundations.time_value",
        "--calculation",
        "present_value",
        "--rate",
        "0.05",
        "--periods",
        "10",
        "--future-value",
        "100",
        cwd=tmp_path,
    )
    assert (done.returncode, done.stderr) == (0, b"")
    inputs = {
        "calculation": "present_value",
        "rate": 0.05,
        "periods": 10,
        "future_value": 100,
    }
    expected = pyeconomics.run("foundations.time_value", inputs).to_json()
    assert done.stdout == expected.encode("utf-8") + b"\n"


def test_the_console_script_writes_utf8_on_every_platform(tmp_path: Path) -> None:
    done = run("models", "describe", "performance.risk_adjusted", cwd=tmp_path)
    assert done.returncode == 0
    text = done.stdout.decode("utf-8")
    assert "²" in text
    assert "\r\n" not in text
    failed = run("models", "run", "foundations.nothing", cwd=tmp_path)
    assert failed.returncode == 5
    assert failed.stderr.decode("utf-8").startswith("model-not-found: ")


def test_version_stays_within_its_time_bound(tmp_path: Path) -> None:
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        done = run("--version", cwd=tmp_path)
        timings.append(time.perf_counter() - start)
        assert done.returncode == 0
    assert min(timings) < VERSION_SECONDS
