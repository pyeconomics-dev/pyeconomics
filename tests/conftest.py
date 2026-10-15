# tests/conftest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Suite-wide test configuration.

Hypothesis profiles, chosen by the ``HYPOTHESIS_PROFILE`` environment variable
(default ``dev``):

- ``ci``: derandomized, so a CI failure reproduces on any machine; no deadline,
  because shared runners time unevenly; and ``print_blob``, so a failure prints
  the ``@reproduce_failure`` blob.
- ``dev``: hypothesis' defaults, randomized, for local runs.

Every test also runs inside ``config_isolation.isolated_configuration``: its
own configuration and cache directories, no provider key or ``PYECONOMICS_*``
variable from the real environment, and an in-memory keyring (the Credential
rule). Request the ``isolated`` fixture for its paths and keyring.
"""

from __future__ import annotations

import itertools
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from config_isolation import Home, Isolation, isolated_configuration
from hypothesis import settings

if TYPE_CHECKING:
    from collections.abc import Iterator

settings.register_profile("ci", derandomize=True, deadline=None, print_blob=True)
settings.register_profile("dev")
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture(scope="session")
def _isolation_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("isolated-configuration")


_TEST_NUMBERS = itertools.count()


@pytest.fixture(autouse=True)
def isolated(
    monkeypatch: pytest.MonkeyPatch, _isolation_root: Path
) -> Iterator[Isolation]:
    """Give every test its own settings, keys and keyring (config_isolation.py).

    The directories are named, not created, so a test that needs files makes
    them; nothing is written for the thousands of tests that do not.
    """
    if (Path.cwd() / "pyeconomics.toml").exists():
        pytest.fail("a pyeconomics.toml in the working directory would reach tests")
    root = _isolation_root / f"test-{next(_TEST_NUMBERS)}"
    with isolated_configuration(monkeypatch, root) as isolation:
        yield isolation


@pytest.fixture
def home(isolated: Isolation, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    """Run in an empty working directory, with ``isolated``'s settings and keyring.

    Its helpers write ``pyeconomics.toml`` and the ``.env`` file where the data
    layer looks for them (tests/data/credentials).
    """
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    return Home(isolated, work_dir)
