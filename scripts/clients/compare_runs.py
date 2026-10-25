# scripts/clients/compare_runs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Check that each client's answer is the Python API's bytes (ci.yml's clients job).

Each file holds the body one generated client received for the smoke run
(``python_smoke.py``'s :data:`INPUTS`; ``tools/node/smoke.mjs`` sends the same).
It must equal ``pyeconomics.run(...).to_json().encode()`` byte for byte: the
REST API returns the canonical bytes unchanged (ADR-0012 decision 3), and a
client that receives them raw must not change them either.

    python scripts/clients/compare_runs.py ts-run.json py-run.json
"""

from __future__ import annotations

import sys
from pathlib import Path

from python_smoke import INPUTS

import pyeconomics

MODEL = "foundations.time_value"


def differing(paths: list[Path], expected: bytes) -> list[str]:
    """Return the names of the files whose bytes are not ``expected``."""
    return [path.name for path in paths if path.read_bytes() != expected]


def main(argv: list[str]) -> int:
    """Compare every file named in ``argv`` with the Python API's bytes."""
    if not argv:
        sys.stderr.write("usage: compare_runs.py RUN_FILE...\n")
        return 2
    expected = pyeconomics.run(MODEL, INPUTS).to_json().encode("utf-8")
    wrong = differing([Path(arg) for arg in argv], expected)
    if wrong:
        sys.stderr.write(f"other bytes than the Python API's: {', '.join(wrong)}\n")
        return 1
    sys.stdout.write(f"{len(argv)} clients returned the Python API's bytes\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
