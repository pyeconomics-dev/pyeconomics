// web/tests/unit/mcp.test.ts
// What the site says about the MCP server (src/lib/mcp.ts, Phase 5 Step 18's
// round 2): the discovery tools each have their words, the start command is
// the documentation's, and the client configuration is JSON a client can read.
// tests/web/test_mcp_tools_listed.py holds the tools' names to the server's.
import { describe, expect, it } from "vitest";

import { MCP_ENDPOINT, MCP_TOOLS, MCP_TOOL_WORDS, mcpArguments, mcpClientConfig, mcpCommand, prerelease } from "@/lib/mcp";

describe("the MCP server as the site describes it", () => {
  it("gives every discovery tool its words, in the server's order", () => {
    expect(Object.keys(MCP_TOOL_WORDS)).toEqual([...MCP_TOOLS]);
    for (const words of Object.values(MCP_TOOL_WORDS)) {
      // A phrase with no full stop, which addresses no one.
      expect(words).toMatch(/^[a-z].*[^.]$/);
      expect(words).not.toMatch(/\byou\b/i);
    }
  });

  it("starts the server as the documentation does, a pre-release with its flag", () => {
    expect(prerelease("1.0.0rc1.dev1")).toBe(true);
    expect(prerelease("1.0.0")).toBe(false);
    expect(mcpCommand("1.0.0rc1.dev1")).toBe('uvx --prerelease allow --from "pyeconomics[mcp]" pyeconomics mcp');
    expect(mcpCommand("1.0.0")).toBe('uvx --from "pyeconomics[mcp]" pyeconomics mcp');
  });

  it("writes a configuration a client can read, with the same command", () => {
    for (const version of ["1.0.0rc1.dev1", "1.0.0"]) {
      const parsed = JSON.parse(mcpClientConfig(version)) as { mcpServers: Record<string, { command: string; args: string[] }> };
      expect(Object.keys(parsed.mcpServers)).toEqual(["pyeconomics"]);
      expect(parsed.mcpServers.pyeconomics).toEqual({ command: "uvx", args: mcpArguments(version) });
    }
    // No key, token or address but the public endpoint.
    expect(mcpClientConfig("1.0.0")).not.toMatch(/key|token|secret|https?:/i);
    expect(MCP_ENDPOINT).toBe("https://pyeconomics.dev/mcp");
  });
});
