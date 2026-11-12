// web/tests/unit/analytics.test.ts
// The vendored tracker and its tag (Phase 5 Step 15; ADR-0013 decision 13):
// the file is the pinned copy, it sets no cookie and writes no storage, and
// the tag excludes the URL's query and fragment, honours Do Not Track, records
// only on the production host and posts only to Umami's collector.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { UMAMI_COLLECTOR } from "../../csp.config.ts";
import { PRODUCTION_HOSTNAME, TRACKER_PATH, TRACKER_SHA256, TRACKER_SOURCE, trackerAttributes } from "@/lib/analytics";

const tracker = readFileSync(fileURLToPath(new URL(`../../${TRACKER_SOURCE}`, import.meta.url)));
const text = tracker.toString("utf8");

describe("the vendored tracker", () => {
  it("is the pinned copy, served at a path that carries its hash", () => {
    expect(createHash("sha256").update(tracker).digest("hex")).toBe(TRACKER_SHA256);
    expect(TRACKER_PATH).toBe(`/vendor/umami-${TRACKER_SHA256.slice(0, 8)}.js`);
  });

  it("sets no cookie and writes no storage: it only reads the visitor's own opt-out", () => {
    expect(text).not.toMatch(/document\.cookie/);
    expect(text).not.toMatch(/sessionStorage|indexedDB/);
    expect(text).not.toMatch(/setItem\(/);
    expect(text.match(/getItem\([^)]*\)/g)).toEqual(['getItem("umami.disabled")']);
  });

  it("posts to the host the tag names, Umami's collector by default", () => {
    expect(text).toContain("https://gateway.umami.is");
    expect(text).toContain("/api/send");
    expect(text).toContain('k("exclude-search")===T');
    expect(text).toContain('k("exclude-hash")===T');
  });
});

describe("the tracker tag", () => {
  it("excludes queries and fragments, honours Do Not Track and records only on the production host", () => {
    const id = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0";
    expect(trackerAttributes(id)).toEqual({
      src: TRACKER_PATH,
      "data-website-id": id,
      "data-host-url": UMAMI_COLLECTOR,
      "data-domains": PRODUCTION_HOSTNAME,
      "data-exclude-search": "true",
      "data-exclude-hash": "true",
      "data-do-not-track": "true",
    });
    expect(PRODUCTION_HOSTNAME).toBe("pyeconomics.dev");
  });

  it("never turns on error capture, a distinct id or a tag", () => {
    const keys = Object.keys(trackerAttributes("0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"));
    for (const off of ["data-errors", "data-distinct-id", "data-tag", "data-performance", "data-before-send"]) {
      expect(keys).not.toContain(off);
    }
  });
});
