// web/csp.config.ts
// ADR-0013 decision 9: the one Content Security Policy every page shares, and
// the headers that travel with it. astro.config.ts gives Astro the directives
// it writes into each page's <meta> policy; scripts/headers.ts writes the same
// directives, with the union of every page's hashes, into dist/_headers. This
// file is the only place a source is added: the analytics collector (Step 15),
// Sentry's ingest origin (Step 14) and the email processor's form endpoint
// (Step 15) join here, and the post-build check refuses anything decision 9
// does not allow. Sentry's origin joins connect-src in a production build that
// carries the browser DSN (sentryBuild) and in no other build: staging, local
// and the app wheel's build load no error tracking (decision 16).

/** A directive's sources, in the order they are written. */
export type Sources = readonly string[];

/**
 * Sentry's US ingest: the one origin the browser DSN may name (decision 15).
 * Organisation and project ids run to 16 digits today, so each takes up to 20.
 */
export const SENTRY_INGEST = /^https:\/\/o\d{1,20}\.ingest\.us\.sentry\.io$/;
const SENTRY_DSN = /^https:\/\/[0-9a-f]{32}@(o\d{1,20}\.ingest\.us\.sentry\.io)\/\d{1,20}$/;

/** The browser DSN a production build carries, and the origin it posts to. */
export interface SentryBuild {
  dsn: string;
  origin: string;
}

/**
 * Read PUBLIC_SENTRY_DSN, the browser project's DSN (public by design): null
 * without one. Only a production build may carry it, and only on Sentry's US
 * ingest, so a staging, local or app build that is handed one fails rather
 * than report from a page whose policy would refuse the request.
 */
export function sentryBuild(
  flavour: string | undefined = process.env.SITE_FLAVOUR,
  dsn: string | undefined = process.env.PUBLIC_SENTRY_DSN,
): SentryBuild | null {
  if (dsn === undefined || dsn === "") return null;
  if (flavour !== "production") {
    throw new Error("PUBLIC_SENTRY_DSN is for production builds only (SITE_FLAVOUR=production)");
  }
  const match = SENTRY_DSN.exec(dsn);
  if (match === null) {
    throw new Error("PUBLIC_SENTRY_DSN is not a Sentry DSN on the US ingest");
  }
  return { dsn, origin: `https://${match[1] ?? ""}` };
}

/** This build's browser DSN, read once. */
export const SENTRY = sentryBuild();

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
  "connect-src": ["'self'", ...(SENTRY ? [SENTRY.origin] : [])],
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

/**
 * Sources decision 9 allows by pattern: Sentry's ingest origin, which names
 * the account's organization (o<number>), so it cannot be listed above.
 */
export const ALLOWED_PATTERNS: Readonly<Record<string, readonly RegExp[]>> = {
  "connect-src": [SENTRY_INGEST],
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
