# tests/isolation_plugin.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Isolate every collected test, including source-module doctests."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from config_isolation import Isolation, isolated_configuration

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="session")
def _isolation_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("isolated-configuration")


_TEST_NUMBERS = itertools.count()


@pytest.fixture(autouse=True)
def isolated(
    monkeypatch: pytest.MonkeyPatch,
    _isolation_root: Path,
    request: pytest.FixtureRequest,
) -> Iterator[Isolation]:
    """Give every test its own settings, keys and keyring (config_isolation.py).

    The directories are named, not created, so a test that needs files makes
    them; nothing is written for the thousands of tests that do not.
    """
    if (Path.cwd() / "pyeconomics.toml").exists():
        pytest.fail("a pyeconomics.toml in the working directory would reach tests")
    root = _isolation_root / f"test-{next(_TEST_NUMBERS)}"
    live = request.node.get_closest_marker("live") is not None
    with isolated_configuration(monkeypatch, root, keep_environment=live) as isolation:
        yield isolation
