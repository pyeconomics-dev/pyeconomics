# src/pyeconomics/exports/reproduction.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The text of a bundle's ``reproduce.py`` (ADR-0012 decision 7).

The wheel admits only ``.py`` files (scripts/checks/dist_contents.py), so the
script a bundle carries lives here as :data:`REPRODUCE_SCRIPT`, a string
:func:`~pyeconomics.exports.bundle.write_bundle` writes unchanged. It uses only
the standard library until it imports pyeconomics, and then:

- checks that the installed pyeconomics is the version the bundle recorded,
  printing the install command and exiting 2 when it is not;
- reruns ``pyeconomics.run(model_id, inputs)`` on ``inputs.json`` and compares
  the rerun's ``result_sha256`` with the recorded one (exit 0 when they agree,
  1 when not), and says whether the rerun's canonical bytes equal
  ``result.json`` or which parts of the manifest differ (the dependency versions
  of another environment, or the data records a rerun from inputs never reads);
- with ``--refetch``, binds the model's data again from ``request.json`` (the
  recorded as-of date, vintage policy, profile, concepts and parameters) and
  reports, field by field, whether each value agrees with the recorded input,
  labelling revised data;
- with ``--out FILE``, writes the rerun's canonical bytes to ``FILE``.

A run that bound data and read revised data carries the ``revised_data`` warning
the bind added; a rerun from the recorded inputs binds nothing, so the script
adds that recorded warning back before it compares the hashes, and says so.

Examples
--------
>>> compile(REPRODUCE_SCRIPT, "reproduce.py", "exec").co_filename
'reproduce.py'
"""

from __future__ import annotations

from typing import Final

__all__ = ["REPRODUCE_SCRIPT"]

REPRODUCE_SCRIPT: Final = r"""#!/usr/bin/env python3
# reproduce.py: rerun the pyeconomics result in this bundle and compare it.
#
# This file is a program. Read it before you run a bundle someone else made.
#
# It reads result.json, inputs.json and request.json beside it, imports the
# pyeconomics version requirements.txt pins, reruns the model on the recorded
# inputs and compares the result's SHA-256 with the recorded one.
#
#     python reproduce.py             exit 0 when the result is the same, else 1
#     python reproduce.py --refetch   also bind the data again as recorded and
#                                     report whether each field agrees
#     python reproduce.py --out FILE  write the rerun's canonical JSON to FILE
#
# Exit code 2: pyeconomics is not installed, another version is, or --refetch
# was asked of a bundle that bound no data.

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSTALL = "pip install -r requirements.txt"
REVISED_DATA = "revised_data"


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def plain(value):
    # A bound array is a tuple; the recorded inputs hold lists.
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def differences(rerun, recorded, prefix=""):
    found = []
    for key in sorted(set(rerun) | set(recorded)):
        left, right = rerun.get(key), recorded.get(key)
        if left == right:
            continue
        if isinstance(left, dict) and isinstance(right, dict):
            found.extend(differences(left, right, f"{prefix}{key}."))
        else:
            found.append(f"{prefix}{key}")
    return found


def rerun_result(pyeconomics, recorded, inputs, out):
    from pyeconomics.core.manifest import result_sha256

    result = pyeconomics.run(recorded["model_id"], inputs)
    produced = result.to_dict()
    warnings = list(produced["warnings"])
    restored = [
        warning
        for warning in recorded["warnings"]
        if warning["code"] == REVISED_DATA and warning not in warnings
    ]
    if restored:
        print(
            "The recorded run read revised data; its revised_data warning came "
            "from the bind, which a rerun from the recorded inputs does not "
            "repeat, so it is added back before the hashes are compared."
        )
    body = {
        "inputs": produced["inputs"],
        "model_id": produced["model_id"],
        "model_version": produced["model_version"],
        "outputs": produced["outputs"],
        "warnings": warnings + restored,
    }
    digest = result_sha256(body)
    expected = recorded["manifest"]["result_sha256"]
    data = result.to_json().encode("utf-8")
    if out is not None:
        Path(out).write_bytes(data)
    if digest != expected:
        print(f"result_sha256 differs: recorded {expected}, rerun {digest}")
        return False
    print(f"result_sha256 agrees: {digest}")
    if data == (HERE / "result.json").read_bytes():
        print("The rerun's canonical bytes are identical to result.json.")
    else:
        changed = ", ".join(differences(produced, recorded))
        print(f"The rerun's bytes differ from result.json in: {changed}")
    return True


def refetch(pyeconomics, recorded, inputs, request):
    if request is None:
        print("This bundle records no bind request, so there is nothing to refetch.")
        return None
    as_of = request["as_of"]
    bound = pyeconomics.bind(
        recorded["model_id"],
        as_of=None if as_of is None else datetime.date.fromisoformat(as_of),
        vintage=request["vintage"],
        profile=request["profile"],
        concepts=request["concepts"] or None,
        parameters=request["parameters"] or None,
    )
    supplied = {
        record["field"]
        for record in recorded["manifest"]["data_sources"]
        if record["licence"] == "user-supplied"
    }
    agreed = True
    for record in bound.sources:
        field = record.field
        if field in supplied:
            print(f"{field}: supplied by the user in the recorded run, not refetched")
            continue
        same = plain(bound.values[field]) == inputs.get(field)
        agreed = agreed and same
        label = " (revised data)" if field in bound.revised else ""
        vintage = record.vintage or "latest"
        verdict = "agrees" if same else "differs"
        print(
            f"{field}: {verdict}{label}; {record.provider}:{record.series_id}, "
            f"vintage {vintage}"
        )
    return agreed


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rerun the pyeconomics result in this bundle and compare it."
    )
    parser.add_argument(
        "--refetch",
        action="store_true",
        help="also bind the data again as recorded and compare each field",
    )
    parser.add_argument(
        "--out", metavar="FILE", help="write the rerun's canonical JSON to FILE"
    )
    options = parser.parse_args(argv)
    recorded = load("result.json")
    inputs = load("inputs.json")
    request = load("request.json")
    version = recorded["manifest"]["package_version"]
    try:
        import pyeconomics
    except ImportError:
        print(f"pyeconomics is not installed; install it with: {INSTALL}")
        return 2
    if pyeconomics.__version__ != version:
        print(
            f"This bundle was made with pyeconomics {version}, but "
            f"{pyeconomics.__version__} is installed; install it with: {INSTALL}"
        )
        return 2
    same = rerun_result(pyeconomics, recorded, inputs, options.out)
    if options.refetch:
        agreed = refetch(pyeconomics, recorded, inputs, request)
        if agreed is None:
            return 2
        same = same and agreed
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
"""
