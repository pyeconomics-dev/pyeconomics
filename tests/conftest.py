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
rule). Request the ``isolated`` fixture for its paths and keyring. A test marked
``live`` keeps the real environment instead: it reads real keys through the key
chain, and only the opt-in live run (``-m live``) selects it.
"""

from __future__ import annotations

import os
from importlib.util import find_spec
from typing import TYPE_CHECKING

import pytest
from cache_support import WallClock
from config_isolation import Home, Isolation
from hypothesis import settings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

settings.register_profile("ci", derandomize=True, deadline=None, print_blob=True)
settings.register_profile("dev")
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

# The API fuzz imports Schemathesis, from the fuzz dependency group that only
# ci.yml's api-fuzz job installs (the Wheel rule keeps it off CPython 3.15, as
# tests/server/test_fuzz_gap.py asserts); with the group installed, the fuzz
# marker still deselects it unless -m fuzz asks for it.
collect_ignore = [] if find_spec("schemathesis") else ["server/test_api_fuzz.py"]


@pytest.fixture
def wall() -> Iterator[WallClock]:
    """Give the cache a fake wall clock for the test (tests/data/cache)."""
    from pyeconomics.data import cache  # noqa: PLC0415 - imported per test

    clock = WallClock()
    with cache.override(clock=clock):
        yield clock


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
