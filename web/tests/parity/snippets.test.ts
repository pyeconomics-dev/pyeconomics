// web/tests/parity/snippets.test.ts
// Each snippet kind the calculators offer (src/lib/snippets.ts), run for one
// model per domain, the first golden case of each, and held to the Python
// API's bytes from golden.json: the Python snippet and the command line's in
// the locked environment, curl against the suite's local `pyeconomics serve`
// (the snippet's origin swapped for it), and the MCP call through the
// in-memory client (scripts/web/mcp_snippet.py).
import { execFile } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

import { describe, expect, inject, it } from "vitest";

import { cliSnippet, curlSnippet, mcpCall, pythonSnippet } from "@/lib/snippets";

const WEB = fileURLToPath(new URL("../..", import.meta.url));
const run = promisify(execFile);

interface GoldenCase {
  model: string;
  case: string;
  inputs: Record<string, unknown>;
  status: number;
  body: string;
}

const golden = JSON.parse(
  readFileSync(new URL("../../src/data/generated/golden.json", import.meta.url), "utf8"),
) as { cases: GoldenCase[] };

const domain = (entry: GoldenCase): string => entry.model.split(".")[0] ?? "";

/** The first golden case of each domain, in golden.json's order. */
const first: GoldenCase[] = [];
for (const entry of golden.cases) if (!first.some((other) => domain(other) === domain(entry))) first.push(entry);

/** Run a command in the locked environment with every extra, feeding it standard input. */
async function locked(args: string[], input: string): Promise<string> {
  const child = run("uv", ["run", "--project", "..", "--locked", "--all-extras", ...args], {
    cwd: WEB,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  child.child.stdin?.end(input);
  return (await child).stdout;
}

describe("the snippets, one model per domain", () => {
  it("cover every domain", () => {
    expect(new Set(golden.cases.map(domain)).size).toBe(first.length);
    expect(first.length).toBeGreaterThanOrEqual(13);
  });

  for (const entry of first) {
    const snippet = { modelId: entry.model, inputs: entry.inputs };

    it.concurrent(`Python: ${entry.model}`, async () => {
      // print() ends the line as the platform does: \r\n on Windows.
      const printed = await locked(["python", "-X", "utf8", "-I", "-"], pythonSnippet(snippet));
      expect(printed.replace(/\r?\n$/, "")).toBe(entry.body);
    });

    it.concurrent(`command line: ${entry.model}`, async () => {
      expect(await locked(["bash", "-s"], cliSnippet(snippet))).toBe(`${entry.body}\n`);
    });

    it.concurrent(`curl: ${entry.model}`, async () => {
      expect(await locked(["bash", "-s"], curlSnippet(snippet, inject("api")))).toBe(entry.body);
    });
  }

  it("MCP: every domain's run_model call through the in-memory client", async () => {
    const calls = first.map((entry) => mcpCall({ modelId: entry.model, inputs: entry.inputs }));
    const answers = JSON.parse(await locked(["python", "../scripts/web/mcp_snippet.py"], JSON.stringify(calls))) as unknown[];
    expect(answers).toEqual(first.map((entry) => entry.body));
  });
});
