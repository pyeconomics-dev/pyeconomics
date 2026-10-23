# scripts/verify_phase03_live.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Published-install recipe for Phase 3; run explicitly by --post, never CI.

Keys pass through the credential chain. Output contains fixed verdicts only;
provider exception text, contacts, credentials and environment values never
reach the verifier's logs. Configuration/cache directories are isolated by
the caller and ambient API-key variables must be absent.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from importlib.metadata import version

from pyeconomics import bind, data, run
from pyeconomics.data import cache
from pyeconomics.data.credentials import has_key, withheld


def main() -> int:  # noqa: PLR0911  # each independent live invariant fails closed
    """Verify BLS without FRED, then a historical ALFRED-bound Taylor rule."""
    if version("pyeconomics") != "1.0.0a2":
        return 1
    if any(name.endswith("_API_KEY") for name in os.environ):
        return 1
    start, end = dt.date(2024, 1, 1), dt.date(2024, 12, 31)
    with cache.bypass(), withheld("fred"):
        if has_key("fred"):
            return 1
        found = data.get("bls:CUUR0000SA0", start=start, end=end)
        months = 12
        if len(found.frame.index) != months or found.sources[0].provider != "bls":
            return 1
    past = dt.date(2019, 6, 28)
    with cache.bypass():
        historical = run(
            "macro.policy_rule",
            bind("macro.policy_rule", as_of=past, calculation="taylor_1993"),
        )
        latest = run(
            "macro.policy_rule",
            bind(
                "macro.policy_rule",
                as_of=past,
                vintage="latest",
                calculation="taylor_1993",
            ),
        )
    sources = historical.manifest.data_sources
    fred = [source for source in sources if source.provider == "fred"]
    minimum_schema = 2
    if not fred or historical.manifest.schema_version < minimum_schema:
        return 1
    historical_fred = [source for source in fred if source.realtime is not None]
    required = {"PCEPILFE", "NROU", "UNRATE"}
    if not required <= {source.series_id for source in historical_fred}:
        return 1
    if not all(
        source.vintage == "as_of:2019-06-28"
        and source.realtime is not None
        and source.realtime.covers(past)
        for source in historical_fred
    ):
        return 1
    if not all(
        source.realtime is not None or "revised_data" in source.warnings
        for source in sources
    ):
        return 1
    if historical.outputs.prescribed_rate == latest.outputs.prescribed_rate:
        return 1
    # Print only public, fixed assertions; no fetched value or exception text.
    sys.stdout.write(
        json.dumps({"bls_without_fred": "PASS", "alfred_vintages": "PASS"}) + "\n"
    )
    return 0


if __name__ == "__main__":
    try:
        status = main()
    except Exception:  # noqa: BLE001  # external failures must not disclose key/URL text
        sys.stderr.write("Published live recipe failed; inspect the provider safely.\n")
        status = 1
    raise SystemExit(status)
