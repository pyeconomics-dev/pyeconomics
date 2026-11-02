# scripts/parity/check_deployed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Check a deployed API against this environment's Python API (Phase 5 Step 6).

The web parity suite (``web/tests/parity/``) proves the calculators' requests
return the Python API's bytes from a local server; this script asks a deployed
one, as the calculators reach it on their site's own origin (ADR-0013
decision 8). For the first golden case of each domain (read from
``tests/golden/`` with ``tomllib``, as ``check_installed.py`` reads them), it
POSTs the inputs' canonical JSON to ``<base>/v1/models/<id>/run`` and compares
the answer with ``pyeconomics.run``'s here: the same canonical bytes, or the
same problem slug, status and detail. Run it where the deployment's own
versions are installed, the same commit's wheel under Python 3.14 with
``uv.lock``'s versions and the container's extras, because a result's manifest
records its dependencies' versions (``deploy-staging.yml`` does).

A deployment behind Cloudflare Access (staging) needs its service token:
``CF_ACCESS_CLIENT_ID`` and ``CF_ACCESS_CLIENT_SECRET`` in the environment,
sent as Access's headers and never printed. The base URL is ``https://``, or
``http://`` to a loopback address for a local server. A rate limit or a busy
server is retried, up to three times, after its ``Retry-After``.

    python -I scripts/parity/check_deployed.py tests/golden https://staging.pyeconomics.dev
"""

from __future__ import annotations

import ipaddress
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Final

import pyeconomics
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.problems import TYPE_BASE, problem_for

#: An answer: canonical bytes, or (slug, HTTP status, detail).
Answer = bytes | tuple[str, int, str]

TIMEOUT: Final = 60
ATTEMPTS: Final = 4
#: The longest wait a Retry-After may ask for, in seconds.
LONGEST_WAIT: Final = 30
RETRIED: Final = frozenset({429, 502, 503, 504})
USER_AGENT: Final = "pyeconomics-parity-check/1.0"
#: Each environment variable of the Access service token, and its header's name.
ACCESS: Final = {
    "CF_ACCESS_CLIENT_ID": "CF-Access-Client-Id",
    "CF_ACCESS_CLIENT_SECRET": "CF-Access-Client-Secret",  # nosec B105 - a header name
}


def cases(golden: Path) -> list[tuple[str, str, dict[str, Any]]]:
    """Return the first case of each domain's first golden file."""
    chosen: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for path in sorted(golden.rglob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        model = str(data["model"])
        domain = model.partition(".")[0]
        if domain not in chosen:
            first = data["cases"][0]
            chosen[domain] = (model, str(first["id"]), dict(first["inputs"]))
    return list(chosen.values())


def python_answer(model: str, inputs: dict[str, Any]) -> Answer:
    """Ask this environment's Python API."""
    try:
        return pyeconomics.run(model, inputs).to_json().encode("utf-8")
    except Exception as error:  # noqa: BLE001 - every failure is an answer
        made = problem_for(error)
        return (made.slug, made.status, made.detail)


def check_base(base: str) -> str:
    """Return the base URL without a trailing slash, or raise for one not allowed.

    Raises
    ------
    ValueError
        For anything but ``https://`` or ``http://`` to a loopback address, or a
        URL with a path, query, fragment or user information.
    """
    parts = urllib.parse.urlsplit(base)
    host = parts.hostname or ""
    local = False
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    allowed = parts.scheme == "https" or (parts.scheme == "http" and local)
    if not allowed or not host or parts.username or parts.password:
        msg = "the base URL is https://, or http:// to a loopback address"
        raise ValueError(msg)
    if parts.path.strip("/") or parts.query or parts.fragment:
        msg = "the base URL is an origin, with no path, query or fragment"
        raise ValueError(msg)
    return f"{parts.scheme}://{parts.netloc}"


def headers() -> dict[str, str]:
    """Return the headers: JSON, the user agent, and Access's when configured."""
    found = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    values = {name: os.environ.get(name, "").strip() for name in ACCESS}
    if all(values.values()):
        found.update({ACCESS[name]: value for name, value in values.items()})
    return found


def open_url(request: urllib.request.Request) -> tuple[int, dict[str, str], bytes]:
    """Send a request; return the status, headers and body, an error's included."""
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 # nosec B310 - check_base allows https, or http to loopback
            return (
                int(response.status),
                dict(response.headers.items()),
                bytes(response.read()),
            )
    except urllib.error.HTTPError as error:
        return int(error.code), dict(error.headers.items()), bytes(error.read())


def _wait(found: dict[str, str]) -> float:
    text = next((v for k, v in found.items() if k.lower() == "retry-after"), "1")
    return float(min(int(text), LONGEST_WAIT)) if text.isdigit() else 1.0


def deployed_answer(base: str, model: str, body: bytes) -> Answer:
    """Ask the deployed API, retrying a rate limit or a busy server."""
    url = f"{base}/v1/models/{model}/run"
    for attempt in range(ATTEMPTS):
        request = urllib.request.Request(  # noqa: S310 - check_base checked the scheme
            url, data=body, method="POST", headers=headers()
        )
        status, found, content = open_url(request)
        if status in RETRIED and attempt < ATTEMPTS - 1:
            time.sleep(_wait(found))
            continue
        if status == 200:  # noqa: PLR2004 - HTTP OK
            return content
        try:
            problem = json.loads(content)
            slug = str(problem["type"]).removeprefix(TYPE_BASE)
            return (slug, status, str(problem["detail"]))
        except (ValueError, KeyError, TypeError):
            return ("not-a-problem", status, content[:200].decode("utf-8", "replace"))
    msg = "unreachable: the last attempt always answers"
    raise AssertionError(msg)


def _describe(answer: Answer) -> str:
    if isinstance(answer, bytes):
        return f"{len(answer)} bytes"
    slug, status, _ = answer
    return f"{slug} (HTTP {status})"


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def main(argv: list[str]) -> int:
    """Compare the deployed API with the Python API; return 1 on any difference."""
    if len(argv) != 2:  # noqa: PLR2004 - the golden directory and the base URL
        sys.stderr.write("usage: check_deployed.py GOLDEN_DIR BASE_URL\n")
        return 2
    try:
        base = check_base(argv[1])
    except ValueError as error:
        sys.stderr.write(f"check_deployed: {error}\n")
        return 2
    chosen = cases(Path(argv[0]))
    access = "with" if len(headers()) > 2 else "without"  # noqa: PLR2004 - the two plain headers
    _say(f"asking {base} {access} an Access service token")
    differences = 0
    for model, case, inputs in chosen:
        expected = python_answer(model, inputs)
        found = deployed_answer(base, model, canonical_json(inputs))
        same = found == expected
        differences += not same
        _say(
            f"{'same' if same else 'differs':8} {model}::{case}: {_describe(expected)}"
        )
        if not same:
            _say(f"         deployed: {_describe(found)}")
    _say(f"{len(chosen)} cases through {base}, {differences} difference(s)")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
