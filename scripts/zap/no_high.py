# scripts/zap/no_high.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fail on any High alert in a ZAP JSON report, whatever the rules file says.

zap-baseline.yml runs this after the scan: a High finding is a FAIL at the
launch readiness gate (Phase 5 Step 20), so `.zap/rules.tsv` may record a Medium
or lower as a false positive, never a High. It prints each alert's rule id, risk
and count, and no request or response.

Usage: python3 scripts/zap/no_high.py report_json.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HIGH = "3"
ARGUMENTS = 2


def alerts(report: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """Return (rule id, risk code, risk, count) for every alert of every site."""
    return [
        (
            str(alert.get("pluginid", "")),
            str(alert.get("riskcode", "")),
            str(alert.get("riskdesc", "")),
            str(alert.get("count", "")),
        )
        for site in report.get("site", [])
        for alert in site.get("alerts", [])
    ]


def main(argv: list[str]) -> int:
    """Print the report's alerts and return 1 when one of them is High."""
    if len(argv) != ARGUMENTS:
        sys.stderr.write(f"{__doc__}\n")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        sys.stdout.write(f"{path} is missing: the scan wrote no report\n")
        return 1
    found = alerts(json.loads(path.read_text(encoding="utf-8")))
    for rule, _, risk, count in found:
        sys.stdout.write(f"{rule}\t{risk}\t{count} instances\n")
    highs = [rule for rule, code, _, _ in found if code == HIGH]
    if highs:
        sys.stdout.write(f"High alerts: {', '.join(highs)}\n")
        return 1
    sys.stdout.write(f"No High alert among {len(found)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
