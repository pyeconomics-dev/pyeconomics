// web/tests/unit/build-info.test.ts
// /version.json's commit: GIT_SHA when a deploy sets it, validated, and the
// checkout's HEAD otherwise; and the build's refusal without the site data.
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { missing, REQUIRED } from "../../scripts/require-data.ts";
import { gitSha } from "@/lib/build-info";

describe("gitSha", () => {
  it("takes a full commit SHA from GIT_SHA", () => {
    const sha = "0123456789abcdef0123456789abcdef01234567";
    expect(gitSha(sha)).toBe(sha);
  });

  it.each(["abc123", "0123456789ABCDEF0123456789ABCDEF01234567", "main", "$(id)"])(
    "refuses %s",
    (value) => {
      expect(() => gitSha(value)).toThrow(/GIT_SHA must be/);
    },
  );

  it("reads the checkout's HEAD when GIT_SHA is unset or empty", () => {
    expect(gitSha("")).toMatch(/^[0-9a-f]{40}$/);
  });
});

describe("require-data", () => {
  it("names every file the build needs when none is there", () => {
    expect(missing(mkdtempSync(join(tmpdir(), "pyeconomics-data-")))).toEqual([...REQUIRED]);
  });

  it("finds them all after `npm run data`", () => {
    expect(missing()).toEqual([]);
  });
});
