# scripts/clients/python_smoke.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Run one data-free model through the generated Python client (ci.yml's clients job).

The client openapi-python-client generated into ``CLIENT_DIR/pyeconomics_client``
calls ``POST /v1/models/foundations.time_value/run`` on a local ``pyeconomics
serve``, and the answer's bytes are written as they came, for
``compare_runs.py`` to check against the Python API's ``Result.to_json()``.

    python scripts/clients/python_smoke.py CLIENT_DIR http://127.0.0.1:8765 py-run.json
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

#: The run every client makes, and compare_runs.py repeats with the Python API.
INPUTS = {
    "calculation": "present_value",
    "rate": 0.05,
    "periods": 10,
    "future_value": 100,
}


def main(argv: list[str]) -> int:
    """Run through the client in ``argv[0]`` at ``argv[1]``; write ``argv[2]``."""
    if len(argv) != 3:  # noqa: PLR2004 - the three arguments
        sys.stderr.write("usage: python_smoke.py CLIENT_DIR BASE_URL OUT_FILE\n")
        return 2
    client_dir, base_url, out = argv
    sys.path.insert(0, str(Path(client_dir).resolve()))
    package = importlib.import_module("pyeconomics_client")
    endpoint = importlib.import_module(
        "pyeconomics_client.api.foundations.run_foundations_time_value"
    )
    inputs = importlib.import_module(
        "pyeconomics_client.models.foundations_time_value_input_present_value_inputs"
    )
    body = inputs.FoundationsTimeValueInputPresentValueInputs.from_dict(INPUTS)
    with package.Client(base_url=base_url) as client:
        response = endpoint.sync_detailed(client=client, body=body)
    if response.status_code != 200:  # noqa: PLR2004 - HTTP OK
        sys.stderr.write(f"the run answered HTTP {int(response.status_code)}\n")
        return 1
    Path(out).write_bytes(response.content)
    sys.stdout.write(f"wrote {len(response.content)} bytes to {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
