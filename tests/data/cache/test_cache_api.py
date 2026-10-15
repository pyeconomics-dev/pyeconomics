# tests/data/cache/test_cache_api.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics.data.cache``: ``info``, ``entries``, ``clear`` and ``path``.

Phase 4's ``pyeconomics cache`` commands wrap these four, so they must create
nothing, expose no payload and take only what they document.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from typing import TYPE_CHECKING

import pytest
from cache_support import Storable, latest, replay_case, toy_query
from stubs import Scripted, answer
from toys import ToyJson

from pyeconomics.core.errors import InputError
from pyeconomics.data import cache, config
from pyeconomics.data.cache.store import DEFAULT_MAX_BYTES, FILE_NAME, SCHEMA_VERSION

if TYPE_CHECKING:
    from pathlib import Path

    from config_isolation import Isolation

pytestmark = pytest.mark.usefixtures("wall")


def fill() -> None:
    """Cache two entries of one provider and one of another."""
    provider, transport = Storable(), Scripted(answer(), answer())
    latest(provider, transport)
    latest(provider, transport, max_observations=5)
    ToyJson().fetch(
        toy_query(ToyJson, "fetch_ok"), transport=replay_case(ToyJson, "fetch_ok")
    )


def test_a_cache_that_does_not_exist_is_empty_and_stays_uncreated(
    isolated: Isolation,
) -> None:
    info = cache.info()
    assert info.path == isolated.cache_dir / FILE_NAME == cache.path()
    assert (info.exists, info.usable) == (False, True)
    assert (info.size_bytes, info.payload_bytes, info.entry_count) == (0, 0, 0)
    assert info.schema_version is None
    assert info.max_bytes == DEFAULT_MAX_BYTES == 1024**3
    assert cache.entries() == ()
    assert cache.entries("fred") == ()
    assert cache.clear() == 0
    assert cache.clear("fred") == 0
    assert not isolated.cache_dir.exists()


def test_info_describes_a_cache_with_entries() -> None:
    fill()
    info = cache.info()
    assert (info.exists, info.usable) == (True, True)
    assert info.entry_count == 3
    assert info.schema_version == SCHEMA_VERSION
    assert 0 < info.payload_bytes <= info.size_bytes
    assert info.path.is_file()


def test_entries_list_keys_times_and_sizes_and_no_payload() -> None:
    fill()
    listed = cache.entries()
    assert [(e.provider, e.series) for e in listed] == [
        ("stub", "S"),
        ("stub", "S"),
        ("toy_json", "TOYRATE"),
    ]
    entry = listed[-1]
    assert entry.vintage == "latest"
    assert entry.licence == "hosted-safe"
    assert entry.retrieved_at is not None
    assert entry.expires_at is not None
    assert entry.size_bytes > 0
    assert entry.query.startswith("{")
    assert {field.name for field in dataclasses.fields(entry)} == {
        "provider",
        "dataset",
        "series",
        "query",
        "vintage",
        "retrieved_at",
        "expires_at",
        "licence",
        "size_bytes",
    }
    # Nothing in what is returned holds an observation or the series' title.
    assert "Toy JSON series" not in repr(listed) + repr(cache.info())


def test_entries_can_be_limited_to_one_provider() -> None:
    fill()
    assert [e.provider for e in cache.entries("toy_json")] == ["toy_json"]
    assert len(cache.entries("stub")) == 2
    assert cache.entries("fred") == ()
    with pytest.raises(InputError):
        cache.entries("Not A Provider")
    with pytest.raises(InputError):
        cache.clear("../etc")


def test_clear_removes_a_providers_entries_or_everything() -> None:
    fill()
    assert cache.clear("stub") == 2
    assert [e.provider for e in cache.entries()] == ["toy_json"]
    assert cache.clear("stub") == 0
    assert cache.clear() == 1
    assert cache.entries() == ()
    info = cache.info()
    assert (info.exists, info.entry_count) == (
        True,
        0,
    )  # an empty cache, not a missing one


def test_a_cleared_entry_is_fetched_again() -> None:
    provider, transport = Storable(), Scripted(answer(), answer())
    latest(provider, transport)
    cache.clear()
    assert latest(provider, transport).origin.cache_hit is False
    assert len(transport.sent) == 2


def test_the_path_follows_the_configured_cache_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("PYECONOMICS_CACHE_DIR", str(elsewhere))
    config.reset()
    assert cache.path() == elsewhere / "cache.sqlite3"
    latest(Storable(), Scripted(answer()))
    assert (elsewhere / "cache.sqlite3").is_file()
    assert cache.info().path == elsewhere / "cache.sqlite3"


def test_the_default_path_is_the_users_cache_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYECONOMICS_CACHE_DIR")
    config.reset()
    assert cache.path().name == "cache.sqlite3"
    assert cache.path().parent.name in {"Cache", "pyeconomics"}
    assert not cache.path().exists() or cache.path().is_file()


def test_the_size_cap_is_reported_and_adjustable_for_a_block() -> None:
    with cache.override(max_bytes=1_000):
        assert cache.info().max_bytes == 1_000
    assert cache.info().max_bytes == DEFAULT_MAX_BYTES


def test_importing_and_inspecting_a_missing_cache_creates_nothing_and_loads_no_sqlite3(
    tmp_path: Path,
) -> None:
    target = tmp_path / "never-created"
    script = (
        "import sys\n"
        "from pyeconomics.data import cache\n"
        "cache.info(); cache.entries(); cache.clear(); cache.path()\n"
        "print('sqlite3' in sys.modules)\n"
    )
    environment = {
        **os.environ,
        "PYECONOMICS_CACHE_DIR": str(target),
        "PYECONOMICS_CONFIG_DIR": str(tmp_path / "config"),
    }
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
        env=environment,
    )
    assert result.stdout.strip() == "False"
    assert not target.exists()
