# tests/cli/test_cli_cache.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics cache`` (Phase 4 Step 4).

Each test runs with its own cache directory (the isolated fixture). An entry is
stored by fetching from the cache tests' storable stub provider, so the
commands list, describe and clear a real cache file; none shows a payload.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cache_support import Storable, latest
from cli_support import cli
from stubs import Scripted, answer

from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import cache
from pyeconomics.surfaces.documents import jsonable

if TYPE_CHECKING:
    import pytest
    from config_isolation import Isolation


def store_one() -> None:
    latest(Storable(), Scripted(answer()))


def test_an_empty_cache_has_nothing_and_creates_nothing(isolated: Isolation) -> None:
    listed = cli("cache", "ls", "--format", "json")
    assert (listed.code, json.loads(listed.stdout)) == (0, [])
    table = cli("cache", "ls")
    assert table.text.splitlines()[-1] == "0 cached entries."
    info = json.loads(cli("cache", "info", "--format", "json").stdout)
    assert (info["exists"], info["entry_count"]) == (False, 0)
    assert cli("cache", "path").text == f"{cache.path()}\n"
    assert not isolated.cache_dir.exists()


def test_the_commands_describe_and_clear_a_stored_entry() -> None:
    store_one()
    listed = cli("cache", "ls", "--format", "json")
    assert listed.stdout == canonical_json(jsonable(cache.entries())) + b"\n"
    (entry,) = json.loads(listed.stdout)
    assert entry["provider"] == "stub"
    assert "payload" not in entry
    table = cli("cache", "ls", "--provider", "stub")
    assert table.text.splitlines()[-1] == "1 cached entry."
    info = cli("cache", "info")
    assert any(line.split() == ["entry_count", "1"] for line in info.text.splitlines())
    assert (
        cli("cache", "clear", "--provider", "other").text
        == "Deleted 0 cached entries.\n"
    )
    assert cli("cache", "clear").text == "Deleted 1 cached entry.\n"
    assert cache.entries() == ()


def test_a_bad_provider_id_is_invalid_input() -> None:
    outcome = cli("cache", "ls", "--provider", "Not An Id")
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: ")


def test_a_broken_setting_is_an_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_OFFLINE", "maybe")
    outcome = cli("cache", "path")
    assert outcome.code == 1
    assert outcome.stderr.startswith("invalid-configuration: PYECONOMICS_OFFLINE")
