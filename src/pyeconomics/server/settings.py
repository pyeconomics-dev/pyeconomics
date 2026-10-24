# src/pyeconomics/server/settings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""How a server runs: its mode, its workers, its queue and its budgets.

A server runs in one of two modes (ADR-0012 decision 11):

- ``local`` (``pyeconomics serve``): every source the user can access, the data
  layer in library mode, no run budget unless one is configured, and answers
  only for loopback host names unless ``allow_remote`` is set;
- ``hosted`` (the container, Step 12): the data layer in hosted mode, so only
  hosted-safe and user-supplied data, and every run held to its cost class's
  budget (:data:`~pyeconomics.surfaces.budgets.HOSTED_BUDGETS`).

:class:`ServerSettings` holds the rest. Two values come from the environment
when the settings leave them unset: ``PYECONOMICS_WORKERS``, the number of
worker processes (default: the CPU count; ``0`` runs every task inline, in the
app's own process, for tests), and ``PYECONOMICS_GIT_SHA``, the commit the
container was built from, which ``/version`` reports.

Examples
--------
>>> settings = ServerSettings(workers=0)
>>> worker_count(settings), budgets_for("local", settings) is None
(0, True)
>>> budgets_for("hosted", settings)[CostClass.HEAVY]
30.0
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Literal

from pyeconomics.core.errors import InputError
from pyeconomics.core.spec import CostClass
from pyeconomics.surfaces.budgets import HOSTED_BUDGETS

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = [
    "DEFAULT_QUEUE_LIMIT",
    "GIT_SHA_VARIABLE",
    "MODES",
    "WORKERS_VARIABLE",
    "ServerMode",
    "ServerSettings",
    "budgets_for",
    "data_mode",
    "git_sha",
    "worker_count",
]

#: A server's mode.
ServerMode = Literal["local", "hosted"]
#: Every mode, in the order the documentation lists them.
MODES: Final[tuple[ServerMode, ...]] = ("local", "hosted")

#: The environment variable that sets the number of worker processes.
WORKERS_VARIABLE: Final = "PYECONOMICS_WORKERS"
#: The environment variable that names the commit ``/version`` reports.
GIT_SHA_VARIABLE: Final = "PYECONOMICS_GIT_SHA"
#: How many tasks may wait for a worker before the server answers 503.
DEFAULT_QUEUE_LIMIT: Final = 32

_GIT_SHA: Final = re.compile(r"[0-9a-f]{7,40}")
_UNKNOWN: Final = "unknown"


@dataclass(frozen=True, slots=True, kw_only=True)
class ServerSettings:
    """What a server needs besides its mode.

    Parameters
    ----------
    workers
        Worker processes; ``None`` reads ``PYECONOMICS_WORKERS``, else uses the
        CPU count. ``0`` runs every task inline, in the app's process, with no
        budget and no queue: for tests.
    queue_limit
        How many tasks may wait for a free worker; one more is answered with the
        ``server-busy`` problem (503).
    budgets
        Wall-clock seconds by cost class. ``None`` means the mode's default: the
        hosted budgets in hosted mode, none in local mode.
    offline
        Serve only cached data; ``None`` keeps the configured setting.
    allow_remote
        In local mode, answer requests addressed to any host name, not only to
        a loopback one (``pyeconomics serve --allow-remote``).
    git_sha
        The commit ``/version`` reports; ``None`` reads ``PYECONOMICS_GIT_SHA``.
        Anything but 7 to 40 lowercase hexadecimal digits reads as ``unknown``.
    worker_setup
        A function each worker process calls once, before its first task. The
        workers are spawned, so it must be importable by its module and name;
        the tests install toy models with it.

    Raises
    ------
    InputError
        For a negative worker count, a queue limit below 1, or a budget that is
        not a positive finite number of seconds.
    """

    workers: int | None = None
    queue_limit: int = DEFAULT_QUEUE_LIMIT
    budgets: Mapping[CostClass, float] | None = None
    offline: bool | None = None
    allow_remote: bool = False
    git_sha: str | None = None
    worker_setup: Callable[[], object] | None = None

    def __post_init__(self) -> None:
        """Check the counts and the budgets, and hold the budgets read-only."""
        if self.workers is not None and not _whole(self.workers, 0):
            msg = f"workers is a whole number from 0, not {self.workers!r}"
            raise InputError(msg)
        if not _whole(self.queue_limit, 1):
            msg = f"queue_limit is a whole number from 1, not {self.queue_limit!r}"
            raise InputError(msg)
        if self.budgets is not None:
            checked = {}
            for cost, seconds in self.budgets.items():
                value: object = seconds
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int | float)
                    or not math.isfinite(value)
                    or value <= 0
                ):
                    msg = f"a budget is a positive number of seconds, not {value!r}"
                    raise InputError(msg)
                checked[CostClass(cost)] = float(value)
            object.__setattr__(self, "budgets", MappingProxyType(checked))


def _whole(value: object, floor: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= floor


def worker_count(settings: ServerSettings) -> int:
    """Return how many worker processes to start.

    Raises
    ------
    ConfigError
        If ``PYECONOMICS_WORKERS`` is set to anything but a whole number from 0.
    """
    if settings.workers is not None:
        return settings.workers
    text = os.environ.get(WORKERS_VARIABLE)
    if text is None or not text.strip():
        # process_cpu_count (3.13) honours the CPU affinity; 3.12 has cpu_count.
        count = getattr(os, "process_cpu_count", os.cpu_count)()
        return int(count or 1)
    stripped = text.strip()
    if not stripped.isdigit():
        from pyeconomics.data.errors import ConfigError  # noqa: PLC0415

        msg = f"{WORKERS_VARIABLE} is a whole number from 0"
        raise ConfigError(msg)
    return int(stripped)


def git_sha(settings: ServerSettings) -> str:
    """Return the commit ``/version`` reports, or ``unknown``."""
    text = settings.git_sha
    if text is None:
        text = os.environ.get(GIT_SHA_VARIABLE, "")
    text = text.strip()
    return text if _GIT_SHA.fullmatch(text) else _UNKNOWN


def budgets_for(
    mode: ServerMode, settings: ServerSettings
) -> Mapping[CostClass, float] | None:
    """Return the run budgets: the settings' own, else the mode's default."""
    if settings.budgets is not None:
        return settings.budgets
    return HOSTED_BUDGETS if mode == "hosted" else None


def data_mode(mode: ServerMode) -> Literal["library", "hosted"]:
    """Return the data layer's mode for a server mode: local serves as the library."""
    return "hosted" if mode == "hosted" else "library"
