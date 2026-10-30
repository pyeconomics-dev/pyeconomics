// web/tests/e2e/version.spec.ts
// /version.json reports the version the site data was exported from and the
// commit the site was built from (ADR-0013 decision 2).
import { readFileSync } from "node:fs";

import { expect, test } from "./support.ts";

const registry = JSON.parse(
  readFileSync(new URL("../../src/data/generated/registry.json", import.meta.url), "utf8"),
) as { pyeconomics: string };

test("/version.json reports the version and the commit", async ({ request }) => {
  const response = await request.get("/version.json");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toMatch(/^application\/json/);
  const body = (await response.json()) as Record<string, unknown>;
  expect(Object.keys(body).sort()).toEqual(["git_sha", "pyeconomics"]);
  expect(body.pyeconomics).toBe(registry.pyeconomics);
  expect(body.git_sha).toMatch(/^[0-9a-f]{40}$/);
  if (process.env.GIT_SHA) expect(body.git_sha).toBe(process.env.GIT_SHA);
});
