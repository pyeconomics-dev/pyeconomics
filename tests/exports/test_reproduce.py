# tests/exports/test_reproduce.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A bundle's ``reproduce.py`` reruns its result (ADR-0012 decision 7; Step 5).

The script runs as a user runs it, a separate process from the bundle's
directory, for its exit codes: 0 with identical bytes, 1 when the result
differs, 2 when pyeconomics is missing or another version is installed. Bound
runs go through the script's ``main`` in this process, over the toy bound models
and scripted providers, for the revised-data rule and ``--refetch``. The CI
``package`` job runs it once more in a fresh environment built from the wheel.
"""

from __future__ import annotations

import json
import runpy
import subprocess  # nosec B404: runs this interpreter on a script the test wrote
import sys
import zipfile
from typing import TYPE_CHECKING, Any

import pytest
from cli_support import install_world

from pyeconomics import run
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import cache
from pyeconomics.exports import write_bundle
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from pyeconomics.core.results import Result

PV = {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}
UNEMPLOYMENT = "macro.toy_unemployment"


def unpack(result: Result[Any, Any], directory: Path, request: Any = None) -> Path:  # noqa: ANN401
    """Write a result's bundle and extract it; return the directory."""
    path = directory / "bundle.zip"
    write_bundle(result, path, request)
    target = directory / "bundle"
    with zipfile.ZipFile(path) as archive:
        archive.extractall(target)
    return target


def rerun(
    bundle: Path, *arguments: str, isolated: bool = False
) -> subprocess.CompletedProcess[str]:
    flags = ["-I", "-S"] if isolated else []
    return subprocess.run(  # noqa: S603 # nosec B603: this interpreter, fixed arguments
        [sys.executable, *flags, str(bundle / "reproduce.py"), *arguments],
        cwd=bundle.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def edit_result(bundle: Path, change: Callable[[dict[str, Any]], None]) -> None:
    document = json.loads((bundle / "result.json").read_bytes())
    change(document)
    (bundle / "result.json").write_bytes(canonical_json(document))


def test_a_rerun_agrees_and_gives_identical_bytes(tmp_path: Path) -> None:
    result = run("foundations.time_value", PV)
    bundle = unpack(result, tmp_path)
    done = rerun(bundle, "--out", str(tmp_path / "rerun.json"))
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"result_sha256 agrees: {result.manifest.result_sha256}" in done.stdout
    assert "identical to result.json" in done.stdout
    assert (tmp_path / "rerun.json").read_bytes() == (
        bundle / "result.json"
    ).read_bytes()


def test_a_rerun_that_differs_exits_1_and_names_both_hashes(tmp_path: Path) -> None:
    bundle = unpack(run("foundations.time_value", PV), tmp_path)

    def forge(document: dict[str, Any]) -> None:
        document["manifest"]["result_sha256"] = "0" * 64

    edit_result(bundle, forge)
    done = rerun(bundle)
    assert done.returncode == 1
    assert f"result_sha256 differs: recorded {'0' * 64}, rerun " in done.stdout


def test_another_installed_version_exits_2_with_the_install_command(
    tmp_path: Path,
) -> None:
    bundle = unpack(run("foundations.time_value", PV), tmp_path)

    def older(document: dict[str, Any]) -> None:
        document["manifest"]["package_version"] = "0.0.1"

    edit_result(bundle, older)
    done = rerun(bundle)
    assert done.returncode == 2
    assert "made with pyeconomics 0.0.1" in done.stdout
    assert "pip install -r requirements.txt" in done.stdout


def test_without_pyeconomics_it_exits_2_with_the_install_command(
    tmp_path: Path,
) -> None:
    bundle = unpack(run("foundations.time_value", PV), tmp_path)
    done = rerun(bundle, isolated=True)  # no site-packages: the stdlib alone
    assert done.returncode == 2, done.stderr
    assert "pyeconomics is not installed" in done.stdout


def test_a_refetch_of_a_bundle_that_bound_nothing_exits_2(tmp_path: Path) -> None:
    bundle = unpack(run("foundations.time_value", PV), tmp_path)
    done = rerun(bundle, "--refetch")
    assert done.returncode == 2
    assert "result_sha256 agrees" in done.stdout
    assert "nothing to refetch" in done.stdout


# --- bound runs, in this process ---------------------------------------------------


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    install_world(monkeypatch)
    with cache.bypass():
        yield


def script_main(bundle: Path) -> Callable[[list[str]], int]:
    namespace = runpy.run_path(str(bundle / "reproduce.py"), run_name="bundle_script")
    main: Callable[[list[str]], int] = namespace["main"]
    return main


@pytest.mark.usefixtures("world")
def test_a_bound_run_reruns_and_refetches_field_by_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = BindRequest(as_of="2024-03-20")
    result = invoke(UNEMPLOYMENT, {"weight": 2.0}, bind=request)
    main = script_main(unpack(result, tmp_path, request))
    assert main(["--refetch"]) == 0
    out = capsys.readouterr().out
    assert "result_sha256 agrees" in out
    assert "differ from result.json in: manifest.data_sources" in out
    (record,) = result.manifest.data_sources
    assert (
        f"unemployment: agrees; {record.provider}:{record.series_id}, "
        f"vintage {record.vintage}"
    ) in out


@pytest.mark.usefixtures("world")
def test_revised_data_is_restored_for_the_hash_and_labelled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = BindRequest(profile="revised")
    result = invoke(UNEMPLOYMENT, {}, bind=request)
    assert result.warnings[-1].code == "revised_data"
    main = script_main(unpack(result, tmp_path, request))
    assert main(["--refetch"]) == 0
    out = capsys.readouterr().out
    assert "its revised_data warning came from the bind" in out
    assert "result_sha256 agrees" in out
    assert "unemployment: agrees (revised data); " in out


@pytest.mark.usefixtures("world")
def test_a_field_the_user_supplied_is_not_refetched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = BindRequest(as_of="2024-03-20")
    result = invoke(UNEMPLOYMENT, {"unemployment": 0.5}, bind=request)
    main = script_main(unpack(result, tmp_path, request))
    assert main(["--refetch"]) == 0
    out = capsys.readouterr().out
    assert "unemployment: supplied by the user in the recorded run" in out


@pytest.mark.usefixtures("world")
def test_a_value_that_changed_since_is_reported_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = BindRequest(as_of="2024-03-20")
    result = invoke(UNEMPLOYMENT, {}, bind=request)
    bundle = unpack(result, tmp_path, request)
    inputs = json.loads((bundle / "inputs.json").read_bytes())
    inputs["unemployment"] = 0.99
    (bundle / "inputs.json").write_bytes(canonical_json(inputs))
    assert script_main(bundle)(["--refetch"]) == 1
    assert "unemployment: differs; " in capsys.readouterr().out
