# docs/conftest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Run only authored site examples, with pytest's socket isolation.

Each example also runs with isolated settings and keys
(tests/config_isolation.py), so no example reads the reader's real
configuration, environment keys or OS keyring.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import pytest
from config_isolation import Isolation, isolated_configuration
from sybil import Sybil
from sybil.parsers.myst import PythonCodeBlockParser

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

collect_ignore = ["conf.py", "_ext"]

_EXAMPLE_NUMBERS = itertools.count()


@pytest.fixture
def isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Isolation]:
    """Isolate one example's settings, keys and keyring."""
    root: Path = tmp_path_factory.getbasetemp() / f"docs-{next(_EXAMPLE_NUMBERS)}"
    with isolated_configuration(monkeypatch, root) as isolation:
        yield isolation


# MyST-NB cells execute in Sphinx; generated model pages contain JSON examples.
pytest_collect_file = Sybil(
    parsers=[PythonCodeBlockParser()],
    filenames=[
        "index.md",
        "installation.md",
        "quickstart.md",
        "conventions.md",
        "results.md",
        "errata.md",
        "notices.md",
        "changelog.md",
        "bindings.md",
        "keys.md",
        "cache.md",
        "writing-a-provider.md",
        "registry.md",
        "exports.md",
    ],
    excludes=["roadmap/*", "adr/*", "releases/*", "reference/*", "_build/*"],
    fixtures=["isolated"],
).pytest()
