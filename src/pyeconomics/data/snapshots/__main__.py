# src/pyeconomics/data/snapshots/__main__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot job's entry point: ``python -m pyeconomics.data.snapshots write``.

The Cloud Run job runs it in hosted mode with ``PYECONOMICS_SNAPSHOT_DIR`` naming
the mounted bucket (:mod:`pyeconomics.data.snapshots.writer`). It logs to
standard error through the redacting log-record factory and prints one line of
canonical JSON to standard output: the run's counts and its time in seconds,
never a URL, a path or a key. It exits 0 when any provider succeeded, 1 when
none did, and 2 for a usage or configuration error.

The image runs it through ``python -m pyeconomics.server.snapshot_job write``,
which passes ``observe`` to report the run to the hosted service's telemetry
(Phase 5 Step 14): the data layer imports no server module.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import redaction
from pyeconomics.data.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pyeconomics.data.snapshots.writer import Report

__all__ = ["main"]

_USAGE: Final = "usage: python -m pyeconomics.data.snapshots write\n"
_LOG: Final = logging.getLogger("pyeconomics.data.snapshots")


def main(
    argv: Sequence[str] | None = None,
    *,
    observe: Callable[[Report], object] | None = None,
) -> int:
    """Run the command line and return its exit code.

    ``observe``, when given, receives the run's report before the summary is
    printed.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["write"]:
        sys.stderr.write(_USAGE)
        return 2
    redaction.install()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    from pyeconomics.data.snapshots import writer  # noqa: PLC0415 - after logging

    try:
        report = writer.write()
    except ConfigError as error:
        _LOG.error("%s", error)
        return 2
    if observe is not None:
        observe(report)
    sys.stdout.write(canonical_json(report.summary()).decode("utf-8") + "\n")
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - the job's entry point
    raise SystemExit(main())
