# tests/repo/test_verify_launch.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/verify_launch.py, the public launch's checks (Phase 5 Step 21).

The checks themselves read the public site and run only on the maintainer's
machine; these tests hold what needs no network: the arguments, the list of
checks and the helpers that read an answer.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_launch.py"


@pytest.fixture(scope="module")
def launch() -> ModuleType:
    """Load the script as a module, by path."""
    spec = importlib.util.spec_from_file_location("verify_launch", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_launch"] = module
    spec.loader.exec_module(module)
    return module


def test_every_deployed_and_verified_item_has_a_check(launch: ModuleType) -> None:
    # Step 21's Deployed & verified bullet, item by item.
    assert set(launch.CHECKS) == {
        "version",
        "headers",
        "observatory",
        "indexing",
        "redirects",
        "models",
        "snapshot",
        "edge-cache",
        "origin",
        "docs",
        "pypi",
        "install",
        "app",
        "mcp-local",
        "mcp-hosted",
        "registry",
        "parity",
        "zap",
        "release",
        "repository",
    }
    for name, check in launch.CHECKS.items():
        assert check.__doc__, name


@pytest.mark.parametrize(
    "argv",
    [["--only", "nope"], ["--tag", "v1.0.0rc2"], ["--tag", "v0.0.0-not-a-tag"]],
)
def test_bad_arguments_stop_before_any_check(
    launch: ModuleType, argv: list[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        launch.main(argv)
    assert stopped.value.code == 2


def test_only_https_or_loopback_is_ever_requested(launch: ModuleType) -> None:
    for url in ("http://pyeconomics.dev/", "ftp://example.org/", "file:///etc"):
        with pytest.raises(launch.CheckFailedError, match="not https"):
            launch.request(url)


def test_the_retrieval_times_are_found_wherever_they_sit(launch: ModuleType) -> None:
    document = {
        "data_sources": [
            {"retrieved_at": "2026-11-28T00:01:00+00:00"},
            {"nested": [{"retrieved_at": "2026-11-27T23:59:00+00:00"}]},
        ],
        "retrieved_at": None,
    }
    assert sorted(launch.retrieved_times(document)) == [
        "2026-11-27T23:59:00+00:00",
        "2026-11-28T00:01:00+00:00",
    ]


def test_the_redirect_hosts_are_every_other_domain(launch: ModuleType) -> None:
    hosts = set(launch.REDIRECT_HOSTS)
    for domain in ("pyeconomics.com", "pyeconomics.org", "pyeconomics.io"):
        assert {domain, f"www.{domain}"} <= hosts
    assert "www.pyeconomics.dev" in hosts
    assert "pyeconomics.dev" not in hosts
