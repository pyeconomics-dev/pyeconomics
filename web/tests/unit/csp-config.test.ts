// web/tests/unit/csp-config.test.ts
// csp.config.ts holds decision 9's policy: its directives, nothing unsafe, and
// a <meta> policy without the directives only a header can carry.
import { describe, expect, it } from "vitest";

import {
  ALLOWED,
  ALLOWED_PATTERNS,
  ANALYTICS,
  DIRECTIVES,
  EMAIL_PROCESSOR,
  FORBIDDEN,
  FORMS,
  HASHED,
  HEADER_ONLY,
  PERMISSIONS_POLICY,
  SECURITY_HEADERS,
  SENTRY,
  SENTRY_INGEST,
  UMAMI_COLLECTOR,
  analyticsBuild,
  metaDirectives,
  sentryBuild,
  signupForms,
} from "../../csp.config.ts";

describe("decision 9's policy", () => {
  it("has exactly decision 9's directives", () => {
    expect(Object.keys(DIRECTIVES)).toEqual([
      "default-src",
      "script-src",
      "style-src",
      "img-src",
      "font-src",
      "connect-src",
      "worker-src",
      "form-action",
      "frame-ancestors",
      "base-uri",
      "object-src",
      "upgrade-insecure-requests",
    ]);
    expect(Object.keys(ALLOWED)).toEqual(Object.keys(DIRECTIVES));
  });

  it("uses only allowed sources and nothing forbidden", () => {
    const allowed = new Map(Object.entries(ALLOWED));
    for (const [name, sources] of Object.entries(DIRECTIVES)) {
      for (const source of sources) {
        expect(allowed.get(name)).toContain(source);
        expect(FORBIDDEN).not.toContain(source);
      }
    }
  });

  it("allows no third-party script or style origin, and frames nowhere", () => {
    expect(ALLOWED["script-src"]).toEqual(["'self'", "'wasm-unsafe-eval'"]);
    expect(ALLOWED["style-src"]).toEqual(["'self'"]);
    expect(DIRECTIVES["frame-ancestors"]).toEqual(["'none'"]);
  });

  it("keeps header-only and hashed directives out of the <meta> list", () => {
    const names = metaDirectives().map((directive) => directive.split(" ")[0]);
    for (const name of [...HEADER_ONLY, ...HASHED]) expect(names).not.toContain(name);
    expect(names).toContain("upgrade-insecure-requests");
    expect(names).toHaveLength(Object.keys(DIRECTIVES).length - HEADER_ONLY.size - HASHED.size);
  });

  it("sends decision 9's other headers", () => {
    expect(Object.keys(SECURITY_HEADERS)).toEqual([
      "Strict-Transport-Security",
      "X-Content-Type-Options",
      "Referrer-Policy",
      "Permissions-Policy",
      "Cross-Origin-Opener-Policy",
    ]);
    expect(SECURITY_HEADERS["Strict-Transport-Security"]).toMatch(/max-age=(\d+); includeSubDomains; preload/);
    const maxAge = Number(/max-age=(\d+)/.exec(SECURITY_HEADERS["Strict-Transport-Security"] ?? "")?.[1]);
    expect(maxAge).toBeGreaterThanOrEqual(31536000);
    for (const feature of PERMISSIONS_POLICY.split(", ")) expect(feature).toMatch(/^[a-z-]+=\(\)$/);
  });
});

describe("Sentry's ingest origin (Phase 5 Step 14)", () => {
  const dsn = "https://0123456789abcdef0123456789abcdef@o42.ingest.us.sentry.io/7";

  it("joins connect-src only in a production build given the browser DSN", () => {
    expect(sentryBuild("production", dsn)).toEqual({ dsn, origin: "https://o42.ingest.us.sentry.io" });
    expect(sentryBuild("production", undefined)).toBeNull();
    expect(sentryBuild("production", "")).toBeNull();
    // These tests build no production flavour: the policy holds no Sentry origin.
    expect(SENTRY).toBeNull();
    expect(DIRECTIVES["connect-src"]).toEqual(["'self'"]);
  });

  it("accepts the 16-digit organisation and project ids Sentry issues today", () => {
    const real = "https://0123456789abcdef0123456789abcdef@o4510273591942001.ingest.us.sentry.io/4510273591942002";
    expect(sentryBuild("production", real)).toEqual({
      dsn: real,
      origin: "https://o4510273591942001.ingest.us.sentry.io",
    });
    expect(SENTRY_INGEST.test("https://o4510273591942001.ingest.us.sentry.io")).toBe(true);
    expect(SENTRY_INGEST.test(`https://o${"1".repeat(21)}.ingest.us.sentry.io`)).toBe(false);
  });

  it.each(["staging", "local", "app", undefined])("refuses a DSN in a %s build", (flavour) => {
    expect(() => sentryBuild(flavour, dsn)).toThrow(/production builds only/);
  });

  it.each([
    "https://0123456789abcdef0123456789abcdef@o42.ingest.de.sentry.io/7",
    "https://0123456789abcdef0123456789abcdef@o42.ingest.sentry.io/7",
    "http://0123456789abcdef0123456789abcdef@o42.ingest.us.sentry.io/7",
    "https://0123456789abcdef0123456789abcdef@o42.ingest.us.sentry.io.example.org/7",
    "https://o42.ingest.us.sentry.io/7",
  ])("refuses a DSN off Sentry's US ingest: %s", (given) => {
    expect(() => sentryBuild("production", given)).toThrow(/US ingest/);
  });

  it("allows Sentry's US ingest origins by pattern, in connect-src alone", () => {
    expect(Object.keys(ALLOWED_PATTERNS)).toEqual(["connect-src"]);
    const [pattern] = ALLOWED_PATTERNS["connect-src"] ?? [];
    expect(pattern?.test("https://o42.ingest.us.sentry.io")).toBe(true);
    for (const origin of ["https://o42.ingest.de.sentry.io", "https://ingest.us.sentry.io", "https://o42.ingest.us.sentry.io.evil.example"]) {
      expect(pattern?.test(origin)).toBe(false);
    }
  });
});

describe("the analytics collector and the email processor (Phase 5 Step 15)", () => {
  const id = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0";

  it("records analytics only in a production build given its website id", () => {
    expect(analyticsBuild("production", id)).toEqual({ websiteId: id });
    expect(analyticsBuild("production", undefined)).toBeNull();
    expect(analyticsBuild("production", "")).toBeNull();
  });

  it.each([undefined, "", "local", "staging", "app"])("refuses a website id in a %s build", (flavour) => {
    expect(() => analyticsBuild(flavour, id)).toThrow(/production builds only/);
  });

  it.each(["not-a-uuid", `${id}x`, id.toUpperCase(), `${id}\n`])("refuses %j as a website id", (given) => {
    expect(() => analyticsBuild("production", given)).toThrow(/not an Umami website id/);
  });

  it("carries the sign-up forms in every build but the app wheel's", () => {
    for (const flavour of [undefined, "", "local", "staging", "production"]) expect(signupForms(flavour)).toBe(true);
    expect(signupForms("app")).toBe(false);
  });

  it("allows the collector only in connect-src and the processor only in form-action", () => {
    expect(UMAMI_COLLECTOR).toBe("https://gateway.umami.is");
    expect(EMAIL_PROCESSOR).toBe("https://buttondown.com");
    for (const [name, sources] of Object.entries(ALLOWED)) {
      expect(sources.includes(UMAMI_COLLECTOR), name).toBe(name === "connect-src");
      expect(sources.includes(EMAIL_PROCESSOR), name).toBe(name === "form-action");
    }
  });

  it("builds this (local) build's policy: no collector, the processor's forms", () => {
    expect(ANALYTICS).toBeNull();
    expect(FORMS).toBe(true);
    expect(DIRECTIVES["connect-src"]).not.toContain(UMAMI_COLLECTOR);
    expect(DIRECTIVES["form-action"]).toEqual(["'self'", EMAIL_PROCESSOR]);
  });
});
