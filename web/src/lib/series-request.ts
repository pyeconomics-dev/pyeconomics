// web/src/lib/series-request.ts
// How the data explorer reads a series (Phase 5 Step 9; ADR-0013 decision
// 11): GET /v1/series/<concept> on the site's own origin through the generated
// client, with ?start=, ?end= and ?transform= (src/lib/explorer.ts
// seriesQuery), and ?format= for a download, so every file carries its
// attributions and source records as the API writes them. The answer is kept
// as the bytes received, as run-request.ts keeps a run's.
import { client as siteClient } from "@/client/client.gen";
import { seriesPath, seriesQuery, type SeriesOptions } from "@/lib/explorer";
import { exchange, type RunAnswer, type RunTransport } from "@/lib/run-request";

/**
 * Where the server says it runs (GET /version's `mode`, server/settings.py
 * MODES): `hosted`, the public service, or `local`, `pyeconomics serve` on
 * the user's machine with every source (ADR-0013 decision 16).
 */
export type ServerMode = "hosted" | "local";

/**
 * Read a concept's series: the answer's bytes, status and download name. A
 * problem answers too, with its status; only a redirect or a network failure
 * throws (run-request.ts `exchange`).
 */
export async function getSeries(
  conceptId: string,
  options: SeriesOptions = {},
  transport: RunTransport = {},
): Promise<RunAnswer> {
  return exchange(transport.fetch ?? globalThis.fetch, (keep) =>
    (transport.client ?? siteClient).get({
      url: seriesPath(conceptId),
      ...(transport.baseUrl === undefined ? {} : { baseUrl: transport.baseUrl }),
      query: seriesQuery(options),
      parseAs: "arrayBuffer",
      redirect: "manual",
      fetch: keep,
      throwOnError: false,
    }),
  );
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
      // Read whatever the status: a body left unread keeps the request open,
      // and a page that holds one never goes quiet on the network.
      const found = ((await response.json()) as { mode?: unknown }).mode;
      return response.ok && found === "local" ? ("local" as const) : ("hosted" as const);
    })
    .catch(() => "hosted" as const);
  return mode;
}

/** Forget the server's mode (tests). */
export function forgetServerMode(): void {
  mode = null;
}
