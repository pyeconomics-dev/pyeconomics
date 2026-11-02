# tests/parity/test_check_deployed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/parity/check_deployed.py, the deployed API's parity check.

The script's HTTP is replaced by a stand-in that answers as a deployment
would, from the Python API in this process, so no socket opens.
"""

from __future__ import annotations

import importlib.util
import json
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import pyeconomics
from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    import urllib.request
    from types import ModuleType

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "parity" / "check_deployed.py"
)
GOLDEN = """model = "fixed_income.duration"

[[cases]]
id = "toy"

[cases.inputs]
calculation = "macaulay_modified"
settlement = 2026-01-15
maturity = 2036-01-15
coupon_rate = 0.045
yield_to_maturity = 0.045
"""


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_deployed", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = load_script()


@pytest.fixture
def golden(tmp_path: Path) -> Path:
    (tmp_path / "fixed_income").mkdir()
    (tmp_path / "fixed_income" / "duration.toml").write_text(GOLDEN, encoding="utf-8")
    return tmp_path


class Deployment:
    """Answers each run from the Python API, optionally changed or refused first."""

    def __init__(self, *, change: bytes = b"", refusals: int = 0) -> None:
        self.change = change
        self.refusals = refusals
        self.requests: list[urllib.request.Request] = []

    def __call__(
        self, request: urllib.request.Request
    ) -> tuple[int, dict[str, str], bytes]:
        self.requests.append(request)
        if self.refusals:
            self.refusals -= 1
            return 429, {"Retry-After": "0"}, b'{"type":"x","detail":"slow down"}'
        model = request.full_url.split("/v1/models/")[1].removesuffix("/run")
        assert isinstance(request.data, bytes)
        inputs: dict[str, Any] = json.loads(request.data)
        return (
            200,
            {},
            pyeconomics.run(model, inputs).to_json().encode("utf-8") + self.change,
        )


def test_the_same_bytes_pass(
    golden: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    deployment = Deployment()
    monkeypatch.setattr(check, "open_url", deployment)
    assert check.main([str(golden), "https://staging.pyeconomics.dev/"]) == 0
    out = capsys.readouterr().out
    assert "same     fixed_income.duration::toy" in out
    assert "without an Access service token" in out
    [request] = deployment.requests
    assert (
        request.full_url
        == "https://staging.pyeconomics.dev/v1/models/fixed_income.duration/run"
    )
    assert request.get_method() == "POST"
    assert request.headers["Content-type"] == "application/json"
    inputs = {
        "calculation": "macaulay_modified",
        "settlement": "2026-01-15",
        "maturity": "2036-01-15",
        "coupon_rate": 0.045,
        "yield_to_maturity": 0.045,
    }
    assert request.data == canonical_json(inputs)


def test_a_byte_difference_fails_and_names_the_case(
    golden: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check, "open_url", Deployment(change=b" "))
    assert check.main([str(golden), "https://staging.pyeconomics.dev"]) == 1
    out = capsys.readouterr().out
    assert "differs  fixed_income.duration::toy" in out
    assert "not canonical JSON" in out
    assert "1 difference(s)" in out


RESULT = {
    "inputs": {"rate": 0.05, "when": "2026-01-15"},
    "manifest": {
        "dependencies": {"numpy": "2.5.3"},
        "result_sha256": "a" * 64,
        "package_version": "1.0.0",
    },
    "outputs": {"npv": 9859.423412459382, "weights": [0.015238095238095488, 1]},
    "warnings": [],
}


def answer(**changes: object) -> bytes:
    """Return RESULT's canonical bytes, with some paths (``a__b``) replaced."""
    document = json.loads(json.dumps(RESULT))
    for path, value in changes.items():
        *parents, last = path.split("__")
        node = document
        for part in parents:
            node = node[part]
        node[last] = value
    return canonical_json(document)


def test_numbers_in_their_last_digits_and_their_hash_read_close() -> None:
    moved = answer(
        outputs__npv=9859.423412459375,
        outputs__weights=[0.015238095238095441, 1.0],
        manifest__result_sha256="b" * 64,
    )
    verdict, lines = check.compare(answer(), moved)
    assert verdict == "close"
    assert [line.split(":")[0] for line in lines] == [
        "outputs.npv",
        "outputs.weights[0]",
    ]


@pytest.mark.parametrize(
    ("changes", "what"),
    [
        ({"outputs__npv": 9859.43}, "outputs.npv"),
        ({"manifest__dependencies": {"numpy": "2.5.4"}}, "manifest.dependencies"),
        ({"inputs__when": "2026-01-16"}, "inputs.when"),
        ({"warnings": [{"code": "x", "message": "y"}]}, "warnings"),
        ({"outputs__weights": [0.015238095238095488]}, "outputs.weights"),
        ({"manifest__result_sha256": "b" * 64}, "manifest.result_sha256"),
    ],
)
def test_anything_but_a_last_digit_differs(changes: dict[str, Any], what: str) -> None:
    verdict, lines = check.compare(answer(), answer(**changes))
    assert verdict == "differs"
    assert any(line.startswith(what) for line in lines), lines


def test_a_problem_must_match_exactly() -> None:
    problem = ("invalid-input", 422, "rate is too high")
    assert check.compare(problem, problem) == ("same", [])
    assert (
        check.compare(problem, ("invalid-input", 422, "rate is high"))[0] == "differs"
    )
    assert check.compare(answer(), problem)[0] == "differs"


def test_the_access_token_is_sent_and_never_printed(
    golden: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = secrets.token_hex(16)
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id.access")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", secret)
    deployment = Deployment()
    monkeypatch.setattr(check, "open_url", deployment)
    assert check.main([str(golden), "https://staging.pyeconomics.dev"]) == 0
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "with an Access service token" in captured.out
    assert deployment.requests[0].headers["Cf-access-client-secret"] == secret


def test_a_rate_limit_is_retried(golden: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    deployment = Deployment(refusals=2)
    monkeypatch.setattr(check, "open_url", deployment)
    monkeypatch.setattr(check.time, "sleep", lambda _seconds: None)
    assert check.main([str(golden), "https://staging.pyeconomics.dev"]) == 0
    assert len(deployment.requests) == 3


@pytest.mark.parametrize(
    "base",
    [
        "http://staging.pyeconomics.dev",
        "ftp://x",
        # User information, built at run time so no scanner reads a credential.
        f"https://someone:{secrets.token_hex(4)}@example.org",
        "https://example.org/v1",
        "https://example.org/?q=1",
    ],
)
def test_only_an_https_origin_or_a_loopback_one_is_asked(
    base: str, golden: Path
) -> None:
    assert check.main([str(golden), base]) == 2


def test_a_loopback_server_may_be_plain_http() -> None:
    assert check.check_base("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert check.check_base("http://localhost:8000") == "http://localhost:8000"


def test_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main([]) == 2
    assert "usage" in capsys.readouterr().err
