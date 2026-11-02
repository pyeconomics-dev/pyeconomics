# scripts/web/mcp_snippet.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Run the calculators' MCP snippets through the in-memory client (Phase 5 Step 6).

A calculator's MCP snippet is a ``tools/call`` request's params: a tool name
and its arguments (``web/src/lib/snippets.ts``). The web parity suite
(``web/tests/parity/snippets.test.ts``) hands this script a JSON array of them
on standard input; it calls each on the MCP server
(:func:`pyeconomics.mcp.build_server`) through the SDK's client connected in
memory, as the MCP tests do, and writes a JSON array of each call's text block,
the result's canonical JSON, to standard output. A call that answers an error
gives ``{"error": <its text>}``. It needs the ``mcp`` extra.

    uv run --locked --all-extras python scripts/web/mcp_snippet.py < calls.json
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

import anyio
from mcp import Client

from pyeconomics.mcp import build_server

if TYPE_CHECKING:
    from collections.abc import Sequence


async def call_all(calls: Sequence[dict[str, Any]]) -> list[object]:
    """Each call's text block, or its error's, in order."""
    answers: list[object] = []
    async with Client(build_server(), raise_exceptions=False) as client:
        for call in calls:
            result = await client.call_tool(call["name"], call["arguments"])
            block = result.content[0]
            text = block.text if block.type == "text" else ""
            answers.append({"error": text} if result.is_error else text)
    return answers


def main() -> int:
    """Read the calls from standard input and write their answers; return 0."""
    calls = json.loads(sys.stdin.buffer.read())
    answers = anyio.run(call_all, calls)
    sys.stdout.buffer.write(json.dumps(answers, ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
