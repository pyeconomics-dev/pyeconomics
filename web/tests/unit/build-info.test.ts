// web/tests/unit/build-info.test.ts
// /version.json's commit: GIT_SHA when a deploy sets it, validated, and the
// checkout's HEAD otherwise; and the build's refusal without the site data or
// with a stale validator.
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { missing, REQUIRED, VALIDATORS, staleValidators } from "../../scripts/require-data.ts";
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

  it("finds every validator current after `npm run data`", () => {
    expect(staleValidators()).toEqual([]);
  });

  it("names a missing, stale or left-over validator", () => {
    const root = mkdtempSync(join(tmpdir(), "pyeconomics-validators-"));
    const generated = join(root, "src", "data", "generated");
    mkdirSync(join(root, VALIDATORS), { recursive: true });
    const schema = { type: "object" };
    const sha = createHash("sha256").update(JSON.stringify(schema), "utf8").digest("hex");
    writeFileSync(
      join(generated, "registry.json"),
      JSON.stringify({
        models: [
          { id: "toy.current", input_schema: schema },
          { id: "toy.stale", input_schema: { type: "object", title: "changed" } },
          { id: "toy.missing", input_schema: schema },
        ],
      }),
    );
    const module = `export default {};\nexport const schemaSha256 = "${sha}";\n`;
    writeFileSync(join(root, VALIDATORS, "toy.current.js"), module);
    writeFileSync(join(root, VALIDATORS, "toy.stale.js"), module);
    writeFileSync(join(root, VALIDATORS, "toy.removed.js"), module);
    expect(staleValidators(root)).toEqual([
      "toy.stale's validator was compiled from another schema",
      "toy.missing has no validator",
      "toy.removed.js is a validator for no registered model",
    ]);
  });
});
