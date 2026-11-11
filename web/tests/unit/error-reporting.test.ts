// web/tests/unit/error-reporting.test.ts
// The islands' browser error reporting (src/lib/error-reporting.ts; Phase 5
// Step 14, ADR-0013 decision 15): the SDK starts with every dataCollection
// category off, no default integration, no replay or tracing, and an
// allowlist that withholds every message and strips every URL's query. Without
// a DSN, as in every build but production's, nothing loads at all.
import type { ErrorEvent } from "@sentry/browser";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DATA_COLLECTION,
  WITHHELD,
  cleanEvent,
  report,
  sentryOptions,
  withoutQuery,
} from "../../src/lib/error-reporting";

const sentry = vi.hoisted(() => ({
  init: vi.fn(),
  captureException: vi.fn(),
  linkedErrorsIntegration: vi.fn(() => ({ name: "LinkedErrors" })),
  dedupeIntegration: vi.fn(() => ({ name: "Dedupe" })),
}));

vi.mock("../../src/lib/sentry-client", () => sentry);

const DSN = "https://0123456789abcdef0123456789abcdef@o42.ingest.us.sentry.io/7";

describe("the SDK's options", () => {
  it("turns every dataCollection category off", () => {
    expect(DATA_COLLECTION).toEqual({
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
    });
  });

  it("starts no default integration, replay, tracing or breadcrumb", () => {
    const options = sentryOptions(DSN, "pyeconomics@1.0.0+abc", []);
    expect(options.dataCollection).toBe(DATA_COLLECTION);
    expect(options.defaultIntegrations).toBe(false);
    expect(options.integrations).toEqual([]);
    expect(options.sendClientReports).toBe(false);
    expect(options.maxBreadcrumbs).toBe(0);
    expect(options.beforeBreadcrumb?.({ message: "x" }, undefined)).toBeNull();
    for (const key of ["tracesSampleRate", "tracesSampler", "replaysSessionSampleRate", "replaysOnErrorSampleRate", "sendDefaultPii"]) {
      expect(options).not.toHaveProperty(key);
    }
    expect(options.environment).toBe("production");
    expect(options.release).toBe("pyeconomics@1.0.0+abc");
    expect(sentryOptions(DSN, "", [])).not.toHaveProperty("release");
  });
});

describe("cleanEvent", () => {
  it("keeps an allowlist, withholds messages and strips queries", () => {
    const address = "198.51.100.7";
    const event = {
      type: undefined,
      event_id: "e1",
      timestamp: 1,
      level: "error",
      platform: "javascript",
      release: "r",
      environment: "production",
      sdk: { name: "sentry.javascript.browser", version: "11.10.0", integrations: ["x"] },
      tags: { island: "calculator", input: address },
      user: { ip_address: address },
      extra: { inputs: address },
      contexts: { trace: { trace_id: "0" } },
      breadcrumbs: [{ message: address }],
      request: { url: `https://pyeconomics.dev/models/x/?q=${address}`, headers: { Cookie: address } },
      exception: {
        values: [
          {
            type: "SyntaxError",
            value: `Unexpected token in JSON: {"rate": ${address}}`,
            mechanism: { type: "generic", handled: true, data: { address } },
            stacktrace: {
              frames: [
                {
                  filename: `https://pyeconomics.dev/_astro/form.js?v=${address}#x`,
                  function: "run",
                  lineno: 3,
                  colno: 9,
                  in_app: true,
                  vars: { inputs: address },
                  context_line: address,
                },
              ],
            },
          },
        ],
      },
    } as unknown as ErrorEvent;
    const cleaned = cleanEvent(event, `https://pyeconomics.dev/models/x/?rate=${address}#top`);
    expect(JSON.stringify(cleaned)).not.toContain(address);
    expect(cleaned.request).toEqual({ url: "https://pyeconomics.dev/models/x/" });
    expect(cleaned.tags).toEqual({ island: "calculator" });
    expect(cleaned.sdk).toEqual({ name: "sentry.javascript.browser", version: "11.10.0" });
    const value = cleaned.exception?.values?.[0];
    expect(value?.value).toBe(WITHHELD);
    expect(value?.mechanism).toEqual({ type: "generic", handled: true });
    expect(value?.stacktrace?.frames).toEqual([
      { filename: "https://pyeconomics.dev/_astro/form.js", function: "run", lineno: 3, colno: 9, in_app: true },
    ]);
    for (const key of ["user", "extra", "contexts", "breadcrumbs"]) expect(cleaned).not.toHaveProperty(key);
  });

  it("keeps an event without exceptions, tags or a page as just its facts", () => {
    const cleaned = cleanEvent({ type: undefined, level: "error", tags: { island: "elsewhere" } });
    expect(cleaned).toEqual({ type: undefined, level: "error" });
  });

  it("drops a URL's query and fragment and keeps anything else whole", () => {
    expect(withoutQuery("https://h/x?a=1#b")).toBe("https://h/x");
    expect(withoutQuery("https://h/x#b")).toBe("https://h/x");
    expect(withoutQuery("/_astro/a.js")).toBe("/_astro/a.js");
  });
});

describe("report", () => {
  beforeEach(() => {
    sentry.init.mockClear();
    sentry.captureException.mockClear();
  });

  it("does nothing without a DSN: every build but production's", async () => {
    await report(new Error("x"), "calculator");
    await report(new Error("x"), "explorer", "");
    expect(sentry.init).not.toHaveBeenCalled();
    expect(sentry.captureException).not.toHaveBeenCalled();
  });

  it("starts the SDK once and tags each report with its island", async () => {
    await report(new Error("first"), "calculator", DSN, "pyeconomics@1.0.0+abc");
    await report("not an error", "explorer", DSN, "pyeconomics@1.0.0+abc");
    expect(sentry.init).toHaveBeenCalledTimes(1);
    const options = sentry.init.mock.calls[0]?.[0] as ReturnType<typeof sentryOptions>;
    expect(options.dataCollection).toBe(DATA_COLLECTION);
    expect(options.defaultIntegrations).toBe(false);
    expect(options.integrations).toEqual([{ name: "LinkedErrors" }, { name: "Dedupe" }]);
    expect(sentry.captureException.mock.calls.map((call) => call[1])).toEqual([
      { tags: { island: "calculator" } },
      { tags: { island: "explorer" } },
    ]);
    expect(sentry.captureException.mock.calls[1]?.[0]).toBeInstanceOf(Error);
  });

  it("never throws when the SDK fails", async () => {
    sentry.captureException.mockImplementationOnce(() => {
      throw new Error("down");
    });
    await expect(report(new Error("x"), "calculator", DSN)).resolves.toBeUndefined();
  });
});
