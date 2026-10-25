# scripts/mcp/inspector_checks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Check the MCP server through the MCP Inspector's CLI (ci.yml's mcp-inspector job).

The Inspector (``@modelcontextprotocol/inspector``, pinned in ``tools/node``)
connects to one server, over stdio or Streamable HTTP, and this script asks it:

1. ``tools/list``: the tools come sorted, ``run_model`` and the data-free
   headline tool ``foundations_time_value`` among them, each with an
   ``outputSchema``;
2. ``tools/call`` of ``foundations_time_value`` on its first example;
3. ``tools/call`` of ``run_model`` on the same model and inputs.

Both calls must succeed and answer the Python API's canonical result as their
first text block and their structured content. Any error, the Inspector's or
the server's, fails the check.

    python scripts/mcp/inspector_checks.py tools/node pyeconomics mcp
    python scripts/mcp/inspector_checks.py tools/node http://127.0.0.1:8765/mcp
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 # runs the pinned Inspector with fixed arguments
import sys
from typing import Any, Final

import pyeconomics

MODEL: Final = "foundations.time_value"
TOOL: Final = "foundations_time_value"
TIMEOUT: Final = 300


def _inputs() -> dict[str, Any]:
    return dict(pyeconomics.registry.get(MODEL).spec.examples[0].inputs)


def _tool_args(arguments: dict[str, Any]) -> list[str]:
    """Return ``--tool-arg`` pairs; the Inspector parses each value as JSON."""
    return [
        f"{name}={value if isinstance(value, str) else json.dumps(value)}"
        for name, value in arguments.items()
    ]


def inspect(node_dir: str, target: list[str], *method: str) -> dict[str, Any]:
    """Run one Inspector CLI call and return its JSON answer.

    Raises
    ------
    RuntimeError
        If the Inspector exits with an error.
    TypeError, ValueError
        If it answers something other than one JSON object.
    """
    npx = shutil.which("npx")
    if npx is None:
        msg = "npx is not on PATH"
        raise RuntimeError(msg)
    command = [npx, "--no-install", "mcp-inspector", "--cli", *target, *method]
    done = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments, no shell
        command,
        cwd=node_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        msg = f"the Inspector exited {done.returncode}: {done.stderr.strip()[-2000:]}"
        raise RuntimeError(msg)
    answer = json.loads(done.stdout)
    if not isinstance(answer, dict):
        msg = "the Inspector's answer is not a JSON object"
        raise TypeError(msg)
    return answer


def check(node_dir: str, target: list[str]) -> list[str]:
    """Run the three checks against one server; return what failed."""
    problems: list[str] = []
    listed = inspect(node_dir, target, "--method", "tools/list")
    tools = listed.get("tools", [])
    names = [tool["name"] for tool in tools]
    if names != sorted(names):
        problems.append("the tools are not sorted by name")
    problems += [
        f"tools/list does not hold {wanted}"
        for wanted in ("run_model", TOOL)
        if wanted not in names
    ]
    problems += [
        f"{tool['name']} has no outputSchema"
        for tool in tools
        if not tool.get("outputSchema")
    ]
    inputs = _inputs()
    expected = pyeconomics.run(MODEL, inputs).to_json()
    calls = {
        TOOL: _tool_args(inputs),
        "run_model": _tool_args({"model_id": MODEL, "inputs": inputs}),
    }
    for name, arguments in calls.items():
        answer = inspect(
            node_dir,
            target,
            "--method",
            "tools/call",
            "--tool-name",
            name,
            "--tool-arg",
            *arguments,
        )
        if answer.get("isError"):
            problems.append(f"{name} answered a tool error: {answer.get('content')}")
            continue
        text = answer["content"][0]["text"]
        if text != expected:
            problems.append(f"{name}'s text is not the Python API's canonical result")
        if answer.get("structuredContent") != json.loads(expected):
            problems.append(f"{name}'s structured content is not the result's object")
    return problems


def main(argv: list[str]) -> int:
    """Check the server ``argv[1:]`` names (a command, or a URL ending in /mcp)."""
    if len(argv) < 2:  # noqa: PLR2004 - the node directory and a target
        sys.stderr.write("usage: inspector_checks.py NODE_DIR (COMMAND... | URL)\n")
        return 2
    node_dir, target = argv[0], argv[1:]
    try:
        problems = check(node_dir, target)
    except (RuntimeError, TypeError, subprocess.TimeoutExpired, ValueError) as error:
        sys.stderr.write(f"mcp-inspector: {error}\n")
        return 1
    for problem in problems:
        sys.stderr.write(f"mcp-inspector: {problem}\n")
    if problems:
        return 1
    print(f"mcp-inspector: {' '.join(target)}: tools/list and both calls passed")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
