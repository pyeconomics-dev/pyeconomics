// web/src/lib/mcp.ts
// What the site says about the MCP server (Phase 5 Step 18's round 2: two
// rounds of developers found a tool's name and a start command, and no word on
// connecting an assistant): the server's discovery tools, the configuration a
// client reads and the hosted endpoint. The tools' names are the server's own
// (src/pyeconomics/mcp/tools.py DISCOVERY_TOOLS), held equal by
// tests/web/test_mcp_tools_listed.py; the configuration is the one the
// documentation's MCP page gives.
import { jsonText } from "@/lib/json-text";
import { ORIGIN } from "@/lib/paths";

/** The server's five discovery tools, in the server's order. */
export const MCP_TOOLS = ["search_models", "describe_model", "run_model", "get_series", "list_sources"] as const;

export type McpTool = (typeof MCP_TOOLS)[number];

/** What each discovery tool does, as a phrase with no full stop. */
export const MCP_TOOL_WORDS: Readonly<Record<McpTool, string>> = {
  search_models: "finds models by a word, or lists a domain's",
  describe_model: "gives a model's inputs and outputs with their units, and its model card",
  run_model: "runs any model by its id, on the inputs given or on live data",
  get_series: "reads a data series, with its source and the attribution it must be shown with",
  list_sources: "lists every data source with its licence class and terms",
};

/** The hosted server's endpoint, for a client that connects to a URL. */
export const MCP_ENDPOINT = `${ORIGIN}/mcp`;

/** Whether a version is a pre-release, which `uvx` installs only when told to. */
export function prerelease(version: string): boolean {
  return /(a|b|rc|dev)\d/.test(version);
}

/** The words `uvx` takes to start the server: the documentation's command. */
export function mcpArguments(version: string): string[] {
  return [...(prerelease(version) ? ["--prerelease", "allow"] : []), "--from", "pyeconomics[mcp]", "pyeconomics", "mcp"];
}

/** The start command as a shell line. */
export function mcpCommand(version: string): string {
  return ["uvx", ...mcpArguments(version).map((word) => (/^[A-Za-z0-9_./=-]+$/.test(word) ? word : `"${word}"`))].join(" ");
}

/** The entry a client's JSON configuration file takes (Claude Desktop's shape, which others share). */
export function mcpClientConfig(version: string): string {
  return jsonText({ mcpServers: { pyeconomics: { command: "uvx", args: mcpArguments(version) } } });
}
