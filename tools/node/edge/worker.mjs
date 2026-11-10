// tools/node/edge/worker.mjs
//
// The edge Worker (ADR-0012 decision 20; ADR-0013 decision 3). One module
// serves two Workers: staging-api.pyeconomics.dev, where it forwards every
// path to the Cloud Run origin, and the site (web/wrangler.jsonc), where an
// ASSETS binding holds the built pages and Cloudflare runs this module first
// only on API_PATHS (run_worker_first); every other request, found or not,
// is the assets'. Should one reach the module anyway, it answers from the
// assets: only the API's paths ever reach the origin.
//
// It keeps GET runs with the Workers Cache API, for as long as the origin's
// Cache-Control allows (ADR-0013 decision 7): never a POST run or a problem.
// Cloudflare's documentation says the Cache API is unavailable for a Worker
// behind Access (staging, and production until the cutover); it worked there on
// 2026-11-10, but that is undocumented, so a failure of the cache is only ever a
// miss.

/** The API's paths, as web/wrangler.jsonc's run_worker_first lists them. */
export const API_PATHS = Object.freeze(["/v1/*", "/mcp", "/healthz", "/version", "/openapi.json"]);

// The one route whose answers the edge keeps.
const RUN_PATH = /^\/v1\/models\/[^/]+\/run$/;

const HOP_BY_HOP_HEADERS = Object.freeze([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

// The browser's cookies (Access's CF_Authorization among them) and every
// header Access adds or reads (cf-access-*) stay at the edge.
const STRIPPED_REQUEST_HEADERS = Object.freeze(["cookie", "host", "x-pyeconomics-edge"]);
const STRIPPED_REQUEST_PREFIX = "cf-access-";

/** Whether a request path is one of API_PATHS, matched as Cloudflare does. */
export function isApiPath(pathname) {
  return API_PATHS.some((pattern) =>
    pattern.endsWith("/*") ? pathname.startsWith(pattern.slice(0, -1)) : pathname === pattern,
  );
}

function connectionTokens(headers) {
  const raw = headers.get("connection");
  if (!raw) {
    return [];
  }
  return raw
    .split(",")
    .map((token) => token.trim().toLowerCase())
    .filter((token) => token.length > 0);
}

function buildForwardHeaders(requestHeaders, credential) {
  const headers = new Headers(requestHeaders);
  for (const name of connectionTokens(requestHeaders)) {
    headers.delete(name);
  }
  for (const name of HOP_BY_HOP_HEADERS) {
    headers.delete(name);
  }
  for (const name of STRIPPED_REQUEST_HEADERS) {
    headers.delete(name);
  }
  for (const name of [...headers.keys()]) {
    if (name.startsWith(STRIPPED_REQUEST_PREFIX)) {
      headers.delete(name);
    }
  }
  const clientIp = requestHeaders.get("cf-connecting-ip");
  if (clientIp !== null && clientIp.trim().length > 0) {
    headers.set("CF-Connecting-IP", clientIp.trim());
  } else {
    headers.delete("cf-connecting-ip");
  }
  headers.set("X-Pyeconomics-Edge", credential);
  return headers;
}

function buildResponseHeaders(upstreamHeaders) {
  const headers = new Headers(upstreamHeaders);
  for (const name of connectionTokens(upstreamHeaders)) {
    headers.delete(name);
  }
  for (const name of HOP_BY_HOP_HEADERS) {
    headers.delete(name);
  }
  // _headers applies to asset responses only, so forwarded ones get it here.
  headers.set("X-Content-Type-Options", "nosniff");
  return headers;
}

function resolveOriginUrl(requestUrlString, originBaseString) {
  const incoming = new URL(requestUrlString);
  const target = new URL(originBaseString);
  if (target.protocol !== "https:") {
    throw new Error("ORIGIN_URL must use https:");
  }
  target.pathname = incoming.pathname;
  target.search = incoming.search;
  target.hash = "";
  return target;
}

function misconfiguredResponse() {
  const body = JSON.stringify({
    type: "https://pyeconomics.dev/problems/service-unavailable",
    title: "Service unavailable",
    status: 503,
    detail: "The edge Worker is missing required configuration.",
  });
  return new Response(body, {
    status: 503,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/problem+json",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export async function forwardRequest(request, env, fetchImpl = globalThis.fetch) {
  const originBase = typeof env?.ORIGIN_URL === "string" ? env.ORIGIN_URL.trim() : "";
  const credential =
    typeof env?.EDGE_CREDENTIAL === "string" ? env.EDGE_CREDENTIAL.trim() : "";
  if (originBase.length === 0 || credential.length < 32 || credential.length > 512) {
    return misconfiguredResponse();
  }

  let targetUrl;
  try {
    targetUrl = resolveOriginUrl(request.url, originBase);
  } catch {
    return misconfiguredResponse();
  }

  const method = request.method.toUpperCase();
  const isHealthProbe =
    targetUrl.pathname === "/healthz" && (method === "GET" || method === "HEAD");
  if (isHealthProbe) {
    // Google Frontend reserves /healthz on *.run.app origin URLs and returns a
    // static 404 before reaching Cloud Run; Cloud Run's own HTTP startup probe
    // checks container /healthz:8080 directly. Probe the container's open
    // /version endpoint and translate a 200 response into {"status":"ok"}.
    targetUrl.pathname = "/version";
    targetUrl.search = "";
  }
  const hasBody = method !== "GET" && method !== "HEAD" && request.body !== null;
  const init = {
    method,
    headers: buildForwardHeaders(request.headers, credential),
    body: hasBody ? request.body : null,
    redirect: "manual",
  };
  if (hasBody) {
    init.duplex = "half";
  }

  const upstream = await fetchImpl(targetUrl.toString(), init);
  if (isHealthProbe && upstream.status === 200) {
    const headers = buildResponseHeaders(upstream.headers);
    headers.set("Cache-Control", "no-store");
    headers.set("Content-Type", "application/json");
    return new Response(method === "HEAD" ? null : '{"status":"ok"}', {
      status: 200,
      statusText: upstream.statusText,
      headers,
    });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: buildResponseHeaders(upstream.headers),
  });
}

/** Whether a request is a GET run, the only request the edge answers from its cache. */
export function isCachedRun(request) {
  return request.method.toUpperCase() === "GET" && RUN_PATH.test(new URL(request.url).pathname);
}

/**
 * Whether the origin lets the edge keep an answer: a 200 it calls public, with a
 * lifetime. A POST run, a problem and a run on data that may not be stored all
 * answer no-store.
 */
export function mayKeep(response) {
  if (response.status !== 200 || response.headers.has("set-cookie")) {
    return false;
  }
  const directives = (response.headers.get("cache-control") ?? "")
    .toLowerCase()
    .split(",")
    .map((directive) => directive.trim());
  const maxAge = directives.find((directive) => directive.startsWith("max-age="));
  return (
    directives.includes("public") &&
    !directives.includes("no-store") &&
    !directives.includes("private") &&
    maxAge !== undefined &&
    Number(maxAge.slice("max-age=".length)) > 0
  );
}

// An answer holds the package's version and the URL does not, so each deployed
// Worker keeps its own entries: a deploy retires every answer the last one
// kept, where the origin's day-long max-age would serve them on.
function cacheKey(request, env) {
  const key = new URL(request.url);
  key.pathname = `/edge-cache/${env?.CF_VERSION_METADATA?.id ?? "local"}${key.pathname}`;
  return key.toString();
}

function conditionalHeaders(request) {
  const tag = request.headers.get("if-none-match");
  return tag === null ? {} : { "If-None-Match": tag };
}

async function keep(edge, key, response) {
  try {
    await edge.cache.put(key, response);
  } catch {
    // A store that fails keeps nothing, and the caller already has the answer.
  }
}

async function cachedRun(request, env, fetchImpl, edge) {
  const key = cacheKey(request, env);
  try {
    const hit = await edge.cache.match(new Request(key, { headers: conditionalHeaders(request) }));
    if (hit !== undefined) {
      return hit;
    }
  } catch {
    // A cache that cannot answer is a miss.
  }
  const response = await forwardRequest(request, env, fetchImpl);
  if (mayKeep(response)) {
    edge.waitUntil(keep(edge, key, response.clone()));
  }
  return response;
}

/**
 * Answer one request: from the assets when the Worker has them and the path is
 * not the API's, a GET run from the edge's cache when it holds one, otherwise
 * from the origin.
 */
export async function handleRequest(request, env, fetchImpl = globalThis.fetch, edge = null) {
  if (env?.ASSETS && !isApiPath(new URL(request.url).pathname)) {
    return env.ASSETS.fetch(request);
  }
  if (edge !== null && isCachedRun(request)) {
    return cachedRun(request, env, fetchImpl, edge);
  }
  return forwardRequest(request, env, fetchImpl);
}

function edgeCache(ctx) {
  const cache = globalThis.caches?.default;
  return cache === undefined || ctx === undefined
    ? null
    : { cache, waitUntil: (task) => ctx.waitUntil(task) };
}

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env, globalThis.fetch, edgeCache(ctx));
  },
};
