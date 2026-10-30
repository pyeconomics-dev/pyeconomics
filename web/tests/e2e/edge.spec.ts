// web/tests/e2e/edge.spec.ts
// One host, one Worker (ADR-0013 decision 3), in the runtime Cloudflare runs:
// `wrangler dev` serves the env-less configuration, whose shared edge Worker
// has no origin and no credential. So an API path reaches the Worker, which
// answers 503 with nosniff; every other path is the assets', the 404 page
// when nothing matches, navigation or not, and never reaches the Worker. A
// local build sends no X-Robots-Tag; only a staging build refuses indexing.
import { expect, headerPolicy, test } from "./support.ts";

const API_PATHS = ["/v1/models", "/mcp", "/healthz", "/version", "/openapi.json"];

for (const path of API_PATHS) {
  test(`${path} runs the edge Worker, never an asset`, async ({ request }) => {
    const response = await request.get(path);
    expect(response.status()).toBe(503);
    const headers = response.headers();
    expect(headers["content-type"]).toBe("application/problem+json");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["content-security-policy"]).toBeUndefined();
    const problem = (await response.json()) as Record<string, unknown>;
    expect(problem.type).toBe("https://pyeconomics.dev/problems/service-unavailable");
  });
}

test("a path matching no asset is the 404 page, even when it is not a navigation", async ({
  request,
}) => {
  for (const path of ["/no-such-page", "/v1", "/v2/models", "/mcp/"]) {
    const response = await request.get(path, { headers: { Accept: "*/*" } });
    expect(response.status(), path).toBe(404);
    expect(response.headers()["content-type"], path).toMatch(/^text\/html/);
    expect(await response.text(), path).toContain("<main");
  }
});

test("pages and files are the assets', with the policy and no X-Robots-Tag", async ({ request }) => {
  for (const path of ["/", "/version.json"]) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(200);
    const headers = response.headers();
    expect(headers["content-security-policy"], path).toBe(headerPolicy());
    expect(headers["x-robots-tag"], path).toBeUndefined();
  }
});
