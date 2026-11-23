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
 * Why a request got no answer from the API when something in front of the
 * site redirected it, said so a visitor can act on it. The page shows it after
 * "The run could not reach the server:" (or the series').
 */
export const REDIRECTED = "it was redirected, most likely to a sign-in page. Reload the page, sign in if asked, then try again.";

/** Why a request got no answer when the browser could not connect, with the browser's own reason. */
export function unreached(error: unknown): string {
  const said = error instanceof Error && error.message !== "" ? ` (${error.message})` : "";
  return `the browser could not connect${said}. Check the connection, then try again.`;
}

/**
 * Send one request to the API through the generated client and keep its
 * answer as received: a problem answers too, with its status. `call` makes
 * the client's request with the fetch it is given, and with
 * `redirect: "manual"`: no API route redirects, so a redirect comes from
 * something in front of the site, such as Cloudflare Access's sign-in when a
 * session has run out (staging, and production until its cutover, sit behind
 * Access). Followed, it would go to another origin, which `connect-src 'self'`
 * refuses, and the page could say only that the request failed (the
 * 2026-11-23 report on production's Solow page). It throws REDIRECTED for a
 * redirect and `unreached` when the browser could not connect; nothing else
 * throws.
 */
export async function exchange(
  send: typeof fetch,
  call: (keep: typeof fetch) => Promise<unknown>,
): Promise<RunAnswer> {
  let received: Response | undefined;
  let bytes: Promise<ArrayBuffer> | undefined;
  let failure: unknown;
  // The generated client parses what it receives and swallows a failure
  // (throwOnError: false); a clone keeps the bytes, and `failure` the reason.
  const keep: typeof fetch = async (input, init) => {
    try {
      received = await send(input, init);
    } catch (error) {
      failure = error;
      throw error;
    }
    bytes = received.clone().arrayBuffer();
    return received;
  };
  await call(keep);
  if (received === undefined || bytes === undefined) throw new Error(unreached(failure));
  // A browser hands back a manual redirect as an opaque response with status 0;
  // Node's fetch (the parity suite's) hands back the 3xx itself.
  if (received.type === "opaqueredirect" || (received.status >= 300 && received.status < 400)) throw new Error(REDIRECTED);
  return {
    status: received.status,
    ok: received.ok,
    contentType: received.headers.get("Content-Type") ?? "",
    bytes: new Uint8Array(await bytes),
    filename: filenameOf(received.headers.get("Content-Disposition")),
    retryAfter: seconds(received.headers.get("Retry-After")),
  };
}

/**
 * Run a model: post its inputs, return the answer's bytes, status and
 * download name. A problem answers too, with its status; only a redirect or
 * a network failure throws (`exchange`).
 */
export async function runModel(
  modelId: string,
  inputs: Readonly<Record<string, unknown>>,
  options: RunOptions = {},
  transport: RunTransport = {},
): Promise<RunAnswer> {
  return exchange(transport.fetch ?? globalThis.fetch, (keep) =>
    (transport.client ?? siteClient).post({
      url: runPath(modelId),
      ...(transport.baseUrl === undefined ? {} : { baseUrl: transport.baseUrl }),
      query: runQuery(options),
      body: inputs,
      bodySerializer: (body: unknown) => runBody(body as Record<string, unknown>),
      headers: { "Content-Type": "application/json" },
      parseAs: "arrayBuffer",
      redirect: "manual",
      fetch: keep,
      throwOnError: false,
    }),
  );
}
