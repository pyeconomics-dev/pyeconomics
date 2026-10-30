// web/tests/unit/csp-config.test.ts
// csp.config.ts holds decision 9's policy: its directives, nothing unsafe, and
// a <meta> policy without the directives only a header can carry.
import { describe, expect, it } from "vitest";

import {
  ALLOWED,
  DIRECTIVES,
  FORBIDDEN,
  HASHED,
  HEADER_ONLY,
  PERMISSIONS_POLICY,
  SECURITY_HEADERS,
  metaDirectives,
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
