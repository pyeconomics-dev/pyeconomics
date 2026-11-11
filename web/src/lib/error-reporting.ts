// web/src/lib/error-reporting.ts
// Browser error reporting for the calculator and explorer islands (Phase 5
// Step 14; ADR-0013 decision 15). Only those islands import this module, and
// it loads the SDK's few functions it uses (src/lib/sentry-client.ts) on the
// first report, so no page carries Sentry's code until an island meets an
// error it did not expect. Only a production
// build carries a DSN (csp.config.ts sentryBuild, which also adds the DSN's
// ingest origin to connect-src); everywhere else report() does nothing.
//
// The SDK starts with no default integration: no global error handler, no
// breadcrumb, no session, no replay and no tracing. Every dataCollection
// category is off, so it collects no user detail, address, cookie, header,
// body or query (SDK 11 collects them unless told not to). beforeSend
// (cleanEvent) keeps what an issue needs and nothing a visitor typed: each
// exception's type and frames, its message withheld, because a parse error
// quotes the text it failed on and that text can hold a run's inputs; every URL
// without its query or fragment; the island's name and the release.
import type { BrowserOptions, ErrorEvent } from "@sentry/browser";

/** The integrations the SDK starts with: a list, never a function. */
type Integrations = Extract<NonNullable<BrowserOptions["integrations"]>, readonly unknown[]>;

/** An island that reports its errors. */
export type Island = "calculator" | "explorer";

/** What an exception's message becomes in an error event. */
export const WITHHELD = "(withheld: pyeconomics never reports an unexpected error's message)";

/** Every dataCollection category, off (SDK 11's option; ADR-0013 decision 15). */
export const DATA_COLLECTION = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
  graphQL: { document: false, variables: false },
  genAI: { inputs: false, outputs: false },
  mcp: { inputs: false, outputs: false },
  databaseQueryData: false,
  queues: false,
  stackFrameVariables: false,
  frameContextLines: 0,
} as const satisfies NonNullable<BrowserOptions["dataCollection"]>;

/** Drop a URL's query and fragment; anything that is not a URL is kept whole. */
export function withoutQuery(url: string): string {
  const cut = url.search(/[?#]/);
  return cut === -1 ? url : url.slice(0, cut);
}

type Frame = NonNullable<NonNullable<NonNullable<ErrorEvent["exception"]>["values"]>[number]["stacktrace"]>["frames"];

function frames(given: Frame): Frame {
  return (given ?? []).map((frame) => ({
    ...(typeof frame.filename === "string" ? { filename: withoutQuery(frame.filename) } : {}),
    ...(typeof frame.abs_path === "string" ? { abs_path: withoutQuery(frame.abs_path) } : {}),
    ...(typeof frame.function === "string" ? { function: frame.function } : {}),
    ...(typeof frame.lineno === "number" ? { lineno: frame.lineno } : {}),
    ...(typeof frame.colno === "number" ? { colno: frame.colno } : {}),
    ...(typeof frame.in_app === "boolean" ? { in_app: frame.in_app } : {}),
  }));
}

/**
 * Rebuild an error event from an allowlist: its id, time, level, platform,
 * release and environment; each exception's type, mechanism and frames, the
 * message withheld; the island tag; and the page's URL without its query.
 * A user, a request's headers or body, extra data, contexts and breadcrumbs
 * never leave the browser.
 */
export function cleanEvent(event: ErrorEvent, location?: string): ErrorEvent {
  const kept: ErrorEvent = { type: undefined };
  if (event.event_id) kept.event_id = event.event_id;
  if (event.timestamp !== undefined) kept.timestamp = event.timestamp;
  if (event.level) kept.level = event.level;
  if (event.platform) kept.platform = event.platform;
  if (event.release) kept.release = event.release;
  if (event.environment) kept.environment = event.environment;
  if (event.sdk?.name) kept.sdk = { name: event.sdk.name, version: event.sdk.version ?? "" };
  const island = event.tags?.island;
  if (island === "calculator" || island === "explorer") kept.tags = { island };
  const values = event.exception?.values ?? [];
  if (values.length > 0) {
    kept.exception = {
      values: values.map((value) => ({
        ...(value.type ? { type: value.type } : {}),
        value: WITHHELD,
        ...(value.mechanism ? { mechanism: { type: value.mechanism.type, handled: value.mechanism.handled } } : {}),
        ...(value.stacktrace ? { stacktrace: { frames: frames(value.stacktrace.frames) } } : {}),
      })),
    };
  }
  const page = location ?? event.request?.url;
  if (typeof page === "string") kept.request = { url: withoutQuery(page) };
  return kept;
}

/** The SDK's options: production, no default integration, nothing collected. */
export function sentryOptions(dsn: string, release: string, integrations: Integrations): BrowserOptions {
  return {
    dsn,
    ...(release ? { release } : {}),
    environment: "production",
    defaultIntegrations: false,
    integrations,
    dataCollection: DATA_COLLECTION,
    sendClientReports: false,
    maxBreadcrumbs: 0,
    beforeBreadcrumb: () => null,
    beforeSend: (event) => cleanEvent(event, globalThis.location?.href),
  };
}

type Sentry = typeof import("./sentry-client");

let started: Promise<Sentry> | null = null;

/** Start the SDK once; the islands' first report does it. */
async function start(dsn: string, release: string): Promise<Sentry> {
  const sentry = await import("./sentry-client");
  sentry.init(sentryOptions(dsn, release, [sentry.linkedErrorsIntegration(), sentry.dedupeIntegration()]));
  return sentry;
}

/**
 * Report an error an island did not expect: one that stopped it loading,
 * rendering, drawing a chart or reading the server's answer. A failed request
 * or a problem the server answered is expected, and never reported. Reporting
 * never throws.
 */
export async function report(
  error: unknown,
  island: Island,
  dsn: string = import.meta.env.PUBLIC_SENTRY_DSN ?? "",
  release: string = import.meta.env.PUBLIC_SENTRY_RELEASE ?? "",
): Promise<void> {
  if (dsn === "") return;
  try {
    started ??= start(dsn, release);
    const sentry = await started;
    sentry.captureException(error instanceof Error ? error : new Error("a value that is not an Error was thrown"), {
      tags: { island },
    });
  } catch {
    // An error tracker that fails stays silent: the island has already
    // shown the visitor what went wrong.
  }
}
