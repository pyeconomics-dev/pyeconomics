// web/tests/parity/golden.test.ts
// The web surface's parity (Phase 5 Step 6; ADR-0013 decision 8, ADR-0012
// decision 3): every golden case, as scripts/web/export_site_data.py wrote it
// into golden.json with the Python API's answer from the same locked
// environment, is sent through the calculator's own request builder
// (src/lib/run-request.ts, the generated client) to a local `pyeconomics
// serve`, and the answer must be the Python API's: the same status and the
// same bytes. A difference is a bug in the side that changed the bytes; this
// comparison is never loosened.
import { readFileSync } from "node:fs";

import { describe, expect, inject, it } from "vitest";

import { runModel } from "@/lib/run-request";

interface GoldenCase {
  model: string;
  case: string;
  inputs: Record<string, unknown>;
  status: number;
  body: string;
}

const golden = JSON.parse(
  readFileSync(new URL("../../src/data/generated/golden.json", import.meta.url), "utf8"),
) as { format: number; cases: GoldenCase[] };

const byModel = new Map<string, GoldenCase[]>();
for (const entry of golden.cases) byModel.set(entry.model, [...(byModel.get(entry.model) ?? []), entry]);

/** Where two byte strings first differ, with a little of each side. */
function firstDifference(found: Uint8Array, expected: Uint8Array): string {
  let at = 0;
  while (at < found.length && at < expected.length && found.at(at) === expected.at(at)) at += 1;
  const show = (bytes: Uint8Array) => new TextDecoder().decode(bytes.slice(Math.max(0, at - 40), at + 40));
  return `byte ${String(at)}: found …${show(found)}… expected …${show(expected)}…`;
}

describe("every golden case through the calculator's request builder", () => {
  it("holds all the golden cases", () => {
    expect(golden.cases.length).toBeGreaterThanOrEqual(354);
    expect(byModel.size).toBeGreaterThanOrEqual(50);
  });

  for (const [model, cases] of byModel) {
    it.concurrent(`${model}: ${String(cases.length)} cases answer the Python API's bytes`, async () => {
      const api = inject("api");
      for (const entry of cases) {
        const answer = await runModel(entry.model, entry.inputs, {}, { baseUrl: api });
        const expected = new TextEncoder().encode(entry.body);
        expect(answer.status, `${model}::${entry.case}`).toBe(entry.status);
        const same = answer.bytes.length === expected.length && answer.bytes.every((byte, index) => byte === expected.at(index));
        expect(same, `${model}::${entry.case} ${same ? "" : firstDifference(answer.bytes, expected)}`).toBe(true);
      }
    });
  }
});
