# scripts/zap/access_props.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Write ZAP's replacer rules that add Cloudflare Access's service-token headers.

zap-baseline.yml runs this before the scan. It reads CF_ACCESS_CLIENT_ID and
CF_ACCESS_CLIENT_SECRET from the environment and writes a Java properties file
for ZAP's ``-configfile`` option: two replacer rules, each adding one header to
requests whose URL is on SCAN_HOST, and to nothing else. It prints nothing of
either value. With neither set (after the cutover), it writes an empty file, and
ZAP adds no header.

Usage: python3 scripts/zap/access_props.py <output file>
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HEADERS = (
    ("CF-Access-Client-Id", "CF_ACCESS_CLIENT_ID"),
    ("CF-Access-Client-Secret", "CF_ACCESS_CLIENT_SECRET"),
)
HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
ARGUMENTS = 2


class RulesError(SystemExit):
    """The environment cannot give a usable set of rules."""


def escape(value: str) -> str:
    """Return a properties value: backslashes doubled, every other character kept."""
    return value.replace("\\", "\\\\")


def rules(host: str, environment: dict[str, str]) -> str:
    """Return the properties text for the headers present in ``environment``."""
    if not HOST.match(host):
        message = "SCAN_HOST must be a host name"
        raise RulesError(message)
    present = [(header, environment.get(name, "")) for header, name in HEADERS]
    if not any(value for _, value in present):
        return ""
    if not all(value for _, value in present):
        message = "set both Access variables, or neither"
        raise RulesError(message)
    url = escape("https://" + re.escape(host) + "/.*")
    lines: list[str] = []
    for index, (header, value) in enumerate(present):
        if "\n" in value or "\r" in value:
            message = f"{header} holds a line break"
            raise RulesError(message)
        prefix = f"replacer.full_list({index})."
        lines += [
            f"{prefix}description=access-header-{index}",
            f"{prefix}enabled=true",
            f"{prefix}matchtype=REQ_HEADER",
            f"{prefix}matchstr={header}",
            f"{prefix}regex=false",
            f"{prefix}replacement={escape(value)}",
            f"{prefix}url={url}",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    """Write the rules file named by ``argv[1]`` and say whether it holds rules."""
    if len(argv) != ARGUMENTS:
        sys.stderr.write(f"{__doc__}\n")
        return 2
    text = rules(os.environ.get("SCAN_HOST", ""), dict(os.environ))
    Path(argv[1]).write_bytes(text.encode("utf-8"))
    sys.stdout.write(
        "Access header rules written\n"
        if text
        else "No Access header rules: none set\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
