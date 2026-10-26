# scripts/parity/check_installed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Check the installed wheel's surfaces against its Python API (ci.yml's parity job).

The in-process parity suite (tests/parity/) asks every surface every golden
case; this script asks the surfaces as a user meets them, out of process, from
a clean environment holding only the wheel with its ``server`` and ``mcp``
extras. For the first golden case of each domain (read from tests/golden/ with
``tomllib``), it compares with the Python API's answer, ``pyeconomics.run``:

1. the console script: ``pyeconomics models run ID --inputs -``, its standard
   output with its one newline removed;
2. a real ``pyeconomics serve --workers 2`` (spawned worker processes) over
   HTTP on 127.0.0.1: a run's POST body;
3. ``pyeconomics mcp`` over stdio, through the SDK's client: ``run_model``'s
   text block and the canonical JSON of its structured content.

A case whose run fails (a model whose extra the wheel was installed without)
must fail the same way everywhere: the same problem slug, HTTP status, exit code
and detail. Any difference prints the case and the surface and exits 1.

    python -I scripts/parity/check_installed.py tests/golden .venv/bin/pyeconomics
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess  # nosec B404 # runs the installed console script with fixed arguments
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import anyio
from mcp import Client, StdioServerParameters

import pyeconomics
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.problems import ROWS, TYPE_BASE, problem_for

#: An answer: canonical bytes, or (slug, HTTP status, exit code, detail).
Answer = bytes | tuple[str, int, int, str]

TIMEOUT: Final = 300
_ROW_OF: Final = {row.slug: row for row in ROWS}
_LOCAL: Final = "127.0.0.1"


def _environment() -> dict[str, str]:
    """Return this environment, less what would make the output UTF-8 anyway."""
    return {
        name: value
        for name, value in os.environ.items()
        if name not in {"PYTHONUTF8", "PYTHONIOENCODING"}
    }


def _failed(slug: str, detail: str, *, status: int = -1, exit_code: int = -1) -> Answer:
    row = _ROW_OF.get(slug)
    if row is not None:
        status = row.status if status == -1 else status
        exit_code = row.exit_code if exit_code == -1 else exit_code
    return (slug, status, exit_code, detail)


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
    """Ask the Python API."""
    try:
        return pyeconomics.run(model, inputs).to_json().encode("utf-8")
    except Exception as error:  # noqa: BLE001 - every failure is an answer
        made = problem_for(error)
        return (made.slug, made.status, made.exit_code, made.detail)


def cli_answer(script: str, model: str, body: bytes) -> Answer:
    """Ask the console script, in a process of its own."""
    done = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments, no shell
        [script, "models", "run", model, "--inputs", "-"],
        input=body,
        capture_output=True,
        env=_environment(),
        check=False,
        timeout=TIMEOUT,
    )
    if done.returncode == 0:
        if done.stderr or not done.stdout.endswith(b"\n"):
            return ("unexpected-output", 0, 0, done.stderr.decode("utf-8", "replace"))
        return done.stdout[:-1]
    slug, _, detail = done.stderr.decode("utf-8").removesuffix("\n").partition(": ")
    return _failed(slug, detail, exit_code=done.returncode)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((_LOCAL, 0))
        return int(probe.getsockname()[1])


def _post(url: str, body: bytes) -> tuple[int, bytes]:
    request = urllib.request.Request(  # noqa: S310 - a fixed http://127.0.0.1 URL
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 # nosec B310 - http://127.0.0.1 only
            return int(response.status), bytes(response.read())
    except urllib.error.HTTPError as error:
        return int(error.code), bytes(error.read())


def _wait_until_healthy(base: str, server: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if server.poll() is not None:
            msg = f"pyeconomics serve exited with {server.returncode}"
            raise RuntimeError(msg)
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=5):  # noqa: S310 # nosec B310 - http://127.0.0.1 only
                return
        except OSError:
            time.sleep(1)
    msg = "pyeconomics serve did not answer /healthz"
    raise RuntimeError(msg)


def rest_answers(script: str, runs: list[tuple[str, bytes]]) -> list[Answer]:
    """Ask a real server, with spawned workers, over HTTP."""
    port = _free_port()
    base = f"http://{_LOCAL}:{port}"
    server = subprocess.Popen(  # noqa: S603 # nosec B603 - fixed arguments, no shell
        [script, "serve", "--port", str(port), "--workers", "2"],
        env=_environment(),
        stderr=subprocess.PIPE,
    )
    try:
        _wait_until_healthy(base, server)
        answers: list[Answer] = []
        for model, body in runs:
            status, content = _post(f"{base}/v1/models/{model}/run", body)
            if status == 200:  # noqa: PLR2004 - HTTP OK
                answers.append(content)
                continue
            problem = json.loads(content)
            slug = str(problem["type"]).removeprefix(TYPE_BASE)
            answers.append(_failed(slug, str(problem["detail"]), status=status))
        return answers
    finally:
        # Ctrl+C, as a user stops it; Windows has no SIGINT to send a process.
        if os.name == "nt":
            server.terminate()
        else:
            server.send_signal(signal.SIGINT)
        try:
            _, log = server.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            server.kill()
            _, log = server.communicate()
        sys.stderr.write(log.decode("utf-8", "replace"))


def _doubles(value: object) -> object:
    """Read every JSON number as the double RFC 8785 says it is."""
    if isinstance(value, dict):
        return {key: _doubles(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_doubles(item) for item in value]
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def mcp_answers(
    script: str, runs: list[tuple[str, bytes]]
) -> list[tuple[Answer, Answer]]:
    """``pyeconomics mcp``'s answers over stdio: its text and structured content."""
    params = StdioServerParameters(command=script, args=["mcp"], env=_environment())

    async def main() -> list[tuple[Answer, Answer]]:
        found: list[tuple[Answer, Answer]] = []
        async with Client(params, cache=None) as client:
            for model, body in runs:
                result = await client.call_tool(
                    "run_model", {"model_id": model, "inputs": json.loads(body)}
                )
                block = result.content[0]
                text = block.text if block.type == "text" else ""
                if result.is_error:
                    problem = json.loads(text)
                    slug = str(problem["type"]).removeprefix(TYPE_BASE)
                    failed = _failed(
                        slug, str(problem["detail"]), status=int(problem["status"])
                    )
                    found.append((failed, failed))
                    continue
                structured = canonical_json(_doubles(result.structured_content))
                found.append((text.encode("utf-8"), structured))
        return found

    return anyio.run(main)


def _describe(answer: Answer) -> str:
    if isinstance(answer, bytes):
        return f"{len(answer)} bytes"
    slug, status, exit_code, _ = answer
    return f"{slug} (HTTP {status}, exit {exit_code})"


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def main(argv: list[str]) -> int:
    """Compare every surface with the Python API; return 1 on any difference."""
    if len(argv) != 2:  # noqa: PLR2004 - the golden directory and the script
        sys.stderr.write("usage: check_installed.py GOLDEN_DIR PYECONOMICS_SCRIPT\n")
        return 2
    golden, script = Path(argv[0]), argv[1]
    chosen = cases(golden)
    runs = [(model, canonical_json(inputs)) for model, _, inputs in chosen]
    expected = [python_answer(model, inputs) for model, _, inputs in chosen]
    cli = [cli_answer(script, model, body) for model, body in runs]
    rest = rest_answers(script, runs)
    mcp = mcp_answers(script, runs)
    failures = 0
    for index, (model, case, _) in enumerate(chosen):
        found = {
            "cli": cli[index],
            "rest": rest[index],
            "mcp text": mcp[index][0],
            "mcp structured": mcp[index][1],
        }
        differing = [
            name for name, answer in found.items() if answer != expected[index]
        ]
        verdict = "differs" if differing else "same"
        _say(f"{verdict:8} {model}::{case}: {_describe(expected[index])}")
        for name in differing:
            failures += 1
            _say(f"         {name}: {_describe(found[name])}")
    _say(f"{len(chosen)} cases on 4 surfaces, {failures} difference(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
