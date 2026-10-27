// tools/node/edge/worker.mjs

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

const STRIPPED_REQUEST_HEADERS = Object.freeze([
  "cf-access-client-id",
  "cf-access-client-secret",
  "cf-access-jwt-assertion",
  "host",
  "x-pyeconomics-edge",
]);

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
    detail: "The staging edge Worker is missing required configuration.",
  });
  return new Response(body, {
    status: 503,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/problem+json",
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

export default {
  async fetch(request, env) {
    return forwardRequest(request, env);
  },
};
