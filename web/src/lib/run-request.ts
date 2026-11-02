// web/src/lib/run-request.ts
// How a calculator runs its model (Phase 5 Step 6; ADR-0012 decisions 3, 9
// and 12; ADR-0013 decision 8): the inputs' JSON, posted to
// POST /v1/models/<id>/run on the site's own origin through the generated
// client, with ?format= for a download and ?profile= (and ?as_of=) for live
// data. The answer is kept as the bytes received: the calculator shows and
// downloads them unchanged, and the web parity suite (tests/parity/) sends
// every golden case through this module and compares them with the Python
// API's. A POST run is never cached and carries the user's values only in its
// body: no input reaches the URL, a header or storage.
import { client as siteClient } from "@/client/client.gen";
import type { Client } from "@/client/client";

/** The formats a run answers in (server/formats.py RUN_FORMATS); json is the result itself. */
export const RUN_FORMATS = ["json", "csv", "xlsx", "parquet", "arrow", "bundle"] as const;
export type RunFormat = (typeof RUN_FORMATS)[number];

/** What a run asks for beside its inputs. */
export interface RunOptions {
  /** A download's format; the result's canonical JSON when absent. */
  format?: RunFormat;
  /** Bind this data profile first; the inputs override what it binds. */
  profile?: string;
  /** With a profile: read the data as published on this date (YYYY-MM-DD). */
  asOf?: string;
}

/** A run's answer, as the server sent it. */
export interface RunAnswer {
  status: number;
  ok: boolean;
  contentType: string;
  /** The response body, byte for byte. */
  bytes: Uint8Array;
  /** A download's file name, from Content-Disposition. */
  filename: string | null;
  /** For a 429 or a busy server: the seconds to wait (Retry-After). */
  retryAfter: number | null;
}

/** Where a run goes: the client to send through, and the origin for a test. */
export interface RunTransport {
  client?: Client;
  baseUrl?: string;
  fetch?: typeof fetch;
}

const MODEL_ID = /^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const PROFILE = /^[a-z][a-z0-9_]*$/;

/** A model's run route. */
export function runPath(modelId: string): string {
  if (!MODEL_ID.test(modelId)) throw new Error(`${modelId} is not a model id`);
  return `/v1/models/${modelId}/run`;
}

/** A run's query parameters; none for a plain run of the result. */
export function runQuery(options: RunOptions = {}): Record<string, string> {
  const query: Record<string, string> = {};
  if (options.profile !== undefined) {
    if (!PROFILE.test(options.profile)) throw new Error(`${options.profile} is not a profile name`);
    query.profile = options.profile;
    if (options.asOf) {
      if (!DATE.test(options.asOf)) throw new Error(`${options.asOf} is not a date (YYYY-MM-DD)`);
      query.as_of = options.asOf;
    }
  }
  if (options.format && options.format !== "json") {
    if (!RUN_FORMATS.includes(options.format)) throw new Error(`${String(options.format)} is not a run format`);
    query.format = options.format;
  }
  return query;
}

/** The body a run posts: the inputs' JSON. */
export function runBody(inputs: Readonly<Record<string, unknown>>): string {
  return JSON.stringify(inputs);
}

/** A download's file name from its Content-Disposition, reduced to safe characters. */
export function filenameOf(disposition: string | null): string | null {
  const match = disposition ? /filename="([^"]*)"/.exec(disposition) : null;
  const name = match?.[1]?.replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^[._-]+/, "");
  return name ? name : null;
}

function seconds(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value.trim())) return null;
  return Number(value.trim());
}

/**
 * Run a model: post its inputs, return the answer's bytes, status and
 * download name. A problem answers too, with its status; only a network
 * failure throws.
 */
export async function runModel(
  modelId: string,
  inputs: Readonly<Record<string, unknown>>,
  options: RunOptions = {},
  transport: RunTransport = {},
): Promise<RunAnswer> {
  const send = transport.fetch ?? globalThis.fetch;
  let received: Response | undefined;
  let bytes: Promise<ArrayBuffer> | undefined;
  // The generated client parses what it receives; a clone keeps the bytes.
  const keep: typeof fetch = async (input, init) => {
    received = await send(input, init);
    bytes = received.clone().arrayBuffer();
    return received;
  };
  await (transport.client ?? siteClient).post({
    url: runPath(modelId),
    ...(transport.baseUrl === undefined ? {} : { baseUrl: transport.baseUrl }),
    query: runQuery(options),
    body: inputs,
    bodySerializer: (body: unknown) => runBody(body as Record<string, unknown>),
    headers: { "Content-Type": "application/json" },
    parseAs: "arrayBuffer",
    fetch: keep,
    throwOnError: false,
  });
  if (received === undefined || bytes === undefined) throw new Error("the run was not sent");
  return {
    status: received.status,
    ok: received.ok,
    contentType: received.headers.get("Content-Type") ?? "",
    bytes: new Uint8Array(await bytes),
    filename: filenameOf(received.headers.get("Content-Disposition")),
    retryAfter: seconds(received.headers.get("Retry-After")),
  };
}
