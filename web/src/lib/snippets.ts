// web/src/lib/snippets.ts
// "Copy as Python, CLI, curl and MCP" (Phase 5 Step 6; ADR-0013 decision 8):
// the run a calculator would make, written for each other surface from the
// same inputs and data options. Each names only the public endpoint and the
// user's own inputs: never a key, a cookie or a header from the page. CI runs
// every kind for one model per domain and requires the Python API's bytes
// (tests/parity/snippets.test.ts).
import { runPath, type RunOptions } from "@/lib/run-request";

/** The production origin a curl snippet names. */
export const API_ORIGIN = "https://pyeconomics.dev";

/** The snippet kinds, in the order the calculator shows them. */
export const SNIPPET_KINDS = ["python", "cli", "curl", "mcp"] as const;
export type SnippetKind = (typeof SNIPPET_KINDS)[number];

/** What a snippet runs: a model, its inputs and, for live data, a profile and date. */
export interface SnippetRun {
  modelId: string;
  inputs: Readonly<Record<string, unknown>>;
  options?: Pick<RunOptions, "profile" | "asOf">;
}

const INDENT = "    ";

/** A JSON value as a Python literal: True, False and None for JSON's words. */
export function pythonLiteral(value: unknown, depth = 0): string {
  const pad = INDENT.repeat(depth + 1);
  const end = INDENT.repeat(depth);
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("a run's inputs hold no NaN or infinity");
    return JSON.stringify(value);
  }
  // A JSON string's escapes are all valid in a Python string literal.
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    if (value.every((item) => typeof item !== "object" || item === null)) {
      return `[${value.map((item) => pythonLiteral(item)).join(", ")}]`;
    }
    return `[\n${value.map((item) => `${pad}${pythonLiteral(item, depth + 1)},`).join("\n")}\n${end}]`;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(([, item]) => item !== undefined);
    if (entries.length === 0) return "{}";
    const lines = entries.map(([key, item]) => `${pad}${JSON.stringify(key)}: ${pythonLiteral(item, depth + 1)},`);
    return `{\n${lines.join("\n")}\n${end}}`;
  }
  throw new Error(`${typeof value} is not a JSON value`);
}

/** The inputs as the JSON a request carries, indented for reading. */
export function inputsJson(inputs: Readonly<Record<string, unknown>>): string {
  return JSON.stringify(inputs, null, 2);
}

/** A shell word, single-quoted unless it needs no quoting. */
function shellWord(word: string): string {
  return /^[A-Za-z0-9_./:=@-]+$/.test(word) ? word : `'${word.replaceAll("'", "'\\''")}'`;
}

function heredoc(json: string): string {
  // The terminator never appears in JSON text, which escapes no letters.
  return `<<'JSON'\n${json}\nJSON`;
}

function dateCall(date: string): string {
  const [year = "", month = "", day = ""] = date.split("-");
  return `dt.date(${Number(year)}, ${Number(month)}, ${Number(day)})`;
}

/** `pyeconomics.run`, after `pyeconomics.bind` for live data. */
export function pythonSnippet({ modelId, inputs, options = {} }: SnippetRun): string {
  const id = JSON.stringify(modelId);
  const literal = pythonLiteral(inputs);
  if (options.profile === undefined) {
    return [
      "import pyeconomics",
      "",
      `inputs = ${literal}`,
      `result = pyeconomics.run(${id}, inputs)`,
      "print(result.to_json())",
      "",
    ].join("\n");
  }
  const asOf = options.asOf ? `, as_of=${dateCall(options.asOf)}` : "";
  return [
    ...(options.asOf ? ["import datetime as dt", ""] : []),
    "import pyeconomics",
    "",
    `inputs = ${literal}`,
    `bound = pyeconomics.bind(${id}, profile=${JSON.stringify(options.profile)}${asOf}, **inputs)`,
    `result = pyeconomics.run(${id}, bound)`,
    "print(result.to_json())",
    "",
  ].join("\n");
}

/** `pyeconomics models run <id> --inputs -`, the inputs' JSON on standard input. */
export function cliSnippet({ modelId, inputs, options = {} }: SnippetRun): string {
  const words = ["pyeconomics", "models", "run", modelId];
  if (options.profile !== undefined) {
    words.push("--profile", options.profile);
    if (options.asOf) words.push("--as-of", options.asOf);
  }
  words.push("--inputs", "-");
  return `${words.map(shellWord).join(" ")} ${heredoc(inputsJson(inputs))}\n`;
}

/** The run route on an origin (the production API by default), with curl. */
export function curlSnippet({ modelId, inputs, options = {} }: SnippetRun, origin = API_ORIGIN): string {
  const query = new URLSearchParams();
  if (options.profile !== undefined) {
    query.set("profile", options.profile);
    if (options.asOf) query.set("as_of", options.asOf);
  }
  const search = query.size > 0 ? `?${query.toString()}` : "";
  const url = `${origin}${runPath(modelId)}${search}`;
  return [
    `curl --fail-with-body --silent --show-error -X POST ${shellWord(url)} \\`,
    `  -H 'Content-Type: application/json' \\`,
    `  --data-binary @- ${heredoc(inputsJson(inputs))}`,
    "",
  ].join("\n");
}

/** The MCP server's run_model call: its name and arguments. */
export function mcpCall({ modelId, inputs, options = {} }: SnippetRun): Record<string, unknown> {
  const args: Record<string, unknown> = { model_id: modelId, inputs };
  if (options.profile !== undefined) {
    args.profile = options.profile;
    if (options.asOf) args.as_of = options.asOf;
  }
  return { name: "run_model", arguments: args };
}

/** The MCP call as the JSON a client sends in tools/call's params. */
export function mcpSnippet(run: SnippetRun): string {
  return `${JSON.stringify(mcpCall(run), null, 2)}\n`;
}

/** Every snippet of a run, by kind. */
export function snippets(run: SnippetRun, origin = API_ORIGIN): Record<SnippetKind, string> {
  return {
    python: pythonSnippet(run),
    cli: cliSnippet(run),
    curl: curlSnippet(run, origin),
    mcp: mcpSnippet(run),
  };
}
