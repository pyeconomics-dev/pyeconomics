// web/src/lib/series-request.ts
// How the data explorer reads a series (Phase 5 Step 9; ADR-0013 decision
// 11): GET /v1/series/<concept> on the site's own origin through the generated
// client, with ?start=, ?end= and ?transform= (src/lib/explorer.ts
// seriesQuery), and ?format= for a download, so every file carries its
// attributions and source records as the API writes them. The answer is kept
// as the bytes received, as run-request.ts keeps a run's.
import { client as siteClient } from "@/client/client.gen";
import { seriesPath, seriesQuery, type SeriesOptions } from "@/lib/explorer";
import { filenameOf, type RunAnswer, type RunTransport } from "@/lib/run-request";

/** Where the server says it runs: `hosted` or `library` (GET /version). */
export type ServerMode = "hosted" | "library";

/**
 * Read a concept's series: the answer's bytes, status and download name. A
 * problem answers too, with its status; only a network failure throws.
 */
export async function getSeries(
  conceptId: string,
  options: SeriesOptions = {},
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
  await (transport.client ?? siteClient).get({
    url: seriesPath(conceptId),
    ...(transport.baseUrl === undefined ? {} : { baseUrl: transport.baseUrl }),
    query: seriesQuery(options),
    parseAs: "arrayBuffer",
    fetch: keep,
    throwOnError: false,
  });
  if (received === undefined || bytes === undefined) throw new Error("the request was not sent");
  const retry = received.headers.get("Retry-After");
  return {
    status: received.status,
    ok: received.ok,
    contentType: received.headers.get("Content-Type") ?? "",
    bytes: new Uint8Array(await bytes),
    filename: filenameOf(received.headers.get("Content-Disposition")),
    retryAfter: retry !== null && /^\d+$/.test(retry.trim()) ? Number(retry.trim()) : null,
  };
}

let mode: Promise<ServerMode> | null = null;

/**
 * The mode of the server the site is served by, read once from GET /version;
 * hosted when it cannot be read, so a concept the snapshot does not serve is
 * never fetched by mistake.
 */
export function serverMode(send: typeof fetch = globalThis.fetch): Promise<ServerMode> {
  mode ??= send("/version", { headers: { Accept: "application/json" } })
    .then(async (response) => {
      if (!response.ok) return "hosted" as const;
      const found = ((await response.json()) as { mode?: unknown }).mode;
      return found === "library" ? ("library" as const) : ("hosted" as const);
    })
    .catch(() => "hosted" as const);
  return mode;
}

/** Forget the server's mode (tests). */
export function forgetServerMode(): void {
  mode = null;
}
