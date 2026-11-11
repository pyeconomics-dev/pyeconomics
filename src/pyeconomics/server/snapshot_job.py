# src/pyeconomics/server/snapshot_job.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot job's command in the image: the writer, observed (Phase 5 Step 14).

``python -m pyeconomics.server.snapshot_job write`` runs
:func:`pyeconomics.data.snapshots.__main__.main`, with the same arguments, output
and exit codes (ADR-0013 decision 6). In hosted mode with the job's telemetry
variables set (:func:`~pyeconomics.server.settings.telemetry_wanted`), it also
reports the run through :meth:`~pyeconomics.server.observability.Telemetry.snapshot`:
whether any provider succeeded, the run's time, each provider's series by state
and the age of its newest observation, and each failed provider to the error
tracker. Without them, as on staging, it is the writer alone.

The data layer imports no server module, so the report reaches the telemetry
through ``main``'s ``observe`` callback. The telemetry is flushed before the
process exits, because a job's container stops with it.

Examples
--------
>>> main(["read"])
2
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

from pyeconomics.data.errors import ConfigError
from pyeconomics.server.settings import ServerSettings, git_sha, telemetry_wanted

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.server.observability import Telemetry

__all__ = ["main"]

_USAGE: Final = "usage: python -m pyeconomics.server.snapshot_job write\n"


def _telemetry() -> Telemetry | None:
    """Start the job's telemetry when hosted mode and its variables ask for it."""
    from pyeconomics.data.modes import Mode, current_mode  # noqa: PLC0415

    if not telemetry_wanted("hosted" if current_mode() is Mode.HOSTED else "local"):
        return None
    from pyeconomics.server import observability  # noqa: PLC0415 - hosted only

    return observability.start(component="snapshots", git_sha=git_sha(ServerSettings()))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the snapshot command, observed; return its exit code."""
    from pyeconomics.data.snapshots import __main__ as command  # noqa: PLC0415

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["write"]:
        sys.stderr.write(_USAGE)
        return 2
    try:
        telemetry = _telemetry()
    except ConfigError as error:
        sys.stderr.write(f"ERROR pyeconomics.data.snapshots {error}\n")
        return 2
    if telemetry is None:
        return command.main(arguments)
    try:
        return command.main(arguments, observe=telemetry.snapshot)
    except Exception as error:
        telemetry.exception(error, route="snapshot")
        raise
    finally:
        telemetry.close()


if __name__ == "__main__":  # pragma: no cover - the job's entry point
    raise SystemExit(main())
