# Umami's tracker, vendored

`script.js` is Umami Cloud's tracker (MIT, `LICENSE` beside it), byte for byte
as `https://cloud.umami.is/script.js` served it on 2026-11-11, the newest Umami
release then being v3.4.1. Its SHA-256 is pinned in `web/src/lib/analytics.ts`
(`TRACKER_SHA256`), which `tests/unit/analytics.test.ts` checks, and its file
name in a production build carries the hash's first eight characters, so a new
copy is a new URL (ADR-0013 decision 13; Phase 5 Step 15).

Only a production build given `PUBLIC_UMAMI_WEBSITE_ID` serves it, copied into
`dist/` by `astro.config.ts`; staging, local and the app wheel's builds never do.
Pages load it from our own origin, and it posts to `https://gateway.umami.is`
through `data-host-url`.

What it does, read from this copy: it sets no cookie and writes no storage; it
reads one `localStorage` key, `umami.disabled`, a visitor's own opt-out; it
sends page views and the events `src/lib/events.ts` allows, with the screen
size, language, page title, hostname, URL and referrer, and with
`data-exclude-search` and `data-exclude-hash` the URL keeps neither its query
nor its fragment. Error capture (`data-errors`) stays off.

To move it: download the file again, read what changed, replace `script.js`,
and move `TRACKER_SHA256` and the date above in the same pull request. Never
edit the file by hand.
