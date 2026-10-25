# scripts/clients/retitle_openapi.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Give each schema component a title made from its unique name, for a generator.

openapi-python-client names a model class after a schema's ``title``, and two
models' definitions can share one (``EffectiveInputs`` is in both
``fixed_income.duration`` and ``fixed_income.interest_rate_tree``), so it drops
whatever collides. ci.yml's clients job runs this on ``openapi.json`` first:
every component's title becomes its component name in CamelCase
(``fixed_income.duration.input.EffectiveInputs`` ->
``FixedIncomeDurationInputEffectiveInputs``). Only titles change; the published
document is never touched.

    python scripts/clients/retitle_openapi.py openapi.json retitled.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_PART = re.compile(r"[A-Za-z0-9]+")


def class_title(name: str) -> str:
    """Return a component name as a CamelCase title, keeping each part's case."""
    return "".join(part[:1].upper() + part[1:] for part in _PART.findall(name))


def retitle(document: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of an OpenAPI document whose components are titled uniquely."""
    copied: dict[str, Any] = json.loads(json.dumps(document))
    for name, schema in copied.get("components", {}).get("schemas", {}).items():
        if isinstance(schema, dict):
            schema["title"] = class_title(name)
    return copied


def main(argv: list[str]) -> int:
    """Read the document at ``argv[0]`` and write the retitled copy to ``argv[1]``."""
    if len(argv) != 2:  # noqa: PLR2004 - the two paths
        sys.stderr.write("usage: retitle_openapi.py OPENAPI_JSON OUT_JSON\n")
        return 2
    source, target = (Path(arg) for arg in argv)
    document = json.loads(source.read_text(encoding="utf-8"))
    target.write_bytes(json.dumps(retitle(document), sort_keys=True).encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
