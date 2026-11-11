// web/src/lib/analytics.ts
// The cookie-less analytics tag (Phase 5 Step 15; ADR-0013 decision 13):
// Umami's tracker, vendored at web/vendor/umami/script.js and pinned by its
// SHA-256, served from our own origin in production builds only, posting to
// Umami Cloud's collector. The tag excludes the URL's query and fragment (and
// the referrer's, which the tracker passes through the same filter), honours
// Do Not Track, records only on the production host, and leaves error capture
// off. Custom events go only through src/lib/events.ts.
import { UMAMI_COLLECTOR } from "../../csp.config.ts";

/** The vendored tracker, relative to web/. */
export const TRACKER_SOURCE = "vendor/umami/script.js";

/** Its SHA-256: a new copy moves this and vendor/umami/README.md together. */
export const TRACKER_SHA256 = "c11c9d29ac15ee26ef07059add176fd7db95acbf8e8bdb1a79796b0ffdb58f18";

/** Where a production build serves it: a new copy is a new URL. */
export const TRACKER_PATH = `/vendor/umami-${TRACKER_SHA256.slice(0, 8)}.js`;

/** The one host whose visits are recorded. */
export const PRODUCTION_HOSTNAME = "pyeconomics.dev";

/** The tracker tag's attributes, for the website id a production build carries. */
export function trackerAttributes(websiteId: string, host: string = UMAMI_COLLECTOR): Record<string, string> {
  return {
    src: TRACKER_PATH,
    "data-website-id": websiteId,
    "data-host-url": host,
    "data-domains": PRODUCTION_HOSTNAME,
    "data-exclude-search": "true",
    "data-exclude-hash": "true",
    "data-do-not-track": "true",
  };
}
