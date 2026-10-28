# scripts/verify_phase04_live.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Live checks for Phase 4; run explicitly by --live and --post, never CI.

``published <console script>`` runs inside a clean venv holding the published
release: the caller isolates configuration and cache and removes ambient keys,
and keys pass through the credential chain. ``version <sha>`` and ``staging``
run in the project environment against the staging edge, reading the
Cloudflare Access service token from the OS keyring
(``service="pyeconomics"``), and the host and origin from the environment.

Output contains fixed verdicts only; exception text, tokens, credentials and
environment values never reach the verifier's logs.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import subprocess  # nosec B404 # runs the release's own console script, fixed arguments
import sys
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from importlib.metadata import version
from typing import Any, Final

VERSION: Final = "1.0.0b1"
RUN_PATH: Final = "/v1/models/foundations.time_value/run"
RUN_BODY: Final = (
    b'{"calculation":"future_value","present_value":1000.0,"rate":0.05,"periods":10}'
)
RUN_INPUTS: Final = {
    "calculation": "future_value",
    "present_value": 1000.0,
    "rate": 0.05,
    "periods": 10,
}
AGENT: Final = {"User-Agent": "pyeconomics-verify/1.0"}
# Cloudflare Access refuses a request without the token by redirecting or denying it.
REFUSED: Final = {302, 303, 401, 403}
# The application's limiter allows 30 series requests a minute; Cloudflare's
# rule allows 50 requests in 10 seconds (Phase 4 Step 13).
SERIES_BURST: Final = 40
EDGE_BURST: Final = 100
CLOUDFLARE_WINDOW: Final = 12.0


def published(cli: str) -> int:  # noqa: PLR0911 # each independent invariant fails closed
    """Check the published release: its version, CLI bytes and keyless data."""
    from pyeconomics import data, run  # noqa: PLC0415 # the clean venv's release
    from pyeconomics.data import cache  # noqa: PLC0415
    from pyeconomics.data.credentials import has_key, withheld  # noqa: PLC0415

    if version("pyeconomics") != VERSION:
        return 1
    if any(name.endswith("_API_KEY") for name in os.environ):
        return 1
    answer = subprocess.run(  # noqa: S603 # nosec B603 # the release's console script
        [cli, "--version"], capture_output=True, text=True, check=True
    )
    if answer.stdout.strip() != f"pyeconomics {VERSION}":
        return 1
    printed = subprocess.run(  # noqa: S603 # nosec B603
        [
            cli,
            "models",
            "run",
            "foundations.time_value",
            "--calculation",
            "future_value",
            "--present-value",
            "1000",
            "--rate",
            "0.05",
            "--periods",
            "10",
        ],
        capture_output=True,
        check=True,
    ).stdout.replace(b"\r\n", b"\n")
    if printed != run("foundations.time_value", RUN_INPUTS).to_json().encode() + b"\n":
        return 1
    start, end = dt.date(2024, 1, 1), dt.date(2024, 12, 31)
    months = 12
    with cache.bypass(), withheld("fred"):
        if has_key("fred"):
            return 1
        found = data.get("bls:CUUR0000SA0", start=start, end=end)
        if len(found.frame.index) != months or found.sources[0].provider != "bls":
            return 1
    shown = subprocess.run(  # noqa: S603 # nosec B603
        [
            cli,
            "data",
            "get",
            "bls:CUUR0000SA0",
            "--start",
            "2024-01-01",
            "--end",
            "2024-12-31",
        ],
        capture_output=True,
        check=False,
    )
    if shown.returncode != 0:
        return 1
    sys.stdout.write(
        json.dumps({"console_script": "PASS", "bls_keyless": "PASS"}) + "\n"
    )
    return 0


def _token() -> dict[str, str]:
    import keyring  # noqa: PLC0415 # the project environment's keyring extra

    names = ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET")
    values = [keyring.get_password("pyeconomics", name) for name in names]
    if not all(values):
        msg = "the service token is not in the keyring"
        raise LookupError(msg)
    return {
        "CF-Access-Client-Id": str(values[0]),
        "CF-Access-Client-Secret": str(values[1]),
        **AGENT,
    }


def _call(
    url: str, headers: dict[str, str], body: bytes | None = None
) -> tuple[int, dict[str, str], bytes]:
    if body is not None:
        headers = {**headers, "Content-Type": "application/json"}
    request = urllib.request.Request(url, data=body, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310 # nosec B310
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers.items()), error.read()


def _edge() -> str:
    return "https://" + os.environ["STAGING_HOST"].strip()


def deployed(sha: str) -> int:
    """Check that staging, through the edge, reports ``sha`` in hosted mode."""
    status, _, body = _call(_edge() + "/version", _token())
    found = json.loads(body) if status == HTTPStatus.OK else {}
    if found.get("git_sha") != sha or found.get("mode") != "hosted":
        return 1
    sys.stdout.write(json.dumps({"deployed_sha": "PASS"}) + "\n")
    return 0


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_: object) -> None:
        return None


def _refusals(edge: str, origin: str) -> bool:
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(
            urllib.request.Request(edge + "/version", headers=AGENT),  # noqa: S310
            timeout=30,
        ) as response:
            unauthenticated = response.status
    except urllib.error.HTTPError as error:
        unauthenticated = error.code
    status, _, body = _call(origin + "/v1/models", AGENT)
    origin_refused = status == HTTPStatus.FORBIDDEN and json.loads(body)[
        "type"
    ].endswith("/problems/edge-required")
    status, _, body = _call(origin + "/version", AGENT)
    return (
        unauthenticated in REFUSED
        and origin_refused
        and status == HTTPStatus.OK
        and json.loads(body).get("mode") == "hosted"
    )


async def _burst(url: str, headers: dict[str, str], count: int) -> list[Any]:
    import httpx2  # noqa: PLC0415 # the project environment's HTTP client

    limits = httpx2.Limits(max_connections=count, max_keepalive_connections=count)
    async with httpx2.AsyncClient(headers=headers, timeout=30, limits=limits) as client:
        await client.get(url)  # warm the connection pool's first connection
        return list(await asyncio.gather(*(client.get(url) for _ in range(count))))


def _rate_limits(edge: str, headers: dict[str, str]) -> bool:
    series = edge + "/v1/series/treasury:debt?start=2025-01-01&end=2025-01-31"
    answers = asyncio.run(_burst(series, headers, SERIES_BURST))
    application = [r for r in answers if r.status_code == HTTPStatus.TOO_MANY_REQUESTS]
    if not application or not all(r.headers.get("Retry-After") for r in application):
        return False
    time.sleep(CLOUDFLARE_WINDOW)
    answers = asyncio.run(_burst(edge + "/version", headers, EDGE_BURST))
    return any(r.status_code == HTTPStatus.TOO_MANY_REQUESTS for r in answers)


def staging() -> int:  # noqa: PLR0911 # each independent live invariant fails closed
    """Check the staging edge, its origin's refusals and both rate limits."""
    from pyeconomics import run  # noqa: PLC0415

    edge, origin = _edge(), os.environ["ORIGIN_URL"].strip().rstrip("/")
    headers = _token()
    status, _, body = _call(edge + "/healthz", headers)
    if status != HTTPStatus.OK or json.loads(body) != {"status": "ok"}:
        return 1
    status, _, body = _call(edge + RUN_PATH, headers, RUN_BODY)
    if status != HTTPStatus.OK:
        return 1
    # The manifest records the interpreter's dependencies; the result and
    # input digests, which never cover it, must equal the Python API's.
    remote, local = (
        json.loads(body),
        json.loads(run("foundations.time_value", RUN_INPUTS).to_json()),
    )
    for key in ("result_sha256", "inputs_sha256"):
        if remote["manifest"][key] != local["manifest"][key]:
            return 1
    if remote["outputs"] != local["outputs"]:
        return 1
    status, _, body = _call(
        edge + "/v1/series/treasury:debt?start=2025-01-01&end=2025-01-31", headers
    )
    series = json.loads(body) if status == HTTPStatus.OK else {}
    if (
        not series
        or series["sources"][0]["licence"] != "hosted-safe"
        or not series["attributions"]
    ):
        return 1
    status, _, body = _call(edge + "/v1/series/fred:UNRATE", headers)
    if status != HTTPStatus.FORBIDDEN or not json.loads(body)["type"].endswith(
        "/problems/licence-refused"
    ):
        return 1
    if not _refusals(edge, origin):
        return 1
    if not _rate_limits(edge, headers):
        return 1
    sys.stdout.write(
        json.dumps({"edge": "PASS", "refusals": "PASS", "rate_limits": "PASS"}) + "\n"
    )
    return 0


def main(argv: list[str]) -> int:
    """Dispatch ``published <cli>``, ``version <sha>`` or ``staging``."""
    match argv:
        case ["published", cli]:
            return published(cli)
        case ["version", sha]:
            return deployed(sha)
        case ["staging"]:
            return staging()
    sys.stderr.write(
        "usage: verify_phase04_live.py published CLI | version SHA | staging\n"
    )
    return 2


if __name__ == "__main__":
    try:
        status = main(sys.argv[1:])
    except Exception:  # noqa: BLE001  # external failures must not disclose token/URL text
        sys.stderr.write("Live check failed; inspect the service safely.\n")
        status = 1
    raise SystemExit(status)
