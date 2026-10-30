// tools/node/edge/worker.test.mjs

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import worker, { API_PATHS, forwardRequest, handleRequest, isApiPath } from "./worker.mjs";

const TEST_ORIGIN = "https://pyeconomics-api-staging-uc.a.run.app";
const TEST_CREDENTIAL = `edge-test-${"x".repeat(26)}`;
const SITE = "https://staging.pyeconomics.dev";

// web/wrangler.jsonc, whose comments each take a whole line.
function siteConfig() {
  const text = readFileSync(new URL("../../../web/wrangler.jsonc", import.meta.url), "utf8");
  const json = text
    .split("\n")
    .filter((line) => !line.trimStart().startsWith("//"))
    .join("\n");
  return JSON.parse(json);
}

// The site Worker's ASSETS binding: records each request it answers.
function makeStubAssets() {
  const calls = [];
  const assets = {
    async fetch(request) {
      calls.push(request.url);
      return new Response("<!DOCTYPE html><title>Not found</title>", {
        status: 404,
        headers: { "Content-Type": "text/html" },
      });
    },
  };
  return { calls, assets };
}

function makeStubFetch(responseInit = {}) {
  const calls = [];
  const fetchStub = async (url, init) => {
    let bodyText = null;
    if (init?.body) {
      bodyText = await new Response(init.body).text();
    }
    calls.push({ url, init, bodyText });
    return new Response(responseInit.body ?? '{"status":"ok"}', {
      status: responseInit.status ?? 200,
      headers: responseInit.headers ?? {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  };
  return { calls, fetchStub };
}

describe("edge worker", () => {
  it("forwards GET method, path and query to ORIGIN_URL with X-Pyeconomics-Edge and CF-Connecting-IP", async () => {
    const { calls, fetchStub } = makeStubFetch({
      status: 200,
      body: '{"observations":[]}',
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=300",
        ETag: 'W/"abc123"',
      },
    });
    const request = new Request(
      "https://staging-api.pyeconomics.dev/v1/series/treasury:debt?start=2025-01-01&end=2025-01-31",
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "CF-Connecting-IP": "203.0.113.42",
          "X-Pyeconomics-Edge": "forged-by-caller",
        },
      },
    );

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 200);
    assert.equal(await response.text(), '{"observations":[]}');
    assert.equal(response.headers.get("etag"), 'W/"abc123"');
    assert.equal(calls.length, 1);
    assert.equal(
      calls[0].url,
      "https://pyeconomics-api-staging-uc.a.run.app/v1/series/treasury:debt?start=2025-01-01&end=2025-01-31",
    );
    assert.equal(calls[0].init.method, "GET");
    assert.equal(calls[0].init.body, null);
    assert.equal(calls[0].init.redirect, "manual");
    const forwarded = calls[0].init.headers;
    assert.equal(forwarded.get("x-pyeconomics-edge"), TEST_CREDENTIAL);
    assert.equal(forwarded.get("cf-connecting-ip"), "203.0.113.42");
    assert.equal(forwarded.get("origin"), null);
  });

  it("forwards POST /mcp body and MCP headers without adding Origin", async () => {
    const { calls, fetchStub } = makeStubFetch({
      status: 200,
      body: '{"jsonrpc":"2.0","id":1,"result":{}}',
    });
    const payload = JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: { name: "foundations_time_value", arguments: {} },
    });
    const request = new Request("https://staging-api.pyeconomics.dev/mcp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "foundations_time_value",
        "CF-Connecting-IP": "198.51.100.7",
      },
      body: payload,
    });

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 200);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "https://pyeconomics-api-staging-uc.a.run.app/mcp");
    assert.equal(calls[0].init.method, "POST");
    assert.equal(calls[0].bodyText, payload);
    const forwarded = calls[0].init.headers;
    assert.equal(forwarded.get("mcp-protocol-version"), "2026-07-28");
    assert.equal(forwarded.get("mcp-method"), "tools/call");
    assert.equal(forwarded.get("mcp-name"), "foundations_time_value");
    assert.equal(forwarded.get("origin"), null);
    assert.equal(forwarded.get("x-pyeconomics-edge"), TEST_CREDENTIAL);
  });

  it("strips hop-by-hop headers, Connection-listed headers, and Cloudflare Access headers while preserving CF-Connecting-IP", async () => {
    const { calls, fetchStub } = makeStubFetch({
      status: 200,
      headers: {
        "Content-Type": "application/json",
        Connection: "keep-alive, x-upstream-hop",
        "Keep-Alive": "timeout=5",
        "Transfer-Encoding": "chunked",
        "X-Upstream-Hop": "drop-me",
        "X-Preserved": "keep-me",
      },
    });
    const request = new Request("https://staging-api.pyeconomics.dev/version", {
      method: "GET",
      headers: {
        Connection: "keep-alive, x-custom-hop, cf-connecting-ip",
        "Keep-Alive": "timeout=5",
        "Proxy-Authorization": "Basic dGVzdDp0ZXN0",
        TE: "trailers",
        Trailer: "Expires",
        "Transfer-Encoding": "chunked",
        Upgrade: "websocket",
        "X-Custom-Hop": "should-be-removed",
        "CF-Access-Client-Id": "access-id",
        "CF-Access-Client-Secret": "access-secret",
        "Cf-Access-Jwt-Assertion": "jwt-token",
        "CF-Connecting-IP": "192.0.2.99",
      },
    });

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    const forwarded = calls[0].init.headers;
    assert.equal(forwarded.get("connection"), null);
    assert.equal(forwarded.get("keep-alive"), null);
    assert.equal(forwarded.get("proxy-authorization"), null);
    assert.equal(forwarded.get("te"), null);
    assert.equal(forwarded.get("trailer"), null);
    assert.equal(forwarded.get("transfer-encoding"), null);
    assert.equal(forwarded.get("upgrade"), null);
    assert.equal(forwarded.get("x-custom-hop"), null);
    assert.equal(forwarded.get("cf-access-client-id"), null);
    assert.equal(forwarded.get("cf-access-client-secret"), null);
    assert.equal(forwarded.get("cf-access-jwt-assertion"), null);
    assert.equal(forwarded.get("cf-connecting-ip"), "192.0.2.99");
    assert.equal(forwarded.get("x-pyeconomics-edge"), TEST_CREDENTIAL);

    assert.equal(response.headers.get("connection"), null);
    assert.equal(response.headers.get("keep-alive"), null);
    assert.equal(response.headers.get("transfer-encoding"), null);
    assert.equal(response.headers.get("x-upstream-hop"), null);
    assert.equal(response.headers.get("x-preserved"), "keep-me");
  });

  it("never changes origin host on protocol-relative paths", async () => {
    const { calls, fetchStub } = makeStubFetch();
    const request = new Request(
      "https://staging-api.pyeconomics.dev//evil.example.com/v1/models",
      { method: "GET" },
    );

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 200);
    assert.equal(calls.length, 1);
    const parsedTarget = new URL(calls[0].url);
    assert.equal(parsedTarget.origin, TEST_ORIGIN);
  });

  it("probes origin /version for GET /healthz because Google Frontend reserves /healthz on *.run.app", async () => {
    const { calls, fetchStub } = makeStubFetch({
      status: 200,
      body: '{"git_sha":"deadbeef","mode":"hosted","pyeconomics":"1.0.0b1.dev1"}',
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
    const request = new Request("https://staging-api.pyeconomics.dev/healthz", {
      method: "GET",
      headers: { "CF-Connecting-IP": "198.51.100.12" },
    });

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 200);
    assert.equal(await response.text(), '{"status":"ok"}');
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(response.headers.get("content-type"), "application/json");
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "https://pyeconomics-api-staging-uc.a.run.app/version");
  });

  it("returns 503 problem+json without calling fetch when misconfigured", async () => {
    const { calls, fetchStub } = makeStubFetch();
    const request = new Request("https://staging-api.pyeconomics.dev/healthz");

    const missingCred = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: "too-short" },
      fetchStub,
    );
    assert.equal(missingCred.status, 503);
    assert.equal(missingCred.headers.get("content-type"), "application/problem+json");
    assert.equal(calls.length, 0);

    const insecureOrigin = await worker.fetch(request, {
      ORIGIN_URL: "http://insecure.example.com",
      EDGE_CREDENTIAL: TEST_CREDENTIAL,
    });
    assert.equal(insecureOrigin.status, 503);
    assert.equal(insecureOrigin.headers.get("x-content-type-options"), "nosniff");
  });

  it("strips every cookie and every Access header, including the authenticated user's email", async () => {
    const { calls, fetchStub } = makeStubFetch();
    const request = new Request("https://staging-api.pyeconomics.dev/v1/models", {
      headers: {
        Cookie: "CF_Authorization=access-session; other=value",
        "Cf-Access-Authenticated-User-Email": "maintainer@example.com",
        "Cf-Access-Jwt-Assertion": "jwt-token",
        "CF-Access-Future-Header": "anything",
        Accept: "application/json",
      },
    });

    await forwardRequest(request, { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL }, fetchStub);

    const forwarded = calls[0].init.headers;
    assert.equal(forwarded.get("cookie"), null);
    assert.deepEqual(
      [...forwarded.keys()].filter((name) => name.startsWith("cf-access-")),
      [],
    );
    assert.equal(forwarded.get("accept"), "application/json");
    assert.equal(forwarded.get("x-pyeconomics-edge"), TEST_CREDENTIAL);
  });

  it("adds X-Content-Type-Options: nosniff to every forwarded response", async () => {
    const { fetchStub } = makeStubFetch({
      status: 404,
      body: '{"status":404}',
      headers: { "Content-Type": "application/problem+json", "X-Content-Type-Options": "sniff-me" },
    });
    const request = new Request("https://staging-api.pyeconomics.dev/v1/models/unknown");

    const response = await forwardRequest(
      request,
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 404);
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("content-type"), "application/problem+json");
  });
});

describe("site worker (ASSETS bound)", () => {
  const env = (assets) => ({
    ORIGIN_URL: TEST_ORIGIN,
    EDGE_CREDENTIAL: TEST_CREDENTIAL,
    ASSETS: assets,
  });

  it("names exactly the paths web/wrangler.jsonc runs the Worker first on", () => {
    const config = siteConfig();
    assert.deepEqual(config.assets.run_worker_first, [...API_PATHS]);
    assert.equal(config.assets.binding, "ASSETS");
    assert.equal(config.main, "../tools/node/edge/worker.mjs");
    assert.equal(config.workers_dev, false);
    assert.equal(config.preview_urls, false);
  });

  it("matches the API's paths as run_worker_first does", () => {
    const api = ["/v1/", "/v1/models", "/v1/series/treasury:debt", "/mcp", "/healthz", "/version", "/openapi.json"];
    for (const path of api) {
      assert.equal(isApiPath(path), true, path);
    }
    const other = [
      "/",
      "/v1",
      "/v2/models",
      "/mcp/",
      "/healthz/",
      "/version.json",
      "/versions",
      "/openapi.json/x",
      "/models/",
      "//evil.example.com/v1/models",
      "/x/v1/models",
    ];
    for (const path of other) {
      assert.equal(isApiPath(path), false, path);
    }
  });

  it("forwards each API path with the credential and without cookies or Access headers", async () => {
    for (const path of ["/v1/models", "/mcp", "/version", "/openapi.json"]) {
      const { calls, fetchStub } = makeStubFetch();
      const { calls: assetCalls, assets } = makeStubAssets();
      const request = new Request(`${SITE}${path}`, {
        method: path === "/mcp" ? "POST" : "GET",
        headers: {
          Cookie: "CF_Authorization=access-session",
          "CF-Access-Client-Id": "access-id",
          "CF-Access-Client-Secret": "access-secret",
          "Cf-Access-Authenticated-User-Email": "maintainer@example.com",
          "CF-Connecting-IP": "203.0.113.9",
        },
        body: path === "/mcp" ? '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' : undefined,
      });

      const response = await handleRequest(request, env(assets), fetchStub);

      assert.equal(response.status, 200, path);
      assert.equal(response.headers.get("x-content-type-options"), "nosniff", path);
      assert.deepEqual(assetCalls, [], path);
      assert.equal(calls.length, 1, path);
      assert.equal(calls[0].url, `${TEST_ORIGIN}${path}`, path);
      const forwarded = calls[0].init.headers;
      assert.equal(forwarded.get("x-pyeconomics-edge"), TEST_CREDENTIAL, path);
      assert.equal(forwarded.get("cookie"), null, path);
      assert.deepEqual([...forwarded.keys()].filter((name) => name.startsWith("cf-access-")), [], path);
      assert.equal(forwarded.get("cf-connecting-ip"), "203.0.113.9", path);
    }
  });

  it("still maps /healthz to the origin's /version", async () => {
    const { calls, fetchStub } = makeStubFetch({
      status: 200,
      body: '{"git_sha":"deadbeef","mode":"hosted","pyeconomics":"1.0.0rc1.dev1"}',
    });
    const { calls: assetCalls, assets } = makeStubAssets();

    const response = await handleRequest(new Request(`${SITE}/healthz`), env(assets), fetchStub);

    assert.equal(response.status, 200);
    assert.equal(await response.text(), '{"status":"ok"}');
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.deepEqual(assetCalls, []);
    assert.equal(calls[0].url, `${TEST_ORIGIN}/version`);
  });

  it("never sends a non-API path to the origin: the assets answer it", async () => {
    const paths = [
      "/",
      "/models/",
      "/version.json",
      "/no-such-page",
      "/v1",
      "/v2/models",
      "/mcp/",
      "/healthz/",
      "//evil.example.com/v1/models",
    ];
    for (const path of paths) {
      const { calls, fetchStub } = makeStubFetch();
      const { calls: assetCalls, assets } = makeStubAssets();

      const response = await handleRequest(
        new Request(`${SITE}${path}`, { method: "POST", body: "{}" }),
        env(assets),
        fetchStub,
      );

      assert.equal(response.status, 404, path);
      assert.equal(calls.length, 0, path);
      assert.equal(assetCalls.length, 1, path);
    }
  });

  it("forwards every path on the API-only Worker, which has no ASSETS binding", async () => {
    const { calls, fetchStub } = makeStubFetch();

    const response = await handleRequest(
      new Request("https://staging-api.pyeconomics.dev/"),
      { ORIGIN_URL: TEST_ORIGIN, EDGE_CREDENTIAL: TEST_CREDENTIAL },
      fetchStub,
    );

    assert.equal(response.status, 200);
    assert.equal(calls[0].url, `${TEST_ORIGIN}/`);
  });
});
