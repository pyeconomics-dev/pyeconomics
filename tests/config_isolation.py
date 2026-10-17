# tests/config_isolation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Isolate pyeconomics' settings and keys for one test (the Credential rule).

Every test and source doctest (tests/isolation_plugin.py), and every
documentation example
(docs/conftest.py) runs inside :func:`isolated_configuration`:

- ``PYECONOMICS_CONFIG_DIR`` and ``PYECONOMICS_CACHE_DIR`` name directories
  of its own, which do not exist until the test creates them, so no test
  reads the maintainer's ``pyeconomics.toml``, ``.env`` or cache;
- every other ``PYECONOMICS_*`` variable and every ``*_API_KEY`` variable of
  the real environment is removed for the test;
- an in-memory keyring backend stands in for the OS keyring, so no test
  reads a real keyring;
- the redaction registry starts empty, the settings are reloaded, and the
  log-record factory is restored afterwards.

A test marked ``live`` (``uv run pytest -m live --force-enable-socket
tests/providers``) is the one exception: it exists to read the maintainer's or
the CI environment's real keys through the key chain, so it keeps the real
environment, configuration directory and keyring, and still starts with an empty
redaction registry and reloaded settings.

The repository root's ignored ``.env`` is never read: the key chain reads a
``.env`` file only from the configuration directory.
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    import pytest

__all__ = ["POSIX", "Home", "Isolation", "MemoryKeyring", "isolated_configuration"]

#: Whether files can be made private to their owner here (not on Windows).
POSIX = os.name == "posix"


class MemoryKeyring:
    """A keyring backend that keeps passwords in a dictionary."""

    def __init__(self) -> None:
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        """Return the stored password, or ``None``."""
        return self.passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        """Store a password."""
        self.passwords[service, username] = password

    def delete_password(self, service: str, username: str) -> None:
        """Remove a stored password."""
        del self.passwords[service, username]


@dataclass(frozen=True)
class Isolation:
    """Where one test's settings live, and its keyring."""

    root: Path
    keyring: MemoryKeyring = field(default_factory=MemoryKeyring)

    @property
    def config_dir(self) -> Path:
        """The test's ``PYECONOMICS_CONFIG_DIR``, not yet created."""
        return self.root / "config"

    @property
    def cache_dir(self) -> Path:
        """The test's ``PYECONOMICS_CACHE_DIR``, not yet created."""
        return self.root / "cache"


@dataclass(frozen=True)
class Home:
    """One test's configuration directory, working directory and keyring."""

    isolation: Isolation
    work_dir: Path

    @property
    def config_dir(self) -> Path:
        """The directory PYECONOMICS_CONFIG_DIR names."""
        return self.isolation.config_dir

    @property
    def keyring(self) -> MemoryKeyring:
        """The in-memory keyring standing in for the OS keyring."""
        return self.isolation.keyring

    @staticmethod
    def _write(path: Path, text: str | bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
        return path

    def write_dotenv(self, text: str | bytes, *, private: bool = True) -> Path:
        """Write the configuration directory's .env, owner-only when ``private``."""
        path = self._write(self.config_dir / ".env", text)
        if POSIX:
            path.chmod(0o600 if private else 0o644)
        return path

    def write_config(self, text: str | bytes, *, working: bool = False) -> Path:
        """Write pyeconomics.toml in the config (or working) directory."""
        directory = self.work_dir if working else self.config_dir
        return self._write(directory / "pyeconomics.toml", text)


@contextlib.contextmanager
def isolated_configuration(
    monkeypatch: pytest.MonkeyPatch, root: Path, *, keep_environment: bool = False
) -> Generator[Isolation]:
    """Run the body with isolated settings, keys, keyring and redaction.

    ``keep_environment`` leaves the real environment, configuration directory
    and keyring alone, for the opt-in live suite. The cache directory is the
    test's own either way: a live test reads the source, never an entry another
    test (or the user) stored, and leaves nothing in the user's cache.
    """
    from pyeconomics.data import cache, config, redaction  # noqa: PLC0415 - per test

    isolation = Isolation(root)
    if not keep_environment:
        for name in list(os.environ):
            if name.startswith("PYECONOMICS_") or name.endswith("_API_KEY"):
                monkeypatch.delenv(name)
        monkeypatch.setenv("PYECONOMICS_CONFIG_DIR", str(isolation.config_dir))
        try:
            import keyring.core  # noqa: PLC0415 - the keyring extra is optional
        except ImportError:  # pragma: no cover - the test group installs keyring
            pass
        else:
            monkeypatch.setattr(keyring.core, "_keyring_backend", isolation.keyring)
    monkeypatch.setenv("PYECONOMICS_CACHE_DIR", str(isolation.cache_dir))
    monkeypatch.setattr(redaction, "_REGISTRY", redaction._Registry())  # noqa: SLF001
    factory = logging.getLogRecordFactory()
    config.reset()
    cache.reset()
    try:
        yield isolation
    finally:
        config.reset()
        cache.reset()
        logging.setLogRecordFactory(factory)
