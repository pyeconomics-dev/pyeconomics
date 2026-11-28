# tests/web/test_mcp_tools_listed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The tools the site lists are the MCP server's (Phase 5 Step 18).

``web/src/lib/mcp.ts`` names the server's discovery tools on the site's page
for AI assistants and gives the command that starts the server. Both are read
from the TypeScript source and held to the library here, so a tool renamed on
one side fails until the other follows.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

WEB: Final = Path(__file__).resolve().parents[2] / "web"
SOURCE: Final = WEB / "src" / "lib" / "mcp.ts"


def test_the_site_lists_the_servers_discovery_tools() -> None:
    from pyeconomics.mcp.tools import DISCOVERY_TOOLS  # noqa: PLC0415

    source = SOURCE.read_text(encoding="utf-8")
    match = re.search(r"export const MCP_TOOLS = (\[[^\]]*\]) as const;", source)
    assert match is not None, "mcp.ts has no MCP_TOOLS"
    assert tuple(ast.literal_eval(match[1])) == DISCOVERY_TOOLS
    # Each tool has its line of words.
    words = source[source.index("MCP_TOOL_WORDS") :]
    for tool in DISCOVERY_TOOLS:
        assert re.search(rf"^\s+{tool}: \"", words, flags=re.MULTILINE), tool


def test_the_sites_command_is_the_documentations() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    page = (WEB.parent / "docs" / "mcp.md").read_text(encoding="utf-8")
    # The page's client configuration, word for word, is what mcp.ts builds
    # for a final release (Phase 5 Step 21): the same arguments in the same
    # order. A pre-release adds `--prerelease allow` in front.
    documented = '["--from", "pyeconomics[mcp]", "pyeconomics", "mcp"]'
    assert documented in page
    assert '["--prerelease", "allow"]' in source
    assert '"--from", "pyeconomics[mcp]", "pyeconomics", "mcp"]' in source
