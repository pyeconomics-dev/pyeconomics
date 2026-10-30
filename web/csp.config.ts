// web/csp.config.ts
// ADR-0013 decision 9: the one Content Security Policy every page shares, and
// the headers that travel with it. astro.config.ts gives Astro the directives
// it writes into each page's <meta> policy; scripts/headers.ts writes the same
// directives, with the union of every page's hashes, into dist/_headers. This
// file is the only place a source is added: the analytics collector (Step 15),
// Sentry's ingest origin (Step 14) and the email processor's form endpoint
// (Step 15) join here, and the post-build check refuses anything decision 9
// does not allow.

/** A directive's sources, in the order they are written. */
export type Sources = readonly string[];

/**
 * Every directive of the policy, in the order the header writes them. Astro
 * appends each page's hashes to script-src and style-src.
 */
export const DIRECTIVES: Readonly<Record<string, Sources>> = {
  "default-src": ["'self'"],
  "script-src": ["'self'", "'wasm-unsafe-eval'"],
  "style-src": ["'self'"],
  "img-src": ["'self'", "data:"],
  "font-src": ["'self'"],
  "connect-src": ["'self'"],
  "worker-src": ["'self'", "blob:"],
  "form-action": ["'self'"],
  "frame-ancestors": ["'none'"],
  "base-uri": ["'none'"],
  "object-src": ["'none'"],
  "upgrade-insecure-requests": [],
};

/** Directives a <meta> policy cannot carry; they travel only as a header. */
export const HEADER_ONLY: ReadonlySet<string> = new Set(["frame-ancestors"]);

/** Directives whose sources Astro fills from its own configuration. */
export const HASHED: ReadonlySet<string> = new Set(["script-src", "style-src"]);

/**
 * The sources decision 9 allows in each directive beyond the hashes. The
 * post-build check fails on any other source, so a later step that needs one
 * amends decision 9 and this table together.
 */
export const ALLOWED: Readonly<Record<string, Sources>> = {
  "default-src": ["'self'"],
  "script-src": ["'self'", "'wasm-unsafe-eval'"],
  "style-src": ["'self'"],
  "img-src": ["'self'", "data:"],
  "font-src": ["'self'"],
  "connect-src": ["'self'", "https://gateway.umami.is"],
  "worker-src": ["'self'", "blob:"],
  "form-action": ["'self'", "https://buttondown.com"],
  "frame-ancestors": ["'none'"],
  "base-uri": ["'none'"],
  "object-src": ["'none'"],
  "upgrade-insecure-requests": [],
};

/** Sources no directive may hold, whatever a later edit adds above. */
export const FORBIDDEN: Sources = [
  "'unsafe-inline'",
  "'unsafe-eval'",
  "'unsafe-hashes'",
  "'strict-dynamic'",
  "*",
  "http:",
  "https:",
];

/**
 * The directives Astro writes into every page's <meta> policy, beside the
 * script-src and style-src it builds itself.
 */
export function metaDirectives(): string[] {
  return Object.entries(DIRECTIVES)
    .filter(([name]) => !HEADER_ONLY.has(name) && !HASHED.has(name))
    .map(([name, sources]) => [name, ...sources].join(" "));
}

/**
 * Every feature a page may use is denied: the site needs none of them.
 * Only features Chromium recognizes are listed, because an unknown one logs a
 * console error.
 */
export const PERMISSIONS_POLICY = [
  "accelerometer=()",
  "autoplay=()",
  "camera=()",
  "display-capture=()",
  "encrypted-media=()",
  "fullscreen=()",
  "geolocation=()",
  "gyroscope=()",
  "magnetometer=()",
  "microphone=()",
  "midi=()",
  "payment=()",
  "picture-in-picture=()",
  "publickey-credentials-get=()",
  "screen-wake-lock=()",
  "usb=()",
  "xr-spatial-tracking=()",
].join(", ");

/** The headers every page and asset gets beside the policy (decision 9). */
export const SECURITY_HEADERS: Readonly<Record<string, string>> = {
  "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": PERMISSIONS_POLICY,
  "Cross-Origin-Opener-Policy": "same-origin",
};

/** Hashed build assets never change at a URL (decision 7). */
export const IMMUTABLE = "public, max-age=31536000, immutable";
