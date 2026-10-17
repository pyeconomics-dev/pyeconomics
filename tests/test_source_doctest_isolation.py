# tests/test_source_doctest_isolation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Source doctests must never read or clear an external configuration/cache."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed local pytest command
from pathlib import Path


def test_source_doctests_leave_external_settings_and_cache_untouched(
    tmp_path: Path,
) -> None:
    config = tmp_path / "external-config"
    config.mkdir()
    (config / "pyeconomics.toml").write_bytes(b"mode = 123\n")
    cache = tmp_path / "external-cache"
    cache.mkdir()
    sentinel = cache / "cache.sqlite3"
    contents = b"source doctests must not inspect or clear this external cache"
    sentinel.write_bytes(contents)
    environment = {
        **os.environ,
        "PYECONOMICS_CONFIG_DIR": str(config),
        "PYECONOMICS_CACHE_DIR": str(cache),
    }
    uv = shutil.which("uv")
    assert uv is not None
    result = subprocess.run(  # nosec B603  # noqa: S603 - resolved uv and fixed arguments, no shell
        [
            uv,
            "run",
            "--no-config",
            "--locked",
            "--no-sync",
            "pytest",
            "src/pyeconomics/data/cache/__init__.py",
            "--no-cov",
            "-q",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert sentinel.read_bytes() == contents
    assert (config / "pyeconomics.toml").read_bytes() == b"mode = 123\n"
