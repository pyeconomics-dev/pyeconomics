# Phase 5 Roadmap — Web App, Docs & Public Launch (1.0.0)

**Status:** In progress

## Overview

Phase 5 opens the launch gate. Phases 6 and 7 build on the stable 1.0.0
API this phase freezes, and run in parallel from it; Phase 7's batches
reach production's sitemap and hosted MCP server through the pipelines
built here; and Gate G3, the evidence that decides whether Phase 8 ever
starts, counts from the announcement this phase makes, with the instruments
it installs. None of that can start until the site, the documentation and
the production service are live, legally sound and observable, and `pip
install pyeconomics` installs 1.0.0. The phase builds the Astro site in
`web/` — a prerendered page and a calculator for every model, navigation,
search and a coverage matrix, a data explorer, and in-browser handling of
users' files — and serves the same site locally through `pyeconomics serve`
and a `pyeconomics-app` wheel; it replaces staging's per-request fetches
with a scheduled snapshot data plane; it finishes the Sphinx documentation
for 1.0; it stands up production on Cloud Run behind Cloudflare with error
tracking, telemetry, uptime checks, a status page and runbooks; it
publishes the legal and trust pages and starts the permissions programme;
and it launches 1.0.0 behind a readiness gate after a seven-day production
soak of `1.0.0rc1`. It adds no model and no provider (Phases 7 and 6),
takes no account, API key or payment (Phase 8) — the "Pro" page is a fake
door that sells nothing — and lets no licensed or library-only data reach
the hosted site. It is one phase because the launch is one irreversible
event: the site, the docs, production and the legal pages go live
together, or the launch is not ready.

The phase lands in 20 layers:

1. **Launch baseline** — lands this roadmap and the refreshed planning kit,
   moves `main` to `1.0.0rc1.dev1`, and closes the findings production must
   not inherit: the verifiers' fail-open under an old bash (#217) and their
   Windows line endings (#213), actionlint in the gate (#212), staging's
   rollback that strands the next deploy (#210) and its project-wide deploy
   role (#211).
2. **ADR-0013** — writes `docs/adr/0013-web-app-and-launch.md`, twenty
   decisions the maintainer accepts or amends in the pull request, from the
   canonical domain and the one-Worker topology to the snapshot store, the
   Content Security Policy, the vendors, the soak and the growth gates, and
   amends the parent roadmap where it changes it.
3. **Web foundation** — the Astro project in `web/` with React islands,
   TypeScript, Tailwind, shadcn/ui and KaTeX; the layout and its notices;
   the site data exported from the registry; a strict Content Security
   Policy built from Astro's hashes into `_headers`; ESLint with security
   rules, Vitest, Playwright with axe, Lighthouse CI, audits and a bundle
   licence check in a required `web` job.
4. **Staging site** — one Cloudflare Worker serving the site from static
   assets and forwarding only the API's paths to Cloud Run, on
   `staging.pyeconomics.dev` behind Access, deployed after the API by every
   merge, with rollback and an hourly probe.
5. **Generated model pages** — a page for every model at its permanent URL
   with formula, variables, assumptions, limitations, evidence, citations,
   data and a worked example; a page for every problem type, so the
   problem URIs resolve; JSON-LD, Open Graph images, the sitemap, indexing
   rules by version and a ledger of shipped pages.
6. **Calculators and web parity** — a schema-driven form on every page with
   precompiled validators, results with their sources, charts from a
   TypeScript port of the library's figures, every download, live data
   where hosted mode can serve it, snippets for Python, the CLI, curl and
   MCP, and parity: every golden case returns the Python API's bytes
   through the calculator's own request path.
7. **Navigation, search and coverage** — fifteen domain sections, Pagefind
   search, the syllabus seed in `syllabi/` with neutral filters, related
   models and the public coverage matrix.
8. **Snapshot data plane** — a daily Cloud Run job that snapshots the
   hosted-safe originators into a private bucket, and a reader that serves
   hosted series and bound runs from it, refusing what is outside the set
   and degrading to the last good data, on staging first.
9. **Data explorer and user data** — `/data/` to find, transform, chart and
   download the series hosted mode serves, a transform option shared by
   every surface, and users' CSV and XLSX files parsed in the browser, with
   a network-log test proving they never leave it except as run values.
10. **Local app** — the `pyeconomics-app` wheel in a uv workspace, the
    `[app]` extra, `pyeconomics serve` hosting the same site with every
    local source, and a release workflow that publishes both distributions
    in lockstep.
11. **Documentation guides** — the tutorial track, how-to guides for pandas,
    R, Excel and xlwings Lite, syllabus study paths and the 0.2.x to 1.0
    migration guide.
12. **Documentation learning content** — an executed gallery, in-browser
    examples on marimo's WebAssembly export and the Python-for-finance
    tutorials.
13. **Production platform** — the production project, API, snapshot job
    and site on `pyeconomics.dev`, private behind Access, deployed by a
    release tag that promotes the staging-verified image through data, API
    and site with rollback at each layer.
14. **Observability and operations** — Sentry, OpenTelemetry to Grafana
    Cloud, Better Stack monitors and heartbeats, a status page, an hourly
    synthetic check, every alarm fired once, and the production runbooks.
15. **Growth signals** — Discussions, the newsletter and the waitlist
    through one processor, the priced Pro preview, cookie-less analytics
    with allowlisted events and a weekly Gate G3 ledger.
16. **Legal, trust and brand** — terms, privacy policy, disclaimers, the
    data-sources and licence pages, `security.txt`, the attribution audit,
    the permissions letters, the trademark clearance record and the
    counsel packet.
17. **Release candidate** — the public-API inventory pinned by a test, a
    TestPyPI rehearsal, `1.0.0rc1` of both distributions on PyPI, and a
    seven-day production soak behind Access.
18. **Launch readiness gate** — `docs/releases/1.0.0-readiness.md`:
    soak, web quality, legal, counsel, rollback, load, security and growth
    evidence, ending in the maintainer's GO or NO-GO.
19. **Cutover and 1.0.0** — `v1.0.0` on PyPI, the site opened to everyone,
    the redirects, Read the Docs' `stable` at 1.0, the MCP Registry's remote
    entry, 0.2.x's end of life and the post-launch verification.
20. **QA + `verify-phase05.sh`** — `scripts/verify-phase05.sh` (`--fast`,
    `--python`, `--node`, `--container`, `--security`, `--live`, `--all`,
    `--post`), `docs/phase05-qa-findings.md`, matrix entry `05` in
    `.github/workflows/phase-verify.yml`, and the alarm re-fired on the
    public path.

The ship test for Phase 5 is straightforward: issues #210, #211, #212,
#213 and #217 are closed with their guards; ADR-0013 is Accepted; every
registered model has a prerendered page listed in the sitemap, and
Lighthouse scores at least 90 for performance, accessibility, best
practices and SEO on the thirteen-page sample ADR-0013 decision 19 fixes,
with no WCAG 2.2 AA violation under axe; every golden case returns the
Python API's canonical bytes through the calculator's request path, and
the parity check passes through the deployed API; hosted series come only
from snapshots, and a source not hosted-safe never reaches the hosted site,
its snapshots or its downloads; users' files never leave the browser
except as run values (a code check and a network-log test); `pip install
pyeconomics` installs 1.0.0, and `pip install "pyeconomics[app]"` then
`pyeconomics serve` serves the same pages locally with library-only sources
available; the documentation's guides, gallery, in-browser examples and
migration guide build with warnings as errors, and Read the Docs `stable`
serves 1.0; production `/version` reports the 1.0.0 SHA, a synthetic check
runs one model per domain and downloads a CSV carrying its attribution,
the snapshot heartbeat is green, and every alarm has fired once; an OWASP
ZAP baseline scan finds no High issue, the MDN HTTP Observatory verifies
the CSP, HSTS and frame-ancestors, the privacy policy matches the actual
data flows, and waitlist emails sit only with their processor under least
privilege; Gate G2's instruments record, and the Gate G3 window opens on
the announcement; and `scripts/verify-phase05.sh --fast` exits 0 on Ubuntu
CI with the `phase-verify.yml` matrix entry `05` green.

**Pre-requisite:** Phase 4 is closed — V1–V16 green on 2026-10-29 (PR
#214), `1.0.0b1` on PyPI with attestations and in the MCP Registry, staging
on Cloud Run behind the Cloudflare edge with its health alarm and budget
notification proven, and `main` protected with 24 strict required checks.
Its registry export is what the pages render, its REST API and generated
TypeScript client are what the calculators call, its parity suite is what
the web joins, its exports are what the downloads offer, its MCP server is
the hosted endpoint this phase opens, its image and staging deploy are
what production promotes, and `verify-phase04.sh` is the template for
`verify-phase05.sh`. The operator holds admin on the GitHub repository and
the Owner role in the `pyeconomics-dev` organization, owner rights with 2FA
on PyPI (to register `pyeconomics-app`'s pending publishers), the `pypi`,
`testpypi`, `mcp-registry` and `staging` environments' review, and admin on
the Read the Docs project; holds the Google Cloud billing account (with
room for a production project, or a quota increase requested at Step 13's
kickoff), the Cloudflare account with the four domains and Zero Trust's
free plan, and the Upstash account; creates during the phase, each on a
free tier where one exists and with the project's address, the Sentry,
Grafana Cloud, Better Stack, analytics and email-processor accounts; has
the GitHub CLI with the `repo` and `workflow` scopes, gcloud, Node.js 24
and Claude Code on the machine that runs `--live` and `--post`; and
engages counsel and a trademark clearance search by Step 16, the outside
parties whose answers the readiness gate records.

**Dependency:** Phases 6 and 7 do not start until V1–V20 are green and
1.0.0 is live; they then run in parallel worktrees (ROADMAP §5 "Sequencing
& dependencies"). They inherit a frozen public API whose every change
follows ADR-0003, a site and documentation that render new models and
providers with no page code, production and its snapshot set, which grow
with each hosted-safe source, the parity suite with its web surface, and
the release workflow for both distributions. Phase 6 adds the local app's
key settings page and BYOK providers that stay off the hosted site; Phase 7
fills the coverage matrix and the other syllabi in `syllabi/`. Phase 8
starts only if Gate G3 passes on the evidence this phase's instruments
record over the window it opens.

**Design rationale (staged, then launched).** The order inside the phase is
the design. Step 1 removes what production would otherwise copy from
staging — a rollback that strands the next deploy, a project-wide role, a
verifier that can pass without running — before anything reuses them.
ADR-0013 then fixes every decision the launch encodes (Step 2), because
several become public API or public promises at 1.0.0: the domain, the
page URLs, the problem URIs, the privacy promises. The web toolchain and
its security headers come first among the build steps (Step 3), and a real
Cloudflare edge follows at once (Step 4), so a header, a CSP violation or a
routing mistake shows up on staging in the step that causes it. Pages,
calculators and navigation follow the registry's shape (Steps 5–7). The
data plane lands before the explorer that reads it (Steps 8–9): data, then
API, then site, as ROADMAP §5's staged-rollout rule asks. The local app
packages a finished site and teaches the release workflow its second
distribution well before the candidate needs it (Step 10). The
documentation describes surfaces that exist (Steps 11–12). Production is
built private (Step 13), made observable with every alarm proven (Step 14)
and instrumented for demand (Step 15) before the legal pages are written
against the data flows that now exist (Step 16). The release repeats the
rehearse-then-release pattern of every earlier phase, with a soak in
production between the candidate and the gate (Steps 17–18), because a
stable PyPI release cannot be unpublished and a public launch cannot be
taken back; the cutover is a decision recorded in its own step (Step 19).

**ADR-0013's decisions (drafted defaults).** Step 2 writes these as the
ADR's decisions with the defaults below, each with its alternatives and
sources; the maintainer accepts or amends each in the pull request. A
decision this roadmap's steps encode is never reopened in a later step
except by a superseding ADR.

1. **Canonical domain.** `pyeconomics.dev` serves the site, the API and the
   MCP endpoint on one origin; `www.pyeconomics.dev`, `pyeconomics.com`,
   `.org` and `.io` answer 301 to the same path on it through Cloudflare
   Single Redirects, enabled at the cutover, and `.io` is never canonical
   (ADR-0009). The problem-type URIs already name `pyeconomics.dev` and
   become public API at 1.0.0; `.dev` is HSTS-preloaded; the name matches
   the GitHub organization. Alternative: `.com` canonical, with the problem
   URIs redirecting for ever.
2. **Site layout and URLs.** `web/` is an Astro project with its own Node
   project and lockfile beside `tools/node/` (the dev-tooling workspace);
   build data comes only from `scripts/web/export_site_data.py`. Pages:
   `/models/<domain>/<name>/` from the model id with underscores as hyphens
   (a bijection, since ids hold no hyphen), `/models/<domain>/`, `/data/`,
   `/search/`, `/coverage/`, `/sources/`, `/problems/<slug>/`,
   `/legal/<page>/`, `/pro/`, `/newsletter/` and `/version.json`, with
   trailing slashes; no path segment or query value names a mark; a shipped
   page never disappears (`web/released-pages.json`; retired URLs
   redirect); Open Graph images come from `astro-og-canvas` (MIT) at build
   time. Alternative: snake_case paths mirroring the ids.
3. **One host, one Worker.** Workers static assets serve the site; one
   Worker — ADR-0012 decision 20's, extended — runs first only on `/v1/*`,
   `/mcp`, `/healthz`, `/version` and `/openapi.json` and forwards them to
   Cloud Run with the edge credential, so no Worker code sits in the page
   path (ADR-0006). Same origin, so no CORS and `connect-src 'self'` for
   the API. Asset requests are free and unlimited; the Worker's 100,000
   free requests a day bound API traffic ahead of the origin's limits. The
   Free plan's one rate rule matches the API's paths on every host.
   Alternatives: an `api.` subdomain (CORS) or Cloudflare Pages (Cloudflare
   now starts new projects on Workers).
4. **Environments.** Every pull request builds and tests the site without
   deploying; every merge deploys staging — the API, then the site on
   `staging.pyeconomics.dev` behind Access — through `deploy-staging.yml`,
   ROADMAP §5's "preview"; a release tag, approved in the protected
   `production` environment, deploys `pyeconomics.dev`, behind Access until
   Step 19 removes it. `staging-api.pyeconomics.dev` stays as staging's
   API-only edge. Alternative: per-PR version URLs (public on workers.dev
   unless protected, with no API behind them).
5. **Production on Google Cloud.** A separate project,
   `pyeconomics-production`, in `us-central1`: the service `pyeconomics-api`
   at minimum 0 and maximum 3 instances, request-based billing with CPU
   throttling, concurrency 8; images promoted by digest from staging, never
   rebuilt; Workload Identity Federation bound to the repository id, the
   `production` environment and `main` or `v*` refs; the deploy identity's
   role on the service alone (#211); deploys restore latest traffic
   (#210); its own Upstash database, edge credential, Access service token
   and Cloudflare token; a $10 monthly budget with 50/90/100% alerts.
   Alternative: production in the staging project (one blast radius).
6. **Snapshot data plane.** A Cloud Run job — the same image in hosted mode
   — runs daily at 23:30 UTC, after the US end-of-day series publish, and
   writes one gzip-compressed canonical-JSON object per provider and run
   (the cache's frame codec, validated on read) and `current.json` last,
   into a private, versioned Cloud Storage bucket mounted read-write into
   the job and read-only into the service. Cloud Storage volume mounts are
   GA for both, so no key, no request signing and no network code outside
   `data/transport/`. The set is computed: every hosted-safe originator
   candidate, never FRED, an aggregator or a storage-forbidden series. A
   series outside it is refused (`not-in-snapshot`, 404, pointing to local
   mode); a snapshot older than two days is served with a `stale_snapshot`
   warning. Alternatives: Cloudflare R2, as ROADMAP §4 5.8 wrote, which
   needs a long-lived access key and signing code; Parquet objects, which
   would put a second parser on the hosted read path when the cache's
   codec already validates frames (pyarrow stays optional under ADR-0008
   decision 8). Step 2 amends the parent roadmap.
7. **Caching.** The edge Worker caches GET run responses with the Workers
   Cache API as the origin's `Cache-Control` allows (ADR-0012 decision 12:
   long for data-free runs, short for bound runs on storable hosted-safe
   data), because a zone's Cache Rules do not cache what a Worker fetches
   from an outside origin; POST runs and problems stay `no-store`;
   `/_astro/*` assets are immutable. No shared result cache: the
   in-process cache and the edge suffice at this scale.
8. **Calculators.** RJSF 6 with its shadcn/ui theme renders each model's
   own input schema, with validators precompiled at build time, so nothing
   is compiled in the browser; the island posts the inputs' JSON and renders
   the canonical bytes it receives; charts come from a TypeScript port of
   `figure_of`, held equal to `example_figure` for every model, on
   Plotly.js's basic bundle at the version the `[plot]` extra bundles;
   downloads use `?format=`; snippets for Python, the CLI, curl and MCP run
   in CI. The web joins the parity evidence: every golden case through the
   island's request builder, and `scripts/parity/check_deployed.py` through
   a deployed API. Alternative: hand-written forms per field type.
9. **Security headers.** One policy for every page, sent from `_headers`
   (and by the local server): `default-src 'self'`; `script-src 'self'
   'wasm-unsafe-eval'` with Astro's build-wide hashes; `style-src 'self'`
   with Astro's hashes; `img-src 'self' data:`; `font-src 'self'`;
   `connect-src 'self'` with the analytics collector and Sentry's ingest
   origin; `worker-src 'self' blob:`; `form-action 'self'` with the email
   processor; `frame-ancestors 'none'`; `base-uri 'none'`; `object-src
   'none'`; `upgrade-insecure-requests`; plus HSTS (two years, subdomains,
   preload), `X-Content-Type-Options`, `Referrer-Policy:
   strict-origin-when-cross-origin`, `Permissions-Policy` and
   `Cross-Origin-Opener-Policy: same-origin`. No `'unsafe-inline'` or
   `'unsafe-eval'`: KaTeX renders MathML, Plotly.js loads `plotly.css` with
   its no-inline-styles marker, and the site uses neither ClientRouter nor
   Shiki, which Astro's CSP does not support. `'wasm-unsafe-eval'` is the
   one concession, for Pagefind. The tracker is served from our origin.
   Verified by a post-build check, a Playwright CSP-violation listener, and
   the MDN HTTP Observatory (grade A or better) once the site is public.
   Alternative: a meta-tag policy alone, which cannot carry frame-ancestors.
10. **Search and navigation.** Pagefind (MIT) indexes the built site and
    searches in the browser; fifteen domain sections in ROADMAP §4 7.2's
    order, `micro` and `alternatives` as planned sections linking the
    coverage matrix; filters by domain, syllabus level and topic, evidence
    status, cost class, data needs and tag; related models computed at
    build time.
11. **Data explorer and user data.** `/data/` offers the catalog's concepts
    with each source's licence class and hosted availability, reads series
    through `/v1/series/`, draws attribution and as-of date on every chart,
    and downloads through `?format=`; transforms are the catalog's own
    single-series transforms through a new `transform` option on `data.get`,
    passed through the CLI, the REST route and MCP's `get_series`, so a
    transformed file carries the same attribution; hosted mode offers only
    the snapshot set; the explorer feeds models and never replicates a
    provider's product (ROADMAP §5 rule 5). Users' files: CSV through Papa
    Parse and XLSX through a maintained permissive reader chosen at Step 9's
    kickoff (never the unmaintained npm `xlsx`), parsed in a worker, capped
    at 5 MB and each field's `max_length`, sent only as run values.
12. **Syllabus seed and coverage matrix.** ROADMAP §4 5.3 asks for syllabus
    filters, and §4 7.1 creates the crosswalks; this phase creates
    `syllabi/` in 7.1's format (a JSON Schema and one TOML file per
    syllabus version) with one seed — the 2027 CFA® Program topic areas for
    Levels I to III, mapped to the fifty launch entries, factual names and
    links only, reviewed by the maintainer — and Phase 7 adds the other
    syllabi and the remaining coverage. Slugs and query values stay neutral
    until CFA Institute answers the URL question (Step 16). The coverage
    matrix is generated from the registry and `syllabi/`. Step 2 amends the
    parent roadmap.
13. **Analytics.** Umami Cloud's free Hobby plan: 100,000 events a month
    with custom events and properties, no cookies, and, by the vendor's
    own statement, no consent banner needed. The tracker is served from our
    origin at a pinned version and posts to Umami's collector; custom
    events come from a fixed allowlist whose properties never hold an
    input, value, query or address; production builds only. Alternatives:
    Plausible ($9 a month, EU-hosted) and GoatCounter (free for reasonable
    public use); Cloudflare Web Analytics is free but records no custom
    events, which Gate G2 needs.
14. **Email processor.** One processor for the newsletter and the
    waitlist: Buttondown — plain HTML forms that post straight to it with
    no key, a `metadata__tier` field for tier interest, double opt-in by
    default, a DPA, export and deletion — free to 100 subscribers and $9 a
    month to 1,000. Alternative: Kit (free to 10,000 subscribers; its
    tracking defaults need review). The maintainer chooses at Step 2.
15. **Errors, telemetry and uptime.** Sentry's free Developer plan for
    errors (`sentry-sdk` on the backend, `@sentry/browser` in the islands
    only; no personal data, no replay); OpenTelemetry metrics and sampled
    traces to Grafana Cloud's free tier through the project's own
    middleware (not the beta FastAPI instrumentation), flushed on shutdown;
    both from a `hosted` dependency group the image installs, never an
    extra. Better Stack's free plan for uptime monitors, the snapshot
    jobs' heartbeats (pinged through the data layer's transport, its host
    declared like a provider's) and the status page at
    `status.pyeconomics.dev`, or the vendor's subdomain if the free plan
    has no custom domain. An hourly `production-health.yml` and the budget
    alerts complete the alarms; each names its runbook.
16. **Local app.** `packages/pyeconomics-app/`, a uv workspace member whose
    wheel carries only the built site; `[app]` pins it to the same version
    and stays out of `[all]` (ADR-0002); `pyeconomics serve` mounts it at
    `/` behind the API's routes with the same headers and the loopback
    guard unchanged; locally the site offers live library-only data with
    the user's keys and the whole catalog.
17. **Public-API freeze.** Step 17 inventories the public surface in
    `docs/public-api.md` and pins it with a test derived from the code;
    after 1.0.0 every change follows ADR-0003. #197, the MCP tool list's
    size, stays a compatible 1.x change — slimmer schemas keep every tool
    name and its validation — unless the maintainer chooses to fix it
    before the freeze.
18. **Release, soak and end of life.** `release.yml` publishes both
    distributions through one Trusted Publishing exchange; the exact
    candidate is rehearsed on TestPyPI (`v1.0.0rc1.dev1`); `1.0.0rc1` goes
    to PyPI and to production behind Access for a seven-day soak with
    fixed criteria, during which only security fixes merge; 1.0.0 follows
    the gate's GO, its archives differing from the candidate's only in
    version metadata, with the Production/Stable classifier; 0.2.x reaches
    end of life (`legacy/0.2.x` locked, SECURITY.md updated); the MCP
    Registry gains the remote entry once the endpoint is public; Read the
    Docs' defaults move to `main` and `stable`.
19. **Launch measures and growth gates.** Lighthouse (median of three
    mobile runs, at least 90 in all four categories) and axe (WCAG 2.2 AA;
    no violation) on thirteen pages: `/`, `/models/`,
    `/models/fixed-income/`, `/models/fixed-income/bond-pricing/`,
    `/models/foundations/time-value/`, `/models/macro/policy-rule/`,
    `/models/econometrics/garch/`, `/data/`, `/search/`, `/coverage/`,
    `/sources/`, `/legal/privacy/` and `/problems/invalid-input/`. The
    OWASP ZAP baseline with no High finding; the Observatory at A or
    better; a Locust load test against staging whose month at 10,000 runs a
    day fits the production budget. Gate G2's signals — page views and the
    allowlisted events, sign-ups by list and tier, API and MCP requests by
    route kind, PyPI downloads and stars — written weekly as counts to a
    pinned "Gate G3 ledger" issue. Gate G3's window: the 90 days after the
    announcement, with ROADMAP §5's thresholds (1,000 sign-ups or 1,000
    activated users, a visitor who completes a run or a download; 30
    upgrade-intent clicks or pre-orders; 10 interviews), confirmed or
    adjusted by the maintainer at Steps 2 and 18.
20. **Legal readiness.** The terms (with the New York Fed's and the
    OECD's conditions passed through), the privacy policy generated from
    one data-flows file, the disclaimers (FINRA Rule 2214's and CFTC Rule
    4.41's statements as templates wherever simulated results appear), the
    data-sources and licence pages, `security.txt` (RFC 9116) and every
    chart's and file's attributions are live before launch. The
    permissions letters go out (the St. Louis Fed, Ken French, Robert
    Shiller, the IMF, the Philadelphia, Atlanta and Cleveland Feds, and CFA
    Institute on URL paths), and no launch item waits for an answer. Counsel
    reviews the pages and the licensing policy before launch (ROADMAP §5),
    and the trademark clearance search is recorded in ADR-0009; at the gate
    a missing outside item is a FAIL unless the maintainer waives it with a
    recorded reason.

Facts behind these decisions were read on 2026-10-29 and are re-read at
each step's kickoff, because they move. From Cloudflare's documentation:
static-asset requests on Workers are free and unlimited; a Free-plan
Worker serves 100,000 requests a day, and paths named in
`run_worker_first` always invoke it; `_headers` and `_redirects` apply to
asset responses only; the Free plan has one rate-limiting rule (path and
verified-bot fields, counted by IP), ten Single Redirect, Cache and
Transform rules each, the managed WAF ruleset on by default, and HSTS;
Cloudflare Web Analytics records no custom events. From Google Cloud's:
Cloud Storage volume mounts are GA for Cloud Run services and jobs;
Always Free covers 5 GB-months of Standard storage in `us-central1`;
Cloud Scheduler gives three free jobs per billing account. From Astro's:
`security.csp` is stable since Astro 6, hashes the island runtime and
every inlined script and style for the whole build, emits a meta element
(an adapter alone can emit headers), and supports neither ClientRouter
nor Shiki. From the vendors': Umami's Hobby plan, Buttondown's tiers,
Sentry's Developer plan (5,000 errors a month), Grafana Cloud's free tier
(10,000 series, 14-day retention) and Better Stack's free plan (ten
monitors and heartbeats, one status page, 3-minute checks) as decisions
13–15 state them.

**Web rules.** Five rules hold for every step from Step 3 on:

- **Generator rule.** The site gains a model only through the registry:
  no page, calculator, form or chart is written by hand for one model, and
  every model page, problem page and source entry is generated from the
  site data export, so Phase 7's models and Phase 6's providers appear
  with no web code.
- **Parity rule.** The canonical bytes stay the contract on the web: a
  calculator renders the bytes the API returns and downloads them
  unchanged, and the web parity suite (Step 6) fails on any difference.
  A presentation — a table, a chart, a summary — goes beside the bytes,
  never in their place.
- **One-policy rule.** Every page shares decision 9's Content Security
  Policy, built from Astro's hashes; no page, island or vendor loosens it,
  and the post-build check and the Playwright listener fail the build on a
  regression.
- **Bundle rule.** Nothing secret reaches the browser: no key, token,
  internal hostname or `*.run.app` origin in the bundle, the pages or the
  generated client; the only third-party origins a page talks to are those
  decision 9 names.
- **Browser-data rule.** A user's file is parsed in the browser and only
  the values a run needs travel, in its body; the site keeps no input in
  storage, the URL or analytics.

**Public-API rule.** ADR-0003 makes the Python API, CLI commands and
options, REST paths and schemas, MCP tool names and schemas, problem slugs
and type URIs, `registry.json`'s format, the export formats, the settings,
the extras and — from this phase — the site's page URLs public API at
1.0.0. Steps 2 to 16 may still change them (each change listed in the next
release notes); Step 17 freezes them in `docs/public-api.md` with a test;
after 1.0.0 a change follows ADR-0003, and a breaking one needs 2.0.0.

**Licence rule.** The hosted site serves only `hosted-safe` and
`user-supplied` data: hosted mode refuses every other class before a
snapshot is read or a request is made, the snapshot set excludes FRED,
every aggregator, every library-only source and every series whose terms
forbid storage, and the explorer offers only what the snapshot set holds.
Every chart, table, download and manifest carries its source's attribution
and required notices (ROADMAP §5 "Data licensing policy" rule 2), tested
per provider; FRED's notice appears on local surfaces only. A permission
granted through the programme (Step 16) is a reclassification in its own
pull request, never a side effect; a source whose terms change is a High
defect whose snapshots are purged.

**Privacy rule.** The phase handles three data classes ROADMAP §5 assigns
to it, each with one destination: waitlist and newsletter emails go only to
the email processor, through forms that post straight to it, with double
opt-in, least-privilege access and deletion on request; analytics is
cookie-less and aggregate, with allowlisted events; user uploads stay in
the browser. Telemetry — errors, traces, metrics, logs — carries route
templates and outcomes, never a personal datum, an input, an address or a
key. The privacy policy is generated from one data-flows file that a test
holds equal to the processors and logs the service really uses.

**Credential rule.** Users' keys never transit a surface, as in Phase 4.
The service's own secrets — production's edge credential and rate-limit
URL, the snapshot jobs' provider keys, the telemetry tokens, the heartbeat
URLs — live in Secret Manager only; CI's — the Cloudflare API tokens, the
Access service tokens, the growth ledger's read tokens — live only as
environment secrets of protected environments (`staging`, `production`,
`growth`), never as repository secrets (Phase 1 V10.5). The maintainer
sets every value with a command the step prints (`gh secret set <NAME>
--env <environment>`, `gcloud secrets versions add <name> --data-file=-`,
`npx wrangler secret put <NAME> --env <environment>`), each of which
prompts for or pipes the value; a value never transits chat, a pull
request or a log. A shared secret is proven by an authenticated
round-trip. Production shares no secret with staging. No session prints,
echoes, logs or pastes a key or an environment value (AGENTS.md "Never
print secrets").

**Version rule.** Step 1 moves `main` from `1.0.0b1` to `1.0.0rc1.dev1`.
Step 17 tags `main`'s head `v1.0.0rc1.dev1` to rehearse the exact
candidate on TestPyPI (a failed rehearsal is a NO-GO: the fix lands on a
`fix/` branch that moves `main` to the next `.devN`, and the rehearsal
repeats), then sets `1.0.0rc1` and tags it. Step 19, after the gate's GO,
sets `1.0.0` and tags it; a NO-GO makes the next candidate `1.0.0rc2`.
`pyeconomics-app` always carries the same version as `pyeconomics`, and
`CITATION.cff` and `server.json` follow `pyproject.toml` at every commit.
This phase changes no model's outputs, so no model version moves; a step
that finds it must change one follows ADR-0003 (a new model version, a
changelog entry on the card and an erratum).

**Dependency rule.** Every Python dependency Phase 5 adds — to an extra,
the `hosted` or `load` group, or the docs group — is added with `uv add
--no-config` (and `uv lock --no-config`, `uv export --no-config`) and
passes `pip-audit`; anything the service runs (the `hosted` group
included) also passes the ADR-0004 licence allowlist. pyarrow and Polars
stay out of every extra (ADR-0008 decision 8). `web/` is the site's own
Node project with a committed lockfile, `npm ci`, `npm audit
--audit-level=high` in the gate and Dependabot's `npm` ecosystem; the
packages the site ships to browsers pass a permissive licence allowlist
(MIT, BSD, Apache-2.0, ISC, 0BSD), while build- and test-only tools sit
outside it, as Python's dev tools do. TypeScript stays on 6.0 in both Node
projects while `astro check` refuses 7, and Node 24 runs the web job.
Facts read from npm and PyPI on 2026-10-29; the hooks and the lockfiles at
step time are the authority:

| Package | Latest | Licence | Use (step) |
| --- | --- | --- | --- |
| astro, @astrojs/react | 7.4.4, 7.1.2 | MIT | site and islands (3) |
| @astrojs/check, typescript | 0.9.12, 6.0.3 | MIT, Apache-2.0 | types (3) |
| react, react-dom | 19.3.1 | MIT | islands (3) |
| tailwindcss, shadcn | 4.3.3, 4.23.0 | MIT | styles, components (3) |
| katex | 0.19.1 | MIT | formulas at build time (3) |
| @rjsf/core, utils, validator-ajv8 | 6.11.0 | Apache-2.0 | forms (6) |
| @rjsf/shadcn | 6.11.0 | MIT | form theme (6) |
| plotly.js-basic-dist-min | 4.1.2 | MIT | charts, pinned to 4.1.1 (6) |
| pagefind | 1.5.2 | MIT | search (7) |
| @astrojs/sitemap, astro-og-canvas | 3.7.4, 0.13.2 | MIT | pages (5) |
| vitest, @playwright/test | 5.0.5, 1.64.1 | MIT, Apache-2.0 | tests (3) |
| @axe-core/playwright | 4.14.0 | MPL-2.0 | tests only (3) |
| @lhci/cli | 0.15.1 | Apache-2.0 | Lighthouse 12.6.1 (3) |
| eslint, eslint-plugin-security | 10.13.0, 4.2.0 | MIT, Apache-2.0 | lint (3) |
| wrangler | 4.155.0 | MIT OR Apache-2.0 | deploy, local edge (3) |
| @sentry/browser | 11.10.0 | MIT | browser errors (14) |
| @mdn/mdn-http-observatory | 1.7.2 | MPL-2.0 | header scan only (19) |
| sentry-sdk | 2.73.0 | MIT | `hosted` group (14) |
| opentelemetry-sdk, OTLP exporter | 1.45.2 | Apache-2.0 | `hosted` group (14) |
| sphinx-gallery | 0.22.1 | BSD-3-Clause | docs group (12) |
| marimo | 0.25.2 | Apache-2.0 | docs group (12) |
| locust | 2.47.0 | MIT | `load` group (18) |

**Wheel rule.** Unchanged from Phase 4: CI runs Python 3.12–3.15 on
Ubuntu, Windows and macOS, so a Python dependency installs from a wheel,
or is pure Python, on every cell; a candidate without one is replaced,
implemented natively or, for an optional group with the maintainer's
approval, gated by `python_full_version < '3.15'` with the gap asserted and
an issue opened. `pyeconomics-app` is pure Python with static files, so it
installs everywhere; the `hosted` group needs only the image's Python 3.14.

**Cross-phase verification rule.** `phase-verify.yml` runs
`verify-phase01.sh` to `verify-phase04.sh` (`--fast` and `--security`) on
every Phase 5 pull request, and those checks were written against earlier
trees. When a Phase 5 change legitimately invalidates one, the same pull
request narrows the check to the invariant it was protecting, never
deletes it, and appends a line to a `## Post-merge addendum (<YYYY-MM-DD>)
— Phase 5 changes to verify-phase0N.sh` section at the end of that phase's
roadmap. The ones this roadmap foresees:

| Check | What it pins today | Step |
| --- | --- | --- |
| Phase 3 check 78, 4 check 64 | workflows reading secrets | 4, 13–15, 18 |
| Phase 2 and 4 package checks | one wheel and one sdist | 10 |
| Phase 4 check 58 | the README names `1.0.0b1` | 19 |
| Phase 1 V4.4, 2 V7.3, 3 V11.3, 4 V15.2 | `stable` docs are 0.2.6 | 19 |
| Phase 2 V14.3, 3 V19.3, 4 V15.3 | a plain install gets 0.2.6 | 19 |
| Phase 1 check 36 | id-token on two publish jobs | none |
| Phase 1 checks 17, 18 and 21 | ADR index; no `cfa` names | none |
| Phase 1 V10.5 | no repository secret | none |

**Contract-change rule.** Steps 3–19 build on contracts Phases 3 and 4
fixed. A step that cannot be completed without a contract change makes it
in-step (Triage rule: an upstream gap that blocks the step): the smallest
change that works, every surface, golden case and snapshot kept green, the
owning step's `<task>` block patched and the change added to the
carry-over checklist in this file's last section. This roadmap foresees
three, each additive: the snapshot reader in the data layer and its
`not-in-snapshot` error row (Step 8), `data.get`'s `transform` option on
every surface (Step 9), and the server's static mount for the local app
(Step 10). A change to a decision an Accepted ADR records is a superseding
ADR in the same pull request, because an Accepted ADR is never edited
(`docs/adr/README.md`).

**Branch strategy.** Every step in this phase lands on its own short-lived
feature branch (`feature/phase05-step<M>-<slug>`), opens a pull request
against `main`, waits for the project's CI workflow to go green, and
squash-merges with a Conventional Commits subject line. Direct pushes to
`main` are blocked by branch protection. See the parent project's ROADMAP
"Branch management strategy" section for the canonical naming convention,
PR rules, and release tagging — this paragraph confirms those rules apply
unchanged within this phase. Per-step branches are listed on each step
header below as `**Branch:**` so reviewers can map commits 1:1 to the step
they implement.

**Branch-first execution rule.** The very first action of every step —
before reading any files, before running any tool, before drafting any
change — is to check out the branch named in that step's `**Branch:**`
line:

```sh
git checkout -b feature/phase05-step<M>-<slug>
```

This is non-negotiable. `main` is protected with `enforce_admins: true`, so
a commit on `main` cannot be pushed and must be rewound or rebased onto the
feature branch before the PR can open — an avoidable round-trip. If you
discover mid-step that you started on `main`, recover by running the same
`git checkout -b` command immediately (uncommitted changes carry over to the
new branch), then continue. AI coding agents executing a step from this
roadmap must treat the branch checkout as Step 0 of every step. Step 1
starts with this roadmap and the refreshed planning kit uncommitted in the
tree; they carry over to its branch and become its first two commits.

**Worktree rule.** One working tree, one step in flight — the lifecycle
below assumes the primary checkout. A second working tree is created only
with `git worktree add`, and only for the three cases the parent ROADMAP
"Worktree strategy" sanctions: a `hotfix/` branch interrupting this step
(cut from `origin/main` in its own worktree so this step's tree is
untouched); steps the Execution Order below explicitly draws in parallel
(each in its own worktree AND its own conversation); and worktree-isolated
subagents inside a step (throwaway trees that merge back into the step
branch locally and are removed before the PR opens). In those cases Stage 1
becomes `git fetch origin && git worktree add -b
feature/phase05-step<M>-<slug> <worktree-path> origin/main`, the worktree
is bootstrapped before any test or build (fresh dependency install and env
files — a worktree has none of the primary tree's untracked state, and it
must never borrow the primary tree's editable install), the Stage 4 merge
runs from the primary tree, and Stage 5 removes the worktree BEFORE pruning
the branch. Undeclared parallelism is a lifecycle violation, not a
shortcut. Worktree location for this project: git-ignored
`.worktrees/<branch-slug>/` inside the repository, matching the parent
ROADMAP; bootstrap with `uv sync --locked` inside it, `npm ci
--ignore-scripts` in `tools/node/` and, from Step 3, `npm ci` in `web/`.

**Security-first execution rule.** Security is not a phase — it is a gate
on every commit of every step. Before each `git commit`, the step's work
must pass the local, fail-closed security gate: secret/PII scan clean, SAST
clean, dependency audit clean, and a diff review confirming no sensitive
data (PII, credentials, tokens) and no new insecure pattern (injection,
weak crypto, over-broad scope, secret in a client bundle or log line). This
gate is wired into the pre-commit hook (prek) and re-run in CI, so a
security issue introduced while implementing a step is caught during
development — before it reaches the branch, the PR, or `main`. See the
parent project's ROADMAP "Security & privacy strategy" → "Per-step security
gate" for the canonical checks and tooling; each step's XML `<task>`
carries a `<security>` block restating them for the agent, and each step's
Acceptance Criteria ends with a security check. AI coding agents executing
a step MUST treat the security gate as part of the step's definition of
done, exactly like its tests. Phase 5 opens the project's first public
ingress and its first client bundle, so its exposures are a secret or a key
in the site bundle, a page or a log (ROADMAP §5 threat 1); cost exhaustion
of production through floods, expensive inputs or the snapshot job
(threat 2); cross-site scripting through model text, user files or a
third-party script, which the Content Security Policy must contain;
unsafe parsing of users' CSV and XLSX files in the browser and of snapshot
objects on the server (threat 3); licensed data escaping to the hosted
site, its snapshots or its downloads (threat 4); a malicious release, image
or site deploy (threat 5); formula injection in downloads (threat 6); and
personal data — waitlist emails, analytics, telemetry — collected beyond
what the privacy policy says, kept by more than one processor, or written
to a log.

**Deploy-and-verify rule.** Merged is not deployed, and deployed is not
released. Every step header carries a `**Deploys:**` line naming the
surface and environment the step's merge reaches — or `nothing beyond
merge` — and when going live needs a release, a version-floor bump, a
migration, or a redeploy, the line says so and this step (or a named
follow-on step) owns that event. For a step whose Deploys line names a
surface, Stage 4 of the lifecycle does not end at the squash-merge: the
step's acceptance criteria carry a **Deployed & verified** bullet (the
surface's version/health endpoint reports this build, and the changed
behaviour is exercised in the target environment with real authentication
via the hands-off recipe the step names), and that bullet must be green
before the step is declared complete. In Phase 5 the surfaces are the
staging API (every merge to `main`, `deploy-staging.yml`), the staging site
on `staging.pyeconomics.dev` (every merge to `main` from Step 4, the same
workflow's `site` job), the staging snapshot job (Step 8), production — the API,
the snapshot job and the site on `pyeconomics.dev` — deployed by a release
tag behind the protected `production` environment (from Step 13), the
Read the Docs `main` build and, at the cutover, `stable`, TestPyPI and PyPI
for both distributions, the MCP Registry, and the monitors (Step 14).
Their hands-off recipes are a push or `workflow_dispatch` run read back
with `gh run view`; a request through the edge with the Cloudflare Access
service token read from the maintainer's keyring (`/version` and
`/version.json` report the SHA; a page answers with its security headers; a
run equals the wheel's bytes); a clean-venv install of the exact version
followed by `scripts/smoke.py` and the step's own recipe; the Read the Docs
and registry APIs; and the monitor vendors' APIs. A step that introduces a
required environment variable or shared secret verifies at kickoff that it
exists in every target environment and proves shared values by an
authenticated round-trip — never by listing env names. See the parent
ROADMAP "Release & deployment strategy" for the surfaces table, promotion
path, staged-rollout rule, migrations, and rollback.

**Triage rule.** Findings surfaced while executing a step are classified
before they are acted on, per the parent ROADMAP "Defect handling &
triage": spec rot → edit this roadmap's affected `<task>` block now;
upstream gap → patch the earlier step's prompt and add it to the
carry-over checklist (the last list in this file's Not-in-scope section);
implementation bug → fix in-step only if it blocks this step's acceptance
criteria, otherwise an issue and its own branch in a fresh conversation;
model error (a published model returns a wrong number) → a High defect: a
`fix/` branch, the failing case added as a golden test, and an entry on
the errata page; a parity failure between the web and the Python API → a
bug in whichever side changed the bytes, never a loosened comparison; a
provider whose source changed its terms, or a permission granted or
withdrawn → a reclassification under ROADMAP §5 "Data licensing policy"
rule 7, with the hosted snapshots purged when a source stops being
hosted-safe; architectural question → an issue for a future phase;
process improvement → recorded where the next conversation will read it;
security finding → jumps the queue by severity. A step's PR contains the
step plus blocking fixes only, and lists the issues it opened. When a
merged PR auto-closes an issue, the environment check is what earns the
close — reopen or follow up if a gap remains.
`docs/phase05-qa-findings.md` is the rollup: every finding, its class, and
the guard added so the class cannot recur. Issues carry the defect-class
labels Phase 1 created (`spec-rot`, `upstream-gap`, `bug`, `model-error`,
`architecture`, `process`, `security`).

**Status rule.** Every step carries a `**Status:**` line directly under its
`## Step N — …` heading, before the Goal, and this file on `main` is the
ledger of what is done — never a chat transcript, never a later
conversation reconstructing history from `git log`. The line reads `Not
started` when this roadmap is written and is flipped by the step's OWN pull
request: at Stage 3, right after `gh pr create` returns the PR number, the
agent sets it to `Complete — PR #<n> (<YYYY-MM-DD>)`, appends ` ✅` to the
step's heading (`## Step 5 — Generated Model Pages ✅`) so the completion
shows in the rendered preview, the outline, and the table of contents,
sets the step's Summary Table Status cell to `Complete — PR #<n>`, commits
that edit on the step branch, and pushes. The PR therefore carries its own
completion mark, and the roadmap on `main` says a step is complete exactly
when that step's PR merges — never before. This file's phase-level
`**Status:**` line (under the title) and the parent project roadmap are
marked the same way, in the same commit: Step 1's PR flips both from `Not
started` to `In progress` (the parent's `### Phase 5` line reads `In
progress — phase05-roadmap.md`, and its "Phase Complexity Summary" row
reads `In progress`), and the final step's PR flips both to `Complete — …`
(the parent's with its row in the "Phase Complexity Summary" table and the
header `> **Status:**` line) and appends ` ✅` to this file's `# ` title and
to the parent's `### Phase 5` heading, so the project roadmap shows a
finished phase the way this file shows a finished step. There is no
separate "update the roadmaps" chore: a step whose PR merged without its
Status line is a lifecycle violation, and the next step's Stage 1 (and
`/roadmap-step`) refuses to start until the previous step reads
`Complete`. If a post-merge check fails — a Deployed & verified bullet, an
alarm that never fired — the step is NOT complete despite the merged line;
say so, and the `hotfix/` PR that completes it appends its own number to
the line. `grep -n '^\*\*Status:\*\*'` on this file is the phase's progress
report, and the ✅ headings are the same report at a glance.

**Step lifecycle.** Every step in this phase follows the exact same
six-stage lifecycle, in order, with no exceptions. Each stage is a hard
checkpoint — if a stage is skipped, branch protection or the next step's
Stage 1 will fail loudly, and that is the safety net. AI coding agents MUST
execute all six stages before declaring a step complete.

1. **Create the branch.** Before any Read / Edit / Bash, run
   `git checkout -b feature/phase05-step<M>-<slug>` from a clean,
   up-to-date `main`. The exact branch name comes from this step's
   `**Branch:**` line. When the Worktree rule applies, the equivalent is
   `git fetch origin && git worktree add -b <branch> <worktree-path>
   origin/main`, followed by the worktree's bootstrap.

2. **Work on the branch, passing the security gate before every commit.**
   All commits land here, each signed off (`git commit -s`). Never push to
   `main` directly — branch protection (`enforce_admins: true`) rejects it.
   Before each `git commit`, run the local security gate (secret/PII scan,
   SAST, dependency audit, sensitive-data diff review — see the step's
   `<security>` block and the parent ROADMAP "Per-step security gate"). It
   is fail-closed: a finding blocks the commit, so a security issue in this
   step's work is caught here, before the PR and before `main`.

3. **Open the PR, then mark the step.** `gh pr create --base main --head
   <branch>` with a Conventional Commits title and a body that references
   this roadmap step and its acceptance criteria. One PR per step; never
   bundle two steps into one PR. Then, with the PR number in hand, set this
   step's `**Status:**` line (directly under its heading) to `Complete — PR
   #<n> (<YYYY-MM-DD>)`, append ` ✅` to the step's `## Step` heading, set
   its Summary Table Status cell to `Complete — PR #<n>`, commit that edit
   on the step branch (`docs: mark Phase 5 Step M complete`), and push —
   the PR now carries its own completion mark, so the roadmap on `main`
   will say the step is complete exactly when the PR merges (Status rule).
   On the phase's first step, the same commit sets this roadmap's
   phase-level `**Status:**` (under its title) and the parent project
   roadmap's Phase 5 `**Status:**` to `In progress`; on the final step,
   both to `Complete`, with ` ✅` appended to this roadmap's `# ` title and
   to the parent's `### Phase 5` heading.

4. **Wait for green checks, then squash-merge.** Every required status
   check must report success: the 24 Phase 4 left required (the nine
   security checks, lint, types, the aggregate `test` gate — which needs
   the twelve-cell matrix and every job this phase adds to it, such as the
   `web` job from Step 3 — package, lockfile, pr-title, dco, and both
   `phase-verify` jobs for `01`–`04`), plus both `phase-verify` jobs for
   `05` once Step 20 adds them. If the PR goes BEHIND main while waiting,
   refresh with `gh pr update-branch --rebase` — never merge `main` into
   the branch; `required_linear_history: true` enforces rebase. Once every
   check is green:

   ```sh
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```

   If this step's `**Deploys:**` line names a surface, the merge is not the
   finish line: run the Deployed & verified check from the acceptance
   criteria against the target environment now (see the Deploy-and-verify
   rule) before declaring the step complete.

5. **Retire the branch (remote + local).** The `--delete-branch` flag plus
   the repo's `delete_branch_on_merge: true` setting retire the remote
   automatically. Sync local state and prune the merged branch plus any
   other `[gone]` labels left over from prior PRs:

   ```sh
   git switch main
   git pull --ff-only origin main
   git fetch --prune origin
   git branch -vv | grep ': gone]' | awk '{print $1}' \
     | xargs -r git branch -D
   ```

   If this step ran in its own worktree, remove it FIRST —
   `git worktree remove <worktree-path>`, then `git worktree prune` —
   because `git branch -D` refuses a branch still checked out in a
   worktree. Confirm with `git branch -vv` that only `main` and any
   intentional long-lived branches remain locally, and with `git worktree
   list` that only the primary tree remains.

6. **Dispose of every finding, declare completion, then new
   conversation.** Before you declare anything, walk the findings this step
   surfaced and send each to its destination per the Triage rule above — a
   note that a later step needs is edited into that step's `<task>` block
   now; a wrong claim in this step's spec is fixed in this roadmap now; an
   implementation bug is fixed in-step or exists as an issue with a number;
   a judgement call you made in the diff is explained in the PR body; a
   process lesson is written where the next conversation reads it. A
   finding you can only *describe* has not been disposed of, and an
   undisposed finding is an unmet acceptance criterion. Only once the PR is
   merged — and `main` therefore carries this step's `Complete` Status line
   — every acceptance criterion is affirmatively met, and every finding has
   a destination, say so plainly: end your final response with an
   explicit, unhedged completion line — verbatim shape "Step M is complete.
   You can now move on to Step M+1." — so the operator has a clean stopping
   point at which to close this conversation. That line is the LAST line of
   the response. Nothing follows it: no "Follow-ups (non-blocking)", no
   "Notes", no "Next", no "worth a glance", no suggested improvements. If
   you want to show your work, a short ledger may PRECEDE the line, one
   entry per finding naming its destination (an issue number, a file you
   edited, the PR body) — never an open item. If any acceptance criterion
   is NOT met, or any finding has no destination yet, do the opposite —
   state plainly that the step is NOT complete, name what is outstanding,
   and do not emit the completion line. "Done" means done, not "done, but
   here is what you still have to do". Then, for phase-boundary hygiene,
   the operator closes this Claude Code / Cursor / Codex session and opens
   a fresh one before starting Step M+1; the new conversation begins again
   at Stage 1 of this lifecycle, with the next step's `**Branch:**` line
   driving the `git checkout -b` command. No work straddles two steps.

---

## Current State (as of Phase 4)

### Package and surface API

- `pyproject.toml` reads `1.0.0b1`, the version on PyPI since 2026-10-28
  with PEP 740 attestations, and its classifier still says `Development
  Status :: 3 - Alpha`. `src/pyeconomics/` holds `core/`, `models/` (13
  domain packages, 50 models: 33 `instant`, 12 `light`, 5 `heavy`; 18 bound
  to data), `data/` (31 providers, 171 catalog concepts), and the Phase 4
  surfaces: `surfaces/` (the one invocation path `invoke`, the error table
  `problems`, the codec, the envelope, the budgets and the registry export),
  `exports/`, `cli/` (Cyclopts), `server/` (FastAPI behind `[server]`),
  `mcp/` (the SDK's low-level `Server` behind `[mcp]`) and `ai/` (the
  optional narrative). The permanent ledgers hold 50 model ids, 31 provider
  ids and 171 concept ids.
- `pyeconomics registry export` writes `registry.json` (format 1: per
  model the 23 `describe()` keys plus `example_result` and
  `example_figure`) and `openapi.json` (OpenAPI 3.1), both deterministic.
  Model tags are topic words (`bond`, `yield curve`); no syllabus tag
  exists, and every card's curriculum section reads "Not yet mapped;
  syllabus crosswalks arrive in Phase 7" (`core/cards.py`).
- The REST API serves `/v1/models`, `/v1/models/{id}`, `POST` and `GET`
  runs for every model (a bound run takes `?as_of=`, `?vintage=`,
  `?profile=`, `?concept=` and `?param=`, its body overriding what is
  bound), `/v1/series/{target}` (`start`, `end`, `as_of`, `vintage`,
  `provider`), `/v1/sources`, `/healthz`, `/version` (package version, git
  SHA, mode) and `?format=` downloads (`json`, `csv`, `xlsx`, `parquet`,
  `arrow`, `bundle`), plus `/mcp` (stateless Streamable HTTP, POST only)
  and, in local mode only, `/docs` and `/redoc`. Problem `type` URIs read
  `https://pyeconomics.dev/problems/<slug>`, and nothing answers at them
  yet (ADR-0012 decision 4).
- `pyeconomics serve` starts local mode on 127.0.0.1:8000, refuses a
  non-loopback host without `--allow-remote` and answers only requests
  addressed to a loopback name (`cli/serve_command.py`). It serves no web
  page: ADR-0002's `[app]` extra and its `pyeconomics-app` wheel do not
  exist, and `[project.optional-dependencies]` says `[app]` arrives with
  its package.
- `core/plotting.py` draws a Plotly figure from a model's `ChartSpec`s
  (`line`, `scatter`, `bar`, `band`) in 60 lines; `figure_of` works from a
  result's JSON document. Five models declare charts. The `[plot]` extra's
  Plotly 7.1.0 bundles Plotly.js 4.1.1, the version the MCP Apps chart
  pins (`mcp/apps.py`, `PLOTLY_JS_VERSION`).

### Web and Node surface

- `web/` holds only a README naming ADR-0006's stack and ADR-0002's
  `pyeconomics-app` wheel. No Astro project, lockfile or site build exists.
- `tools/node/` is the one Node workspace (Node 22.19 or later): the
  TypeScript client generated from `openapi.json` with
  `@hey-api/openapi-ts` 0.99.0, the MCP Inspector checks (2.12.0) and the
  staging edge Worker (`tools/node/edge/worker.mjs`, its `node:test` suite
  and `wrangler.toml`). TypeScript is pinned at 6.0.3, because 7.0's
  native compiler has no JavaScript API; Dependabot PR #187 (TypeScript 7)
  stays unmerged. `npm audit --prefix tools/node --audit-level=high` is a
  prek hook, and Dependabot's `npm` ecosystem watches `/tools/node` only.

### Hosted service and edge surface

- Staging runs in Google Cloud project `pyeconomics-staging`
  (`us-central1`): Cloud Run service `pyeconomics-api-staging` (minimum 0,
  maximum 2 instances, 1 GiB, concurrency 8), Artifact Registry
  `pyeconomics`, a runtime identity that reads only its two secrets, a
  deploy identity reached through Workload Identity Federation bound to the
  repository id and `refs/heads/main`, Secret Manager (`ratelimit-url`,
  `edge-credential`), and a $1 monthly budget with 50/90/100% alerts to
  Pub/Sub. The image is `python:3.14-slim-bookworm` pinned by digest, with
  the `[server,mcp,econometrics,plot,sdmx]` extras and pyarrow from
  `uv.lock` hashes, non-root, scanned by Trivy in `ci.yml`.
- The edge is the Cloudflare Worker `pyeconomics-api-staging` on
  `staging-api.pyeconomics.dev`, behind Cloudflare Access (the maintainer's
  identity and the `pyeconomics-staging-ci` service token, which expires
  2027-10-27), forwarding to the origin with the edge credential; the free
  plan's one rate rule (50 requests per 10 seconds per IP) covers that
  host. Google Frontend reserves `/healthz` on `*.run.app`, so the Worker
  answers edge `/healthz` from the origin's `/version`.
- `deploy-staging.yml` builds, scans, pushes and deploys on every merge to
  `main` and verifies through the edge; `staging-health.yml` probes hourly
  and opens a `staging-health` issue on failure. Two findings must close
  before production repeats the setup: #210 (a rollback pins traffic, so
  the next deploy gets 0%) and #211 (the deploy identity holds project-level
  `roles/run.admin`).
- Hosted mode fetches hosted-safe originators per request (ADR-0012
  decision 11), with an in-process GET run cache and no shared cache.
  Phase 5 replaces the per-request fetch with its snapshot reader.

### Data plane surface

- Every provider and series carries its licence class, terms page,
  attribution, notices, `llm_use` and storage terms. Hosted mode refuses
  every source not `hosted-safe` or `user-supplied`, in the resolver and in
  the provider. `cache.policy.may_store` is the one storage gate; the cache
  writes canonical-JSON frame payloads into one SQLite file and validates
  them back into frames, never a pickle.
- No snapshot code, bucket, job or schedule exists. The hosted-safe
  originators that need a key (BEA always; BLS and Census for higher
  limits) hold keys only in the `providers-live` environment and on the
  maintainer's keyring; the hosted service holds none.

### Documentation surface

- Read the Docs builds `main` as the non-default 1.0 preview (`/en/main/`)
  with warnings as errors; the project's default branch is
  `legacy/0.2.x` and its default version `stable`, which serves 0.2.6 with
  `latest`. `docs/conf.py` uses MyST-NB, sphinx-autoapi, Napoleon and the
  local `model_pages`, `provider_pages`, `concept_pages` and
  `problem_pages` extensions under `pydata_sphinx_theme`, titled
  "pyeconomics 1.0 preview" with an alpha-preview announcement; an audit
  hook blocks non-loopback sockets during the build; Sybil runs the
  Markdown examples. sphinx-gallery is not installed.
- Pages exist for installation, the quick-start, one tutorial
  (`tutorials/first-model.md`), the CLI, REST API, MCP, exports, AI
  narrative, results, conventions, registry, problems, notices, errata,
  the data layer and the generated model, provider and concept reference.
  No how-to guide, migration guide, study path, gallery or in-browser
  example exists. Roadmaps, ADRs, release records and
  `docs/operations/` are excluded from the site.

### Legal, brand and community surface

- The README carries the CFA® notice verbatim, the 0.2.x pointer, the
  disambiguation note and the `mcp-name:` marker; `NOTICE` holds the
  dependency attributions; `SECURITY.md` routes reports through GitHub's
  private vulnerability reporting and promises 0.2.x security fixes until
  1.0.0. The brand assets live in `docs/_static/brand/` (the bell-curve
  mark, banner, avatar and social card; charcoal #1E1E1E, blue #63C1FF,
  off-white #E7E7E7).
- The four domains are on Cloudflare Registrar with Cloudflare DNS
  (ADR-0009); only `staging-api.pyeconomics.dev` serves anything. No terms,
  privacy policy, disclaimers page, data-sources page, `security.txt`,
  status page, analytics, newsletter or waitlist exists. GitHub Discussions
  is enabled with no categories configured for the launch, and the
  repository's homepage field is empty. The trademark clearance search
  ADR-0009 asks for is not done, and no permission request has been sent.

### Release and CI surface

- `ci.yml` runs lint, types, ty (informational), twelve test cells,
  package, pyodide, docs, api-fuzz, clients, mcp-inspector, parity,
  container, lockfile, pr-title, dco and the aggregate `test`;
  `security.yml`, `codeql.yml`, `scorecard.yml` and `phase-verify.yml`
  (matrix `01`–`04`) run beside it, all on GitHub-hosted runners, as a
  public repository's must. `main` requires 24 strict checks: the nine
  security checks, lint, types, test, package, lockfile, pr-title, dco and
  both `phase-verify` jobs for `01`–`04`.
- `release.yml` builds one distribution with `uv build`, checks it
  against `scripts/checks/dist_contents.py` (the wheel admits only `.py`
  files) and publishes through Trusted Publishing with attestations:
  `.devN` tags to TestPyPI, other tags to PyPI behind the `pypi`
  approval, then `release-smoke.yml`. `mcp-registry.yml` publishes
  `server.json` (schema 2025-12-11, one stdio package entry, no remote)
  through OIDC from the protected `mcp-registry` environment.
- Nine Dependabot PRs are open (#101–#103, #185, #187, #188, #202, #203,
  #215) and proceed under normal checks; #187 stays unmerged.

### Security and sensitive-data surface

- Phase 5 adds three data classes ROADMAP §5 "Data classification" names
  for it: waitlist and newsletter emails (PII: one processor,
  least-privilege access, deletion on request, never in logs or
  analytics), analytics (cookie-less, aggregate, disclosed) and user
  uploads (parsed in the browser, never stored by the hosted service). It
  adds the first public ingress, the first production secrets, the first
  third-party scripts in a browser and the first client bundle that could
  leak a secret.
- The prek gate runs gitleaks, bandit, semgrep with the project rules,
  `pip-audit`, `npm audit` for `tools/node`, `lock-index`, `licences`,
  zizmor and `no-commit-to-branch`; actionlint is not in it (#212). No
  ESLint, no `eslint-plugin-security` and no browser security header
  exists yet. Patterns every step mirrors: secrets only in Secret Manager
  and protected GitHub environments, set by commands that prompt or pipe;
  shared secrets proven by an authenticated round-trip; `--no-config` on
  every `uv add`, `lock` and `export`; a workflow change treated as a
  security-relevant diff.

### Operations and observability surface

- The runtime surfaces are staging (health signal `/healthz` and
  `/version` through the edge; probe `staging-health.yml`; alarm an issue
  and GitHub's notification, proven by synthetic run 40699025411 and issue
  #209), the staging budget (notification proven on 2026-10-28), package
  publishing (`release-smoke.yml`) and the weekly `providers-live.yml`
  with the daily `providers-heartbeat.yml`. `docs/operations/staging.md`
  holds the staging runbooks.
- No production service, snapshot job, error tracker, telemetry, uptime
  check or status page exists. ROADMAP §5's health-signal table promises
  them for Phase 5, each with an alarm seen to fire once.

### Verification surfaces

- `scripts/verify-phase01.sh` to `verify-phase04.sh` exist;
  `verify-phase04.sh` (64 static checks, V1–V16, eight modes: `--fast`,
  `--python`, `--node`, `--container`, `--security`, `--live`, `--all`,
  `--post`) is the template for `verify-phase05.sh`, with its live helper
  `scripts/verify_phase04_live.py` and its pytest twin
  `tests/repo/test_phase04.py`. Its canonical `--post` passed 121/0 on
  2026-10-29 in 15,414 seconds, nested Phase 3, 2 and 1 runs included.
- `.github/workflows/phase-verify.yml` runs the matrix `phase: ["01",
  "02", "03", "04"]`, both jobs required; Phase 5 appends `"05"`. Known
  verifier traps: the scripts need bash 4 or later and fail open under
  macOS's bash 3.2 (#217); Phase 1 check 16 misreads `gh`'s CRLF on
  Windows (#213); gcloud's Git Bash wrapper breaks under
  `MSYS_NO_PATHCONV=1`; Cloudflare's rate rule counts with a lag; a new
  advisory can turn a nested phase's gate red mid-run.
- Several earlier checks pin facts the launch changes on purpose: Read
  the Docs `stable` serving 0.2.6 and `main` titled "1.0 preview" (Phase 1
  V4.4, Phase 2 V7.3, Phase 3 V11.3, Phase 4 V15.2), a plain `pip install
  pyeconomics` resolving 0.2.6 (Phase 2 V14.3, Phase 3 V19.3, Phase 4
  V15.3), and the README naming `1.0.0b1` (Phase 4 check 58, a static
  check every pull request runs). The Cross-phase verification rule below
  assigns each one to the step that changes it.

---

## Execution Order

```
Step 1  (launch baseline)             roadmap + kit landed; 1.0.0rc1.dev1;
                                      #210 #211 #212 #213 #217 closed
                                      → implement
  ↓
Step 2  (ADR-0013)                    web, hosting, data plane, telemetry,
                                      launch and growth decisions;
                                      parent amended → implement
  ↓
Step 3  (web foundation)              web/: Astro, React, Tailwind, shadcn,
                                      KaTeX, CSP, tests; ci web job
                                      → implement
  ↓
Step 4  (staging site)                staging.pyeconomics.dev: Worker +
                                      static assets + Access; site job
                                      in deploy-staging → implement
  ↓
Step 5  (model pages)                 /models/<domain>/<name>/ for all 50;
                                      problems, sitemap, OG, JSON-LD
                                      → implement
  ↓
Step 6  (calculators + web parity)    RJSF island, chart port, downloads,
                                      snippets; parity through the API
                                      → implement
  ↓
Step 7  (navigation + search)         15 sections, Pagefind, syllabus
                                      seed, related models, coverage
                                      → implement
  ↓
Step 8  (snapshot data plane)         snapshot job, bucket, reader;
                                      hosted series from snapshots
                                      (staging) → implement
  ↓
Step 9  (data explorer + user data)   explorer, series transforms,
                                      in-browser CSV/XLSX for runs
                                      → implement
  ↓
Step 10 (local app)                   pyeconomics-app wheel, [app],
                                      serve hosts the site; release
                                      builds both → implement
  ↓
Step 11 (docs: guides)                tutorials, how-tos, migration
                                      guide, study paths → implement
  ↓
Step 12 (docs: learning)              gallery, in-browser examples,
                                      Python-for-finance tutorials
                                      → implement
  ↓
Step 13 (production platform)         prod project, API, job, site on
                                      pyeconomics.dev behind Access;
                                      tag deploys → implement
  ↓
Step 14 (observability)               Sentry, OpenTelemetry, uptime,
                                      status page, synthetic checks,
                                      alarms fired, runbooks → implement
  ↓
Step 15 (growth signals)              Discussions, newsletter + waitlist,
                                      Pro preview, analytics, G3 ledger
                                      → implement
  ↓
Step 16 (legal, trust + brand)        terms, privacy, disclaimers,
                                      sources, security.txt; letters;
                                      counsel packet → implement
  ↓
Step 17 (release candidate)           API freeze; v1.0.0rc1 on PyPI;
                                      production soak starts (7 days)
                                      → operate
  ↓
Step 18 (launch readiness gate)       docs/releases/1.0.0-readiness.md;
                                      GO / NO-GO → implement
  ↓
Step 19 (cutover + 1.0.0)             v1.0.0 on PyPI; public site; RTD
                                      stable; MCP remote; announce
                                      → operate
  ↓
Step 20 (QA + verify-phase05.sh)      scripts/verify-phase05.sh
                                      + docs/phase05-qa-findings.md
                                      + phase-verify.yml matrix entry
                                      → create

--- post-implementation ---

V1   Roadmap and kit landed; main at 1.0.0rc1.dev1; the five carried
     issues closed with their guards.
V2   ADR-0013 Accepted and indexed; the parent roadmap amended where it
     changes it.
V3   The site builds statically with no server route; its CSP needs no
     unsafe-eval; tests, audits and the bundle licence check pass.
V4   Merges deploy the staging site behind Access with its headers; API
     paths reach the staging origin through the same host.
V5   Every model has a page in the sitemap; every problem type resolves;
     JSON-LD and Open Graph images exist; the page ledger holds.
V6   Every golden case returns the Python API's bytes through the
     calculator's request path; charts equal example_figure.
V7   Fifteen sections, search, syllabus filters and the coverage matrix
     render from the registry and syllabi/.
V8   Staging's hosted series come from snapshots; the job runs on its
     schedule; a series outside the set is refused.
V9   The explorer charts and downloads hosted-safe series with source and
     as-of; user files never leave the browser except as run values.
V10  pyeconomics[app] serves the same site locally; both distributions
     build, check and smoke together.
V11  The guides, how-tos, migration guide and study paths build with
     warnings as errors, and their examples run.
V12  The gallery executes, the in-browser examples load the core in
     Pyodide, and the finance tutorials run.
V13  A release tag deploys the API, job and site to production by
     digest; production answers behind Access.
V14  Each alarm fired once; monitors, status page, synthetic checks,
     error tracking and telemetry record production.
V15  Discussions, newsletter, waitlist, Pro preview, analytics events and
     the weekly ledger all record.
V16  The legal pages are live and match the data flows; letters sent;
     security.txt valid; counsel packet delivered.
V17  The public API inventory is pinned; 1.0.0rc1 on PyPI for both
     distributions; production soaked 7 days.
V18  Readiness evidenced with the maintainer's GO.
V19  1.0.0 on PyPI; pyeconomics.dev public and indexable; RTD stable is
     1.0; the MCP Registry lists the remote; post-launch checks pass.
V20  verify-phase05.sh --fast and --security exit 0 in phase-verify.yml;
     Phases 1–4 stay green.
```

Steps are sequential by dependency, and this phase draws no steps in
parallel: nearly every step edits `web/`, `pyproject.toml`, `uv.lock`,
`ci.yml` or the shared deploy workflows, so concurrent branches would
conflict, and the Worktree rule's parallel case does not apply. Step 1
closes the findings production must not inherit before anything reuses
staging's setup. Step 2's ADR fixes every decision the site, the data
plane, production and the launch encode, so no code bakes in a choice the
maintainer has not accepted. Step 3 builds the toolchain and the security
headers every page inherits, and Step 4 puts it behind a real Cloudflare
edge at once, so every later web step verifies on staging rather than on a
laptop. Step 5's pages are where Step 6's calculators and Step 7's
navigation live. Step 8 lands the hosted data plane before Step 9's
explorer reads it, because the explorer lists only what hosted mode can
serve; data before the site, as ROADMAP §5's staged-rollout rule asks.
Step 10 packages the finished site for local use and teaches the release
workflow to publish two distributions, which Step 17's candidate needs.
Steps 11 and 12 document surfaces that exist by then. Step 13 deploys data,
then API, then site to production; Step 14 makes production observable and
proves its alarms; Step 15 adds the growth signals; and Step 16 writes the
privacy policy last among them, so it describes data flows that exist.
Step 17 freezes the public API and starts a seven-day production soak of
the release candidate, which is wall-clock time; Step 18 runs only after
the soak ends; Step 19 releases and opens the site only after the
maintainer's GO; Step 20 follows Step 19.

---

## Step 1 — Launch Baseline and Carried Fixes ✅

**Status:** Complete — PR #219 (2026-10-29)

> **Goal:** Set the baseline the launch builds towards and close the
> findings production must not inherit. Land this roadmap and the refreshed
> planning kit as the branch's first two commits; move `main` to
> `1.0.0rc1.dev1` with `CITATION.cff` in step and an `[Unreleased]` section
> in `CHANGELOG.md`; close #217, so every `scripts/verify-phaseNN.sh` fails
> closed under a bash older than 4 (exit 2 with a message) and keeps a
> crash's exit status through its `EXIT` trap, with the requirement named in
> `CONTRIBUTING.md`; close #213, so Phase 1 check 16 reads `gh`'s output
> without its carriage returns on Windows; close #212, so actionlint, pinned
> and checksum-verified, runs in the prek gate and the CI gate jobs over
> every workflow, with whatever it reports today fixed; close #210, so
> `deploy-staging.yml` returns traffic to the latest revision before it
> verifies and `docs/operations/staging.md` says how to return to latest
> after a manual rollback; and close #211, so the staging deploy identity
> holds its Cloud Run role on the service alone, never on the project. No
> web code and no new runtime dependency arrive yet, and no model's outputs
> change. Parent: issues #210–#213 and #217; `docs/phase04-qa-findings.md`
> "Pre-ship items and owners"; ROADMAP §5 "Per-step security gate" rule 5.

**Branch:** `feature/phase05-step1-launch-baseline`

**Deploys:** the staging API on Cloud Run — this merge redeploys staging
through `deploy-staging.yml`, as every merge does, now with #210's fix and
#211's narrowed identity; the Deployed & verified check reads the run, the
service's traffic and its IAM policy. The version moves to
`1.0.0rc1.dev1`, but this step pushes no tag and publishes nothing.

|               |          | Cost                 | Balanced             | Quality            |
| ------------- | -------- | -------------------- | -------------------- | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**      | **GPT-6.1 Sol**      | **Gemini 4 Argon** |
|               | Platform | Codex                | Codex                | Antigravity        |
|               | Level    | Low                  | High                 | High               |
|               | AA       | 42.1                 | 50.2                 | 52.6               |
|               | Price    | $1.36/1M             | $2.18/1M             | $4.00/1M*          |
| **Runner‑up** | Model    | **Gemini 3.8 Flash** | **Sonnet 5.5**       | **Opus 5.5**       |
|               | Platform | Antigravity          | Claude Code          | Claude Code        |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 39.8                 | 46.8                 | 53.6               |
|               | Price    | $2.19/1M             | $3.03/1M             | $6.02/1M           |
| **Backup**    | Model    | **Sonnet 5.5**       | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    |
|               | Platform | Claude Code          | Antigravity          | Codex              |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 40.8                 | 40.9                 | 50.2               |
|               | Price    | $2.69/1M             | $4.29/1M             | $2.18/1M           |

Ranked for coding, medium complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

> Ran 2026-10-29: Quality Runner-up — Opus 5.5 · High. The operator opened
> the step on Claude Code (Claude pool headroom); the Runs rule selected the
> Balanced Pick, GPT-6.1 Sol on Codex.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: five small
fixes whose shape each issue already describes — a guard and a trap in
four Bash verifiers, a line-ending fix, a pinned linter in the gate, one
workflow command and one IAM move the maintainer runs — plus the version
move. Complexity is Medium, because the IAM change and the workflow change
touch the deploy path and must be proven by a real deploy, and the step is
not novel. The ladder's Balanced column runs: GPT-6.1 Sol on Codex at
Intelligence High (ChatGPT Pro, the lane with slack; AA Intelligence Index
50.2), with Sonnet 5.5 on Claude Code at Effort High as its Runner-up and
Gemini 3.8 Flash on Antigravity as its Backup. Cost runs GPT-6.1 Sol at
Intelligence Low (42.1) and Quality Gemini 4 Argon on Antigravity at Effort
High (52.6); Sonnet 5.5 and Opus 5.5 always think, so they have no Thinking
toggle. New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step1-launch-baseline`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 1 is
       complete. You can now move
       on to Step 2." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 2.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - actionlint arrives pinned by version and checksum (or
      as the upstream pre-commit hook pinned by commit SHA),
      MIT-licensed; its findings are fixed, never silenced
      without an inline justification.
    - The IAM change narrows privilege only: after it, the
      deploy identity holds no project-level Cloud Run role,
      and a dispatched deploy proves it still deploys; the
      maintainer runs the gcloud commands the step prints,
      and the PR records what changed, never a credential.
    - A verifier that fails open is a security gap: the bash
      guard and the trap fix make every verify script exit
      non-zero when it cannot run its checks.
  </security>

  <context>
    pyeconomics. Phase 5. Step 1: launch baseline and carried
    fixes.

    Current state (as of Phase 4; no Phase 5 step has run):

    - main is at 206c2fa (PR #216) or later; ordinary
      Dependabot maintenance merges independently.
      pyproject.toml and CITATION.cff read 1.0.0b1;
      CHANGELOG.md has an empty [Unreleased] section above
      [1.0.0b1] - 2026-10-28.
    - This roadmap (docs/roadmap/phase05-roadmap.md) is
      untracked, and planning/ holds roadmodel 0.2.104's kit
      (planning/HOW-TO-USE.md and planning/model-selector.txt
      modified by /roadmap-phase 5 on 2026-10-29). Both carry
      over to the step branch.
    - #217: under macOS's /bin/bash 3.2, `declare -A` fails,
      the first `record` dies under `set -u`, and the EXIT
      trap's `rm -rf` status (0) becomes the script's, so
      every verify script stops at its first check and exits
      0. CI runs bash 5 and is unaffected.
    - #213: verify-phase01.sh check 16 compares `gh` output
      that carries CRLF on Windows.
    - #212: a job-level `env:` using the `runner` context
      broke ci.yml at load time in Phase 4 Step 8; zizmor
      audits security, not validity.
    - #210: deploy-staging.yml's rollback runs
      `gcloud run services update-traffic
      --to-revisions=<previous>=100`, which removes
      `latestRevision: true`, so the next deploy's revision
      gets 0% of traffic until someone restores it.
    - #211: the deploy identity
      `pyeconomics-staging-deploy@pyeconomics-staging.iam`
      holds roles/run.admin on the project, because Cloud
      Run refused a service-level binding before the service
      existed. The service exists now.
    - gcloud's Git Bash wrapper breaks under
      MSYS_NO_PATHCONV=1: call it with `env -u
      MSYS_NO_PATHCONV`. The Budget API needs
      `--billing-project=pyeconomics-staging`.

    Files to read (every file before drafting):
    - This roadmap's Overview (Version rule, Cross-phase
      verification rule) and Current State.
    - Issues #210, #211, #212, #213 and #217
      (`gh issue view <n> --comments`).
    - scripts/verify-phase01.sh to verify-phase04.sh (the
      head of each, check 16 of Phase 1, the trap lines).
    - .pre-commit-config.yaml and .github/workflows/
      security.yml (the gate jobs).
    - .github/workflows/deploy-staging.yml and
      docs/operations/staging.md.
    - CONTRIBUTING.md (its verification notes), CHANGELOG.md,
      CITATION.cff and tests/unit/test_version.py.
  </context>

  <goal>
    The roadmap and kit are on main; main reads
    1.0.0rc1.dev1; every verify script refuses to run under
    an old bash and never turns a crash into a pass; check 16
    passes on Windows; actionlint gates every workflow;
    staging's next deploy after a rollback takes traffic by
    itself, and its deploy identity holds no project-level
    role; the five issues close with their guards.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Land the roadmap first. After Stage 1, commit planning/
      as /roadmap-step §5 instructs (`chore(planning): refresh
      the roadmodel kit to 0.2.104`), then this file
      (`docs(roadmap): add the Phase 5 roadmap`), each signed
      off and gated, before any other change.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer (Auto
      mode blocks IAM writes one at a time): the gcloud
      commands for #211 — bind the deploy identity on the
      service `pyeconomics-api-staging` (roles/run.developer
      when deploy-staging.yml no longer sets the service's
      IAM policy on each deploy, else roles/run.admin on the
      service), then remove its project-level roles/run.admin
      binding — each with its effect; the dispatch of
      deploy-staging.yml that proves the deploy still works;
      and approval to merge when the checks are green. Record
      the answers in the PR body.
    </requirement>

    <requirement>
      #217 in all four verify scripts: near the top,
      `[ "${BASH_VERSINFO[0]:-0}" -ge 4 ] || { echo "verify
      needs bash >= 4 (brew install bash)" >&2; exit 2; }`;
      the trap becomes `trap 'rc=$?; rm -rf "$TMP"; exit
      $rc' EXIT`. Add tests/repo/test_verify_portability.py
      (a basename unique repo-wide): each script under a
      stand-in bash that reports version 3 exits 2 with the
      message, and a script killed mid-run by a failing
      command exits non-zero. Name the bash requirement in
      CONTRIBUTING.md's verification notes.
    </requirement>

    <requirement>
      #213: check 16 strips carriage returns from `gh`
      output before comparing (`tr -d '\r'`), with a twin
      test fed CRLF text.
    </requirement>

    <requirement>
      #212: actionlint in .pre-commit-config.yaml (the
      upstream hook pinned by commit SHA, or a pinned binary
      verified by checksum), run by prek locally and by the
      CI gate job that runs the hooks; fix every finding it
      reports today, and keep zizmor. A workflow added by a
      later step passes actionlint before it merges.
    </requirement>

    <requirement>
      #210: deploy-staging.yml runs `gcloud run services
      update-traffic --to-latest` after `gcloud run deploy`
      and before verifying, so a pinned split from a
      rollback never strands the new revision; the deploy
      verification still compares /version's git_sha with
      the commit. docs/operations/staging.md's rollback
      section says how to return to latest after a manual
      rollback.
    </requirement>

    <requirement>
      #211: after the maintainer's commands, record in
      docs/operations/staging.md the identity's roles exactly
      (service-level only) and the date; a dispatched
      deploy-staging.yml run on the branch's merge proves the
      deploy. Phase 5 Step 13 repeats the service-level
      pattern for production from the start.
    </requirement>

    <requirement>
      Version (Version rule): `uv version 1.0.0rc1.dev1
      --no-config`, with CITATION.cff and server.json's three
      versions to match (tests/mcp/test_mcp_registry_entry.py
      holds server.json to pyproject.toml);
      tests/unit/test_version.py passes, and so do
      verify-phase01.sh check 44 and verify-phase02.sh check
      7. CHANGELOG.md's [Unreleased] gains "Fixed" entries
      for #210, #211, #213 and #217, a "Security" entry for
      #212 and a "Changed" entry for the version. The PR body
      says `Closes #210, closes #211, closes #212, closes
      #213, closes #217`.
    </requirement>

    <requirement>
      Cross-phase verification rule: run each of
      verify-phase01.sh to verify-phase04.sh with `--fast`
      before the PR; a check this step legitimately breaks is
      narrowed with an addendum line, never deleted.
    </requirement>

    <requirement>
      Stage 3, the phase's first step (Status rule): the same
      commit that marks this step sets this roadmap's
      phase-level Status line and the parent's `### Phase 5`
      Status line to `In progress` (the parent's as `In
      progress — phase05-roadmap.md`), and the parent's
      "Phase Complexity Summary" row for Phase 5 to
      `In progress`.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); YAML starts with `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 1 acceptance criteria

- This roadmap and the refreshed planning kit reached `main` as the step
  branch's first two commits.
- Every `scripts/verify-phaseNN.sh` exits 2 with its message under a bash
  older than 4 and exits non-zero when a check crashes;
  `tests/repo/test_verify_portability.py` proves both; `CONTRIBUTING.md`
  names the requirement. Issue #217 is closed.
- Phase 1 check 16 passes on Windows with `gh`'s CRLF output, with its twin
  test; issue #213 is closed.
- actionlint runs in the prek gate and in CI, pinned, and reports nothing
  on every workflow; issue #212 is closed.
- `deploy-staging.yml` restores latest traffic before verifying, and the
  runbook says how to return to latest after a manual rollback; issue #210
  is closed.
- The staging deploy identity holds its Cloud Run role on the service only;
  the runbook records it; issue #211 is closed.
- `pyproject.toml` and `CITATION.cff` read `1.0.0rc1.dev1`, `CHANGELOG.md`'s
  `[Unreleased]` lists the changes, the full suite and the coverage floors
  pass on all twelve CI cells, and `verify-phase01.sh` to
  `verify-phase04.sh --fast` pass in `phase-verify.yml`.
- The phase is marked started: this roadmap's phase-level Status line and
  the parent's `### Phase 5` Status line read `In progress`, and the
  parent's "Phase Complexity Summary" row for Phase 5 reads `In progress`.
- **Deployed & verified:** the `deploy-staging.yml` run on this step's
  merge commit succeeded, staging `/version` through the edge (service
  token from the maintainer's keyring) reports that SHA, `gcloud run
  services describe pyeconomics-api-staging` shows the latest revision
  serving 100% with `latestRevision: true`, and `gcloud projects
  get-iam-policy pyeconomics-staging` lists no `roles/run.admin` for the
  deploy identity.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, actionlint and zizmor clean on every
  workflow — the deploy identity's privileges only narrowed, and no
  credential appears in the PR or a log.

---

## Step 2 — ADR-0013: Web App, Hosting, Data Plane and Launch

**Status:** Not started

> **Goal:** Fix every decision the site, the data plane, production and
> the launch encode before any of them is built. Write
> `docs/adr/0013-web-app-and-launch.md` from the twenty decisions this
> roadmap's Overview drafts — the canonical domain, the site's layout and
> URLs, one host and one Worker, the environments, production on Google
> Cloud, the snapshot data plane, caching, calculators, the security
> headers, search and navigation, the data explorer, the syllabus seed,
> analytics, the email processor, error tracking, telemetry and uptime, the
> local app, the public-API freeze, the release and soak, the launch
> measures and growth gates, and the legal readiness items — each with its
> options, sources and access dates, for
> the maintainer to accept or amend in the pull request; index it in
> `docs/adr/README.md`; and amend the parent roadmap where the ADR changes
> it: the snapshot store (§4 5.8; §5 "Cost projection", "Data and schema
> migrations" and "Rollback"), the syllabus filters' seed (§4 5.3, with the
> matching line in §4 7.1), the preview environment (§5 "Deployable
> surfaces"), and the soak period, the Lighthouse page sample and the Gate
> G3 window, which ROADMAP §4 5.9 and §5 "Monetization strategy &
> validation gates" leave to this roadmap. No code arrives. Parent: ROADMAP
> §4 5.1–5.10; §5 "Release & deployment strategy", "Security & privacy
> strategy", "Operations & observability strategy", "Data licensing
> policy", "Legal & brand guardrails" and "Monetization strategy &
> validation gates"; ADR-0002, ADR-0003, ADR-0005, ADR-0006, ADR-0007,
> ADR-0009 and ADR-0012.

**Branch:** `feature/phase05-step2-adr-launch`

**Deploys:** nothing beyond merge — an ADR and roadmap text; the Read the
Docs `main` preview rebuilds as on every merge, and ADRs stay outside the
site.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Opus 5.5**       | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | High               | XHigh              |
|               | AA       | 47.8               | 53.6               | 56                 |
|               | Price    | $1.61/1M           | $6.02/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 51                 |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $4.00/1M           |

Ranked for planning, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Planning is PRIMARY and knowledge SECONDARY: twenty
decisions that span a frontend stack, an edge, two clouds, a data plane,
four vendors, privacy law and a public launch, several of which become
public API or public promises at 1.0.0. Complexity is High — the decisions
interact (the CSP constrains the chart, form, search and analytics choices;
the snapshot store constrains the data layer's network rule) — but the
step is not novel: every decision has a drafted default and facts checked
on 2026-10-29 in this roadmap. The ladder's Balanced column runs: Opus 5.5
on Claude Code at Effort High (claude.ai Max; AA Intelligence Index 53.6),
with GPT-6.1 Sol on Codex at Intelligence High as Runner-up and Gemini 4
Argon on Antigravity as Backup. Quality raises Opus 5.5 to Effort XHigh
(56.0); Cost runs GPT-6.1 Sol at Intelligence Medium (47.8). Opus 5.5
always thinks, so it has no Thinking toggle. New conversation per
phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step2-adr-launch`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 2 is
       complete. You can now move
       on to Step 3." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 3.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The ADR names no secret value, account id beyond what
      the repository already records, personal email address
      or private hostname; vendor accounts appear by product
      and plan only.
    - Every decision that touches personal data (analytics,
      the email processor, error tracking, telemetry, logs)
      states what is collected, who processes it, where it is
      kept and for how long, so Step 16's privacy policy can
      be checked against it line by line.
  </security>

  <context>
    pyeconomics. Phase 5. Step 2: ADR-0013, the web app,
    hosting, data plane and launch decisions.

    Current state (post-Phase-5 Step 1):

    - main reads 1.0.0rc1.dev1; #210-#213 and #217 are
      closed; actionlint is in the gate.
    - ADR-0006 chose Astro static output with React islands,
      Tailwind and shadcn/ui, the static site on Cloudflare
      (Workers static assets unless a reason to stay on
      Pages), FastAPI on Cloud Run, and no Worker code in the
      page path unless a later ADR adds it. ADR-0007 chose
      Sphinx with MyST-NB, sphinx-autoapi and sphinx-gallery
      on Read the Docs, and marimo's WebAssembly export for
      in-browser examples. ADR-0002 put the built site in a
      `pyeconomics-app` wheel behind `[app]`. ADR-0009 left
      the canonical domain to Phase 5. ADR-0012 decision 11
      left hosted series to Phase 5's snapshot reader, and
      decision 16 left the MCP Registry's remote entry to
      Phase 5's production endpoint.
    - ROADMAP §4 5.9 leaves the soak period and §4 5.1's
      Lighthouse sample to this roadmap; §5's Gate G3 row
      leaves its window to it; §5 says the thresholds are the
      maintainer's judgement, confirmed or adjusted before
      launch.
    - This roadmap's Overview drafts the twenty decisions,
      their defaults, the facts read on 2026-10-29 and the
      cross-phase narrowings.

    Files to read (every file before drafting):
    - This roadmap's Overview and Current State, in full.
    - docs/adr/README.md, template.md, ADR-0002, ADR-0003,
      ADR-0005, ADR-0006, ADR-0007, ADR-0009 and ADR-0012.
    - docs/roadmap/ROADMAP.md: §3, §4 Phase 5 and 7.1, §5
      "Cost projection", "Release & deployment strategy",
      "Security & privacy strategy", "Operations &
      observability strategy", "Data licensing policy",
      "Legal & brand guardrails" and "Monetization strategy
      & validation gates".
    - The vendors' current pricing and terms pages for each
      decision, re-read at kickoff (prices move).
  </context>

  <goal>
    ADR-0013 is Accepted with the maintainer's choice on each
    decision; the ADR index lists it; the parent roadmap
    agrees with it; every later step encodes a decision this
    ADR records, never a fresh one.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Write docs/adr/0013-web-app-and-launch.md from
      template.md: context, drivers, considered options and,
      for each of the twenty decisions in this roadmap's
      Overview, the drafted default with its rationale, the
      alternatives and sources with access dates; then
      Consequences and a Confirmation table naming the check
      and the Phase 5 step that builds it. Status `Proposed`
      until the maintainer accepts it in the PR; then
      `Accepted` with the date in the file and the index.
    </requirement>

    <requirement>
      Re-read at kickoff every fact a decision rests on that
      can move (prices, free-tier limits, package versions,
      the Astro CSP feature's status, the vendors' terms), and
      update this roadmap's facts where they changed (spec
      rot). A decision whose default a changed fact breaks is
      put to the maintainer with a new recommendation.
    </requirement>

    <requirement>
      ONE batched question to the maintainer, with each
      recommendation first: accept or amend each decision;
      confirm the Gate G3 thresholds and window (decision
      19); choose the email processor and the analytics
      provider among the options decision 13 and 14 list;
      and approve the merge when the checks are green.
      Record the answers in the PR and the ADR.
    </requirement>

    <requirement>
      Amend the parent roadmap where the ADR changes it, each
      edit naming ADR-0013: §4 5.8 and §5 "Cost projection",
      "Data and schema migrations" and "Rollback" for the
      snapshot store (decision 6); §4 5.3 and 7.1 for the
      syllabus seed (decision 12); §5 "Deployable surfaces"'
      hosted web app row for the staging site as the preview
      (decision 4); §4 5.9 for the soak and the Lighthouse
      sample (decisions 18 and 19); §5's Gate G3 row for its
      window (decision 19); the cost table for the email
      processor, the analytics provider and the production
      budget. Add the matching line to each phase roadmap the
      change reaches only if one exists.
    </requirement>

    <requirement>
      Update AGENTS.md's "Repository layout" for `web/` (the
      site, its own Node project and lockfile), `syllabi/`
      and `packages/pyeconomics-app/` as decisions 2, 12 and
      16 place them, and add a "Web rules" section the later
      steps fill: no hand-written model page, one CSP, no
      third-party script but the decided analytics, no key or
      secret in the bundle, user files parsed in the browser.
    </requirement>

    <requirement>
      Filepath comment: Markdown follows the sibling ADRs'
      conventions (no path line).
    </requirement>
  </requirements>
</task>
```

### Step 2 acceptance criteria

- `docs/adr/0013-web-app-and-launch.md` exists with all twenty decisions,
  each with options, sources and access dates, and reads `Status:
  Accepted` with the maintainer's acceptance date; `docs/adr/README.md`
  indexes it.
- The maintainer's answers — each decision accepted or amended, the G3
  window and thresholds, the email processor and the analytics provider —
  are recorded in the PR and the ADR.
- The parent roadmap's §4 5.3, 5.8, 5.9 and 7.1 and §5 "Cost projection",
  "Deployable surfaces", "Data and schema migrations", "Rollback" and the
  Gate G3 row agree with the ADR, each edit naming it.
- `AGENTS.md` lists `web/`, `syllabi/` and `packages/pyeconomics-app/` in
  its layout and carries the "Web rules" section.
- `verify-phase01.sh --fast` (checks 17 and 18: the ADR index) and the
  other phases' `--fast` modes pass in `phase-verify.yml`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — and the ADR holds no secret, private
  hostname or personal address, and states the personal data each
  decision collects.

---

## Step 3 — Web Foundation

**Status:** Not started

> **Goal:** Build the site's toolchain and the security every page
> inherits. Create the Astro project in `web/` (ADR-0006, ADR-0013
> decisions 2 and 9): static output with no adapter, React 19 islands,
> TypeScript 6.0 in strict mode, Tailwind 4 and shadcn/ui, KaTeX rendering
> MathML at build time, Node 24 pinned in `.nvmrc`, and a committed
> `web/package-lock.json`; the base layout with the brand assets, a header,
> and a footer carrying the CFA® notice, "as is; not investment advice" and
> links to the disclaimers and data notices; a home page and a 404 page;
> `/version.json` with the package version and the build's git SHA;
> `scripts/web/export_site_data.py`, which writes the registry, the OpenAPI
> document, the error table and the source and concept summaries the site
> reads into a git-ignored directory, and the TypeScript client generated
> from that OpenAPI document; Astro's `security.csp` with no inlined
> processed script or stylesheet, and a post-build step that copies its
> build-wide hashes into `dist/_headers` with decision 9's other headers
> and fails the build on `'unsafe-inline'`, `'unsafe-eval'` or a server
> route; ESLint with `eslint-plugin-security` and accessibility rules,
> Vitest, Playwright with axe at WCAG 2.2 AA and a CSP-violation listener,
> and Lighthouse CI on decision 19's page sample, all served by `wrangler
> dev` so headers behave as on Cloudflare; `npm audit` and a licence check
> of the shipped bundle in the gate; Dependabot for `/web`; and a `web` job
> in `ci.yml` that the aggregate `test` requires. Parent: ROADMAP §4 5.1;
> §5 "Per-step security gate"; ADR-0006; ADR-0013 decisions 2, 9 and 19.

**Branch:** `feature/phase05-step3-web-foundation`

**Deploys:** nothing beyond merge — the site builds and is tested in CI on
every pull request; Step 4 deploys it to staging.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | High               | High               | XHigh              |
|               | AA       | 50.2               | 52.6               | 56                 |
|               | Price    | $2.18/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | XHigh              | High               | High               |
|               | AA       | 51.9               | 53.6               | 52.6               |
|               | Price    | $3.56/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | XHigh              | XHigh              |
|               | AA       | not measured       | 51                 | 52.4               |
|               | Price    | $2.40/1M*          | $4.00/1M           | $16.36/1M          |

Ranked for coding, high complexity. Price: list $ per 1M tokens (3 in : 1 out) ×
the tokens the model uses at that level; * token use not yet measured, a typical
model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and planning SECONDARY: a new
toolchain in a second language whose configuration fixes how every later
page is built, tested and secured — above all a Content Security Policy
with no unsafe sources across Astro's island runtime, React, the form
library, the chart library, search and formulas, each of which has a known
trap. Complexity is High; the step is not novel, because each trap has a
documented way through (Astro's build-wide hashes, precompiled validators,
Plotly's stylesheet opt-out, MathML output). The ladder's Balanced column
runs: Gemini 4 Argon on Antigravity at Effort High with Thinking on
(Google AI Ultra; AA Intelligence Index 52.6), Runner-up Opus 5.5 on
Claude Code at Effort High, Backup GPT-6.1 Sol on Codex at Intelligence
XHigh. Cost runs GPT-6.1 Sol at Intelligence High (50.2) and Quality Opus
5.5 at Effort XHigh (56.0). New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step3-web-foundation`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 3 is
       complete. You can now move
       on to Step 4." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 4.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The CSP is decision 9's: no 'unsafe-inline' and no
      'unsafe-eval' in any directive, no third-party script
      origin, frame-ancestors 'none'; the post-build check
      fails the build otherwise, and the Playwright listener
      fails a test on any securitypolicyviolation event.
    - No secret reaches the bundle: the site reads no
      environment variable at build time but the version and
      git SHA, `import.meta.env` holds no PUBLIC_ value that
      names a key, and the web job scans `dist/` with
      gitleaks and the repository's config.
    - Shipped dependencies pass a permissive licence
      allowlist (MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0,
      ISC, 0BSD); build- and test-only tools (axe-core and
      the Observatory CLI under MPL-2.0, Lighthouse) are
      outside it, as the Python dev tools are; `npm audit
      --audit-level=high` runs in the gate for web/.
    - eslint-plugin-security and the accessibility rules
      run with zero warnings allowed; a suppression carries
      an inline justification.
  </security>

  <context>
    pyeconomics. Phase 5. Step 3: the web foundation.

    Current state (post-Phase-5 Step 2):

    - ADR-0013 is Accepted. web/ holds only a README.
      tools/node/ is the Node workspace for the TypeScript
      client, the Inspector checks and the staging edge
      Worker (Node 22.19 or later; TypeScript 6.0.3).
    - pyeconomics registry export writes registry.json and
      openapi.json; surfaces/problems.py holds the error
      table; data/catalog and data/registry describe the
      concepts and providers.
    - Facts read on 2026-10-29 (re-check at kickoff): astro
      7.4.4 needs Node 22.23.4 or later; security.csp is
      stable since Astro 6, emits a meta element per page
      with sha256 hashes collected for the whole build, does
      not work in dev, supports neither ClientRouter nor
      Shiki, and always inlines the island runtime (hashed);
      `vite.build.assetsInlineLimit: 0` and
      `build.inlineStylesheets: 'never'` stop other
      inlining; frame-ancestors works only as a header.
      TypeScript 7 is unsupported by astro check
      (@astrojs/check peers on ^5 or ^6). Node 26 became
      Active LTS on 2026-10-28; Node 24 is Maintenance LTS
      to 2028-04-30. KaTeX's HTML output carries inline
      style attributes; its MathML output does not.
      Workers static assets apply _headers to asset
      responses only.
    - The brand assets are in docs/_static/brand/ (the mark
      is font-free SVG); the blue #63C1FF fails text
      contrast on white and is used for accents only.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 2, 9
      and 19), ADR-0006 and ADR-0002.
    - web/README.md, tools/node/package.json and
      .github/dependabot.yml.
    - .pre-commit-config.yaml (the npm-audit and licences
      hooks), scripts/checks/ (the licence allowlist).
    - .github/workflows/ci.yml (the clients job, the
      aggregate test job) and security.yml.
    - src/pyeconomics/surfaces/registry_export.py,
      problems.py and src/pyeconomics/data/api.py
      (sources, describe).
    - ROADMAP §5 "CFA Institute marks and content" (the
      notice) and "Required notices".
  </context>

  <goal>
    web/ builds a static site whose every page carries the
    brand, the notices and the headers ADR-0013 decided,
    with no unsafe CSP source, tested for accessibility,
    CSP violations and performance in CI, audited and
    licence-checked in the gate; later steps add pages
    without touching the security model.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Scaffold web/ with the official Astro and shadcn/ui
      paths (re-read at kickoff): Astro 7, @astrojs/react,
      React 19, Tailwind 4 through @tailwindcss/vite,
      shadcn/ui components copied into
      web/src/components/ui/, TypeScript 6.0.3 strict with
      @astrojs/check, `output: 'static'` and no adapter,
      no ClientRouter, no Shiki (code blocks are plain
      `<pre>`), `vite.build.assetsInlineLimit: 0`,
      `build.inlineStylesheets: 'never'`, `.nvmrc` 24 and
      `engines.node` `>=22.23.4`. Every version is pinned in
      web/package-lock.json; `npm ci` reproduces it.
    </requirement>

    <requirement>
      Site data: scripts/web/export_site_data.py (run by
      `npm run data` before every build, through `uv run
      --locked`) writes registry.json, openapi.json,
      problems.json, sources.json (per provider: id, name,
      licence class, terms page, attribution, notices,
      whether hosted mode serves it) and concepts.json (per
      concept: id, title, unit, frequency, candidates and
      hosted availability) into web/src/data/generated/
      (git-ignored), deterministically; the TypeScript
      client is generated from that openapi.json with
      @hey-api/openapi-ts into web/src/client/ (git-ignored).
      A build without the export fails with a message.
    </requirement>

    <requirement>
      Layout: header (the mark and wordmark, the main
      navigation Step 7 fills, the search slot), main,
      footer (the CFA® notice verbatim from ROADMAP §5, "As
      is; not investment advice", links to /legal/disclaimers/,
      /sources/ and the licence, the GitHub repository and
      the documentation); a system font stack, no web font;
      skip link, landmarks and visible focus; the brand blue
      never carries text on white. Home and 404 pages;
      /version.json with `pyeconomics` and `git_sha`.
    </requirement>

    <requirement>
      Formulas: a Math component that runs KaTeX at build
      time with `output: 'mathml'`, `throwOnError: true`
      and `trust: false`, so no formula ships script or
      inline style; a test renders every registry formula.
    </requirement>

    <requirement>
      Headers (decision 9): `security.csp` enabled; a
      post-build script reads the policy Astro wrote, which
      is identical on every page, and writes dist/_headers:
      for `/*` the full policy as a header (Astro's script
      and style hashes plus decision 9's directives,
      frame-ancestors included), Strict-Transport-Security,
      X-Content-Type-Options, Referrer-Policy,
      Permissions-Policy and Cross-Origin-Opener-Policy; for
      `/_astro/*` a year's immutable Cache-Control. The
      script fails the build on 'unsafe-inline',
      'unsafe-eval', a missing directive, an inline script
      or style Astro did not hash, or any server-rendered
      route in the build output.
    </requirement>

    <requirement>
      Quality tooling: ESLint (typescript-eslint,
      eslint-plugin-security, eslint-plugin-astro and
      jsx-a11y), Vitest, Playwright with @axe-core/playwright
      run with the wcag2a, wcag2aa, wcag21a, wcag21aa and
      wcag22aa tags and a listener that fails on any CSP
      violation, and Lighthouse CI asserting decision 19's
      scores on the sample pages that exist. Playwright and
      Lighthouse run against `wrangler dev` serving dist/ as
      Workers static assets, so _headers apply as on
      Cloudflare.
    </requirement>

    <requirement>
      Gate and CI: a second npm-audit hook (or the existing
      one extended) audits web/ at high and above;
      scripts/checks/web_licences.py checks the production
      dependency tree (`npm ls --omit=dev --all --json`)
      against the allowlist; Dependabot's npm ecosystem
      watches /web; ci.yml gains a `web` job (Node from
      .nvmrc, `npm ci`, the export, astro check, lint,
      Vitest, build, the headers check, gitleaks over dist/,
      Playwright with axe, Lighthouse CI, npm audit and the
      licence check), and the aggregate `test` job needs it.
      Every new action is pinned by SHA with permissions {}
      and passes actionlint and zizmor.
    </requirement>

    <requirement>
      AGENTS.md "Web rules" (Step 2 created the section):
      run the site through `npm run data && npm run build`;
      no hand-written model page; one CSP, built from Astro's
      hashes, never loosened by a page; no third-party script
      but decision 13's analytics; no secret or key in the
      bundle; KaTeX as MathML; TypeScript stays on 6.0 while
      astro check refuses 7. .gitignore covers web/dist,
      web/.astro, web/node_modules and the generated
      directories.
    </requirement>

    <requirement>
      Filepath comment: every new TypeScript, JavaScript and
      Astro file starts with `// <path>`; CSS with
      `/* <path> */`; YAML and TOML with `# <path>`; a new
      Python file gets the three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 3 acceptance criteria

- `web/` builds a static site with no server route from a committed
  lockfile on Node 24; `npm ci && npm run data && npm run build` reproduces
  it, and the export is deterministic.
- Every page carries the layout's notices; `/version.json` reports the
  version and SHA; formulas render as MathML with no script or inline
  style.
- `dist/_headers` holds decision 9's policy with Astro's hashes and no
  unsafe source; the post-build check fails the build on a regression, and
  Playwright records no CSP violation on any page.
- The `web` job passes every check — astro check, lint with the security
  and accessibility rules, Vitest, the headers check, gitleaks over
  `dist/`, Playwright with axe at WCAG 2.2 AA, Lighthouse CI at the
  decision-19 scores, `npm audit` and the shipped-bundle licence check —
  and the aggregate `test` requires it.
- `npm audit` for `web/` runs in the prek gate, Dependabot watches `/web`,
  and `AGENTS.md` carries the web rules.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean (ESLint security included), dependency audit clean for Python and
  both Node projects — the CSP has no unsafe source, no secret reaches the
  bundle, and every shipped dependency is permissively licensed.

---

## Step 4 — Staging Site on Cloudflare

**Status:** Not started

> **Goal:** Put the site behind a real Cloudflare edge from the start, so
> every later web step is verified where it will run. Extend the edge
> Worker (`tools/node/edge/worker.mjs`) so one Worker serves the site from
> Workers static assets and runs only on the API's paths (ADR-0013
> decision 3: `run_worker_first` on `/v1/*`, `/mcp`, `/healthz`, `/version`
> and `/openapi.json`), forwarding those to the Cloud Run origin with the
> edge credential as staging's API Worker does; deploy it as
> `pyeconomics-web-staging` on `staging.pyeconomics.dev` behind Cloudflare
> Access (the maintainer's identity and the existing CI service token),
> with `workers.dev` and version URLs off; add a `site` job to
> `deploy-staging.yml` that runs after the API job on every merge, builds
> the staging flavour of the site (indexing refused) from the merge commit,
> deploys it with a Cloudflare API token scoped to this Worker, verifies it
> through Access and rolls back to the previous Worker version on failure;
> re-express the free plan's one rate rule by path, so it covers the API's
> paths on every staging host; add the site to `staging-health.yml`'s probe;
> narrow the workflow secret boundary for the new token; and write the
> site's runbook into `docs/operations/staging.md`. Parent: ROADMAP §4 5.8
> (static hosting) and §5 "Deployable surfaces"; ADR-0006; ADR-0012
> decision 20; ADR-0013 decisions 3, 4 and 9.

**Branch:** `feature/phase05-step4-staging-site`

**Deploys:** the staging site on `staging.pyeconomics.dev` behind
Cloudflare Access — this step's merge is the first deploy, and from it on
every merge to `main` redeploys the API and then the site through
`deploy-staging.yml`; the Deployed & verified check runs through Access
with the service token from the maintainer's keyring.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: a
provisioning run across Cloudflare (a Worker with static assets, a custom
domain, an Access application, a scoped API token, the rate rule) and
GitHub (environment secrets, the deploy job), driven by commands the step
prints for the maintainer, plus a Worker change with tests. Complexity is
High and security-sensitive — a new deploy credential, an edge trust
boundary and the first browser-facing headers — though the topology is
ADR-0013's, so it is not novel. The ladder's Balanced column runs: Sonnet
5.5 on Claude Code at Effort XHigh (claude.ai Max; AA Intelligence Index
51.9), Runner-up GPT-6.1 Sol on Codex at Intelligence High, Backup Gemini
4 Argon on Antigravity at Effort Medium. Cost runs GPT-6.1 Sol at
Intelligence Medium (47.8) and Quality Opus 5.5 at Effort XHigh (56.0);
Sonnet 5.5 and Opus 5.5 always think, so they have no Thinking toggle. New
conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step4-staging-site`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 4 is
       complete. You can now move
       on to Step 5." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 5.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The Cloudflare API token is scoped to editing this
      account's Workers and this zone's Worker routes and
      custom domains, nothing else; it lives only in the
      protected `staging` environment, set by `gh secret set
      CLOUDFLARE_API_TOKEN --env staging` from a prompt; the
      maintainer records its expiry date in the runbook.
    - The Worker runs only on the API's paths, adds the edge
      credential from a Worker secret, strips hop-by-hop
      headers, never forwards a cookie or an Access header to
      the origin, and adds `X-Content-Type-Options: nosniff`
      to forwarded responses (`_headers` does not reach
      them); static assets never invoke it.
    - The staging hostname answers nothing without Access:
      an unauthenticated request gets Access's login, and
      the build refuses indexing besides; `workers_dev` and
      `preview_urls` are false.
    - deploy-staging.yml grants `id-token: write` only to its
      API job and keeps permissions {} at the top; Phase 3
      check 78 and Phase 4 check 64 are narrowed to admit
      `CLOUDFLARE_API_TOKEN` for this workflow and nothing
      else, with their addendum lines.
  </security>

  <context>
    pyeconomics. Phase 5. Step 4: the staging site on
    Cloudflare.

    Current state (post-Phase-5 Step 3):

    - web/ builds the static site with dist/_headers;
      Playwright and Lighthouse already run against
      `wrangler dev` with the static assets.
    - The staging API Worker `pyeconomics-api-staging`
      (tools/node/edge/worker.mjs, wrangler.toml) serves
      staging-api.pyeconomics.dev behind Access and forwards
      every path to ORIGIN_URL with EDGE_CREDENTIAL; it
      answers edge /healthz from the origin's /version,
      because Google Frontend reserves /healthz on
      *.run.app. It was deployed by hand with wrangler.
    - deploy-staging.yml (environment `staging`, OIDC to
      Google Cloud) builds, scans, pushes and deploys the
      image on every merge and verifies through the edge;
      since Step 1 it restores latest traffic first. The
      `staging` environment holds CF_ACCESS_CLIENT_ID and
      CF_ACCESS_CLIENT_SECRET (service token
      `pyeconomics-staging-ci`, expiring 2027-10-27).
    - Facts read on 2026-10-29 (re-check at kickoff): static
      asset requests are free and unlimited; a Free-plan
      Worker serves 100,000 requests a day, and paths
      matched by run_worker_first always invoke it (429
      past the limit); a version may hold 20,000 files of
      at most 25 MiB; _headers (100 rules) and _redirects
      apply to asset responses only; the Free plan's one
      rate-limiting rule matches on path (and verified
      bots) only, counts by IP, 10-second period.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 3, 4
      and 9) and ADR-0012 decision 20.
    - tools/node/edge/ (the Worker, its tests,
      wrangler.toml) and docs/operations/staging.md.
    - .github/workflows/deploy-staging.yml and
      staging-health.yml.
    - scripts/verify-phase03.sh (check 78) and
      scripts/verify-phase04.sh (check 64).
    - Cloudflare's Workers static assets, Access and API
      token documentation, read at kickoff.
  </context>

  <goal>
    Every merge deploys the API and then the site to
    staging; staging.pyeconomics.dev serves the site with
    its headers and the API on the same origin to Access
    only; a failed site deploy rolls back by itself; the
    hourly probe watches the site too.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      every command and its effect: create the API token
      (Workers Scripts edit on the account; Workers Routes
      edit on the pyeconomics.dev zone) and store it with
      `gh secret set CLOUDFLARE_API_TOKEN --env staging`;
      set CLOUDFLARE_ACCOUNT_ID as an environment variable;
      pipe the existing staging edge credential into
      `npx wrangler secret put EDGE_CREDENTIAL --env staging`
      for the new Worker without displaying it; create the
      Access application for staging.pyeconomics.dev with
      the maintainer's Allow policy and the existing service
      token's Service Auth policy; and approve the merge when
      the checks are green. Record what was done, never a
      value, in the PR body.
    </requirement>

    <requirement>
      The Worker: one module serves both Workers. With an
      ASSETS binding present, requests outside the API's
      paths never reach it (run_worker_first); on the API's
      paths it forwards as today. Extend worker.test.mjs:
      API paths forward with the credential and without
      cookies or Access headers; /healthz still maps to the
      origin's /version; the nosniff header is added; a
      non-API path never reaches the fetch stub.
    </requirement>

    <requirement>
      web/wrangler.jsonc: `main` the shared Worker module;
      `assets` with directory ./dist, binding ASSETS,
      run_worker_first decision 3's list,
      not_found_handling "404-page", html_handling
      "auto-trailing-slash"; workers_dev and preview_urls
      false; env `staging` (name pyeconomics-web-staging,
      custom domain staging.pyeconomics.dev, ORIGIN_URL
      the staging origin) and env `production` declared
      for Step 13 but not deployed.
    </requirement>

    <requirement>
      deploy-staging.yml gains a `site` job after the API
      job (needs: deploy), in the `staging` environment
      with contents: read only: `npm ci`, the site data
      export from the merge commit, the staging build,
      `npx wrangler deploy --env staging` with the scoped
      token; then verify with the service token:
      /version.json equals the commit, `/` answers 200 with
      the exact CSP from dist/_headers and `X-Robots-Tag:
      noindex`, `/v1/models` answers 200 through the same
      host, and a request without the token is refused; on
      failure, roll back to the previous Worker version
      and fail. The concurrency group never cancels a
      running deploy.
    </requirement>

    <requirement>
      The rate rule: re-express the one Free-plan rule by
      path (the API's paths, so every staging host and,
      from Step 13, production are covered), keep 50
      requests per 10 seconds per IP unless decision 3 says
      otherwise, and record the expression in the runbook;
      a burst through staging.pyeconomics.dev's /v1 trips
      it (waves of 30 spaced 1.5 s apart, the lag Phase 4
      measured).
    </requirement>

    <requirement>
      staging-health.yml probes the site too (/version.json
      equals the newest successful deploy's SHA; `/` carries
      the CSP), opening its `staging-health` issue on
      failure as it does for the API.
    </requirement>

    <requirement>
      docs/operations/staging.md: the site's topology,
      deploy and rollback (`wrangler rollback` and
      `wrangler versions deploy`), the Access application,
      rotating the Cloudflare API token (its expiry
      recorded) and the rate rule's expression.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      and Phase 4 check 64 to admit CLOUDFLARE_API_TOKEN in
      deploy-staging.yml's `staging` set, each with an
      addendum line in that phase's roadmap.
    </requirement>

    <requirement>
      Filepath comment: JavaScript starts with `// <path>`;
      JSONC carries a leading `// <path>` comment; YAML with
      `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 4 acceptance criteria

- One Worker module serves the staging API host and the staging site; its
  tests prove the API forwarding, the `/healthz` mapping, the stripped
  headers and that static paths never reach it.
- `deploy-staging.yml` deploys the API, then the site, on every merge, and
  rolls the site back on a failed verification; the scoped token lives
  only in the `staging` environment.
- `staging.pyeconomics.dev` refuses requests without Access; the rate rule
  covers the API's paths on every staging host and trips under a burst;
  `staging-health.yml` probes the site.
- Phase 3 check 78 and Phase 4 check 64 are narrowed with their addendum
  lines; the runbook covers the site.
- **Deployed & verified:** the `deploy-staging.yml` run on this step's
  merge commit succeeded in both jobs; with the service token from the
  maintainer's keyring, `https://staging.pyeconomics.dev/version.json`
  reports that SHA, `/` answers 200 with the CSP from `dist/_headers` and
  `X-Robots-Tag: noindex`, and `/v1/models` answers 200 through the same
  host; without the token the host answers Access's login; the newest
  `staging-health` run is green.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, actionlint and zizmor clean on both
  workflows — the API token is least-privilege and environment-scoped, the
  Worker forwards no cookie or Access header, and no secret value appears
  in the repository, a log or the PR.

---

## Step 5 — Generated Model Pages

**Status:** Not started

> **Goal:** Give every registered model a prerendered page generated from
> the registry, and make the problem-type URIs resolve. Add an Astro
> content collection over the site data Step 3's export writes, rendering
> `/models/<domain>/<name>/` (ADR-0013 decision 2) for every model: title,
> summary, the formula through KaTeX at build time, variables and units
> from the input and output schemas, assumptions, limitations, evidence
> status, cost class, citations, the data each bound field can read with
> its licence class and hosted availability, the worked example (the first
> example's inputs and `example_result`), the model's changelog, and links
> to its documentation page, REST route, MCP tool and CLI command; add
> `/models/` and a domain index for each domain (Step 7 builds the
> navigation around them), `/problems/<slug>/` for every row of the error
> table, so `https://pyeconomics.dev/problems/<slug>` answers once
> production is public, schema.org JSON-LD and a build-time Open Graph
> image for every page, `@astrojs/sitemap`, a `robots.txt` that refuses
> indexing on staging and pre-release builds, redirects from every model
> alias to its model's page, a 404 page, and a released-page ledger so a
> page that has shipped never disappears. Card text is trusted repository
> content, and it is still rendered without raw HTML. Parent: ROADMAP §4
> 5.2 (first bullet); ADR-0006; ADR-0012 decision 4; ADR-0013 decisions 2
> and 19.

**Branch:** `feature/phase05-step5-model-pages`

**Deploys:** the staging site on `staging.pyeconomics.dev` (behind Access)
— this merge redeploys it through `deploy-staging.yml`'s `site` job with
every model page; production receives the pages with Step 17's release
candidate.

|               |          | Cost                 | Balanced             | Quality            |
| ------------- | -------- | -------------------- | -------------------- | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**      | **GPT-6.1 Sol**      | **Gemini 4 Argon** |
|               | Platform | Codex                | Codex                | Antigravity        |
|               | Level    | Low                  | High                 | High               |
|               | AA       | 42.1                 | 50.2                 | 52.6               |
|               | Price    | $1.36/1M             | $2.18/1M             | $4.00/1M*          |
| **Runner‑up** | Model    | **Gemini 3.8 Flash** | **Sonnet 5.5**       | **Opus 5.5**       |
|               | Platform | Antigravity          | Claude Code          | Claude Code        |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 39.8                 | 46.8                 | 53.6               |
|               | Price    | $2.19/1M             | $3.03/1M             | $6.02/1M           |
| **Backup**    | Model    | **Sonnet 5.5**       | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    |
|               | Platform | Claude Code          | Antigravity          | Codex              |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 40.8                 | 40.9                 | 50.2               |
|               | Price    | $2.69/1M             | $4.29/1M             | $2.18/1M           |

Ranked for coding, medium complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY: a content collection, page and
component templates, a handful of build-time generators (formulas, Open
Graph images, JSON-LD, the sitemap and the ledger) and their tests, over a
registry whose shape Phase 4 fixed. Complexity is Medium — the data is
deterministic and the stack is Step 3's — and the step is not novel. The
ladder's Balanced column runs: GPT-6.1 Sol on Codex at Intelligence High
(ChatGPT Pro; AA Intelligence Index 50.2), Runner-up Sonnet 5.5 on Claude
Code at Effort High, Backup Gemini 3.8 Flash on Antigravity. Cost runs
GPT-6.1 Sol at Intelligence Low (42.1) and Quality Gemini 4 Argon on
Antigravity at Effort High (52.6). New conversation per phase-boundary
hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step5-model-pages`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 5 is
       complete. You can now move
       on to Step 6." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 6.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Model text reaches HTML only through Astro's escaping
      or a Markdown renderer with raw HTML disabled; a test
      plants `<script>` and an `onerror=` attribute in a toy
      card and finds neither in the built page.
    - KaTeX runs at build time with `trust: false` and
      `throwOnError: true`, so a formula can neither inject
      markup nor fail silently; no formula reaches the
      browser as script.
    - No page carries a key, an internal hostname or a
      `*.run.app` origin; the built `dist/` is scanned by the
      gate's secret patterns in the web job.
  </security>

  <context>
    pyeconomics. Phase 5. Step 5: generated model pages.

    Current state (post-Phase-5 Step 4):

    - web/ builds a static Astro site with React islands,
      Tailwind, shadcn/ui and KaTeX, under ADR-0013's CSP,
      from site data exported at build time
      (scripts/web/export_site_data.py writes registry.json,
      openapi.json, problems.json and the provider and
      concept summaries into a git-ignored directory). The
      layout carries the brand, the CFA® notice and the
      disclaimer footer.
    - Every merge deploys the API and then the staging site
      through deploy-staging.yml to staging.pyeconomics.dev
      behind Access; /version.json reports the build's SHA.
    - registry.json holds 50 models in 13 domains, each with
      the 23 describe() keys, example_result and
      example_figure. Problem rows live in
      surfaces/problems.py ROWS; docs/_ext/problem_pages.py
      already renders them for the documentation.
    - Model ids are permanent (ADR-0003); an alias is a
      retired id that still resolves to its model.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 2, 9
      and 19) and ADR-0006.
    - web/ in full (layout, export script, tests, CI).
    - src/pyeconomics/core/describe.py, core/cards.py and
      surfaces/registry_export.py, registry_schema.py.
    - src/pyeconomics/surfaces/problems.py and
      docs/_ext/problem_pages.py, model_pages.py.
    - One generated card under docs/reference/models/.
  </context>

  <goal>
    Every model has a page at its permanent URL with every
    section its card has, a structured-data block and a
    social image; every problem type resolves to a page; the
    sitemap lists them all; staging and pre-release builds
    ask not to be indexed; the ledger keeps shipped pages
    alive.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      A content collection with a loader over the exported
      registry.json (validated by a Zod schema that mirrors
      REGISTRY_SCHEMA's required keys, so a registry change
      that the pages cannot render fails the build), and
      web/src/pages/models/[domain]/[name].astro generating
      one page per model at the URL decision 2 derives from
      its id. Sections in this order: summary, formula,
      variables (inputs and outputs: name, description, unit,
      bounds), worked example, assumptions, limitations,
      evidence status (with what the status means), data
      (bound models: each field's concept, candidates,
      licence class and whether hosted mode serves it, from
      the export), citations (with DOI or URL links),
      changelog, and "use it elsewhere" (the docs page, the
      REST route, the MCP tool name when the model has a
      headline tool, the CLI command). Step 6 adds the
      calculator island and Step 7 the syllabus tags.
    </requirement>

    <requirement>
      KaTeX renders every formula at build time; the build
      fails on any KaTeX error; the KaTeX stylesheet and
      fonts are self-hosted. A model page ships no
      JavaScript but the islands later steps add.
    </requirement>

    <requirement>
      /problems/[slug].astro for every row of the error
      table (exported to problems.json): title, HTTP status,
      CLI exit code, what it means and what to do, with the
      local-mode command where the problem points to local
      mode (budgets.local_command). A test holds the page set
      equal to problems.ROWS, so a new row without a page
      fails CI.
    </requirement>

    <requirement>
      /models/ (every model by domain) and
      /models/[domain]/ (the domain's models with summary,
      evidence status and cost class), minimal until Step 7.
    </requirement>

    <requirement>
      Structured data and social images: each model page
      carries schema.org JSON-LD (a WebPage about the model,
      with its citations, `isAccessibleForFree`, and a
      BreadcrumbList), a canonical link on the production
      origin, Open Graph and Twitter card tags, and a
      1200x630 image generated at build time with the tool
      decision 2 names. A test parses every JSON-LD block.
    </requirement>

    <requirement>
      Indexing: @astrojs/sitemap lists every page on the
      production origin; robots.txt names the sitemap. A
      build of a pre-release version, and every staging
      build, writes `Disallow: /` and sends `X-Robots-Tag:
      noindex` through _headers; a final release's
      production build allows indexing (the build reads the
      version). Tests cover both builds.
    </requirement>

    <requirement>
      Aliases and the ledger: _redirects sends each alias's
      URL to its model's page (301). web/released-pages.json
      records every page URL a release has shipped (Step 17
      writes the first entries); a test fails if a URL in it
      neither builds nor redirects, the pages' equivalent of
      the released-id ledger.
    </requirement>

    <requirement>
      Tests (Vitest over the built HTML, Playwright on
      staging-shaped builds): the model page count equals the
      registry's; every page has every required section and a
      valid KaTeX render; every internal link in dist/
      resolves; no page holds raw HTML from card text; axe
      finds no WCAG 2.2 AA violation on /models/, one domain
      page, five model pages (one per cost class, a bound
      model and a model with a chart) and a problem page;
      the Lighthouse sample pages that exist now meet
      decision 19's scores in CI.
    </requirement>

    <requirement>
      Filepath comment: every new TypeScript, Astro or
      JavaScript file starts with `// <path>` (Astro
      frontmatter comment); YAML and TOML with `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 5 acceptance criteria

- Every registered model has a page at its decision-2 URL with every
  required section; the page count equals the registry's, and a registry
  change the pages cannot render fails the build.
- Every row of the error table has a page under `/problems/`, held equal to
  `problems.ROWS` by a test.
- Every model page carries valid JSON-LD, a canonical link, Open Graph tags
  and a generated image; the sitemap lists every page; staging and
  pre-release builds refuse indexing and a final release build allows it.
- Every alias redirects to its model's page; the released-page ledger test
  exists and passes.
- The web job's tests pass: sections, KaTeX, internal links, the raw-HTML
  test, axe on the sample with no WCAG 2.2 AA violation, and Lighthouse on
  the sample pages that exist at the decision-19 scores.
- **Deployed & verified:** through the staging edge with the service token
  from the maintainer's keyring, `/version.json` reports this step's merge
  SHA, `/models/fixed-income/duration/` and `/problems/invalid-input/`
  answer 200 with the CSP header, `/sitemap-index.xml` lists all 50 model
  pages, and every response carries `X-Robots-Tag: noindex`.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean (ESLint security included), dependency audit clean — card text
  renders without raw HTML, KaTeX runs untrusted-off, and the built site
  holds no key, internal hostname or origin URL.

---

## Step 6 — Calculators and Web Parity

**Status:** Not started

> **Goal:** Put a working calculator on every model page and prove it
> returns the Python API's bytes. Add a React island (ADR-0013 decision 8)
> that renders the model's own input schema with RJSF 6 and its shadcn/ui
> theme, validated by validators precompiled at build time so the CSP needs
> no `'unsafe-eval'`; posts the canonical JSON of the inputs to
> `POST /v1/models/{id}/run` on its own origin and renders the canonical
> result it receives without re-serializing it — outputs with their units,
> warnings, and the manifest's data sources with each source's attribution,
> notices and as-of date; draws charts with a TypeScript port of
> `core.plotting.figure_of` on Plotly.js's basic bundle (the version the
> `[plot]` extra bundles, loaded only when a chart renders, with
> `plotly.css` and its no-inline-styles marker); offers every download
> format through `?format=`; offers "live data" for a bound model wherever
> hosted mode can serve it and the user's own values otherwise; generates
> "copy as Python, CLI, curl and MCP" snippets from the same inputs, each
> run in CI; shows problems from the error table with their pages; and adds
> the web surface to the parity evidence: every golden case's request built
> by the island's own code returns the Python API's bytes from a local
> server in CI, and `scripts/parity/check_deployed.py` checks one golden
> case per domain through a deployed API. Parent: ROADMAP §4 5.2 (second
> bullet) and the Phase 5 acceptance criterion on web parity; ADR-0012
> decisions 3, 9 and 12; ADR-0013 decisions 8 and 9.

**Branch:** `feature/phase05-step6-calculators`

**Deploys:** the staging site on `staging.pyeconomics.dev` (behind Access)
through `deploy-staging.yml`'s `site` job — the calculators run against the
staging API on the same origin; production receives them with Step 17's
release candidate.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | High               | High               | XHigh              |
|               | AA       | 50.2               | 52.6               | 56                 |
|               | Price    | $2.18/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | XHigh              | High               | High               |
|               | AA       | 51.9               | 53.6               | 52.6               |
|               | Price    | $3.56/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | XHigh              | XHigh              |
|               | AA       | not measured       | 51                 | 52.4               |
|               | Price    | $2.40/1M*          | $4.00/1M           | $16.36/1M          |

Ranked for coding, high complexity. Price: list $ per 1M tokens (3 in : 1 out) ×
the tokens the model uses at that level; * token use not yet measured, a typical
model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY: a schema-driven form over fifty
real schemas (the largest 32 KB, with nested calculations), a chart port
held equal to the Python figures, a download and snippet layer, and a
parity harness across two languages. Complexity is High — a byte
difference between the island's request and the Python API's inputs (the
canonical JSON integer and float quirk among them) is exactly what the
parity suite exists to catch — and the step is not novel. The ladder's
Balanced column runs: Gemini 4 Argon on Antigravity at Effort High with
Thinking on (Google AI Ultra; AA Intelligence Index 52.6), Runner-up Opus
5.5 on Claude Code at Effort High, Backup GPT-6.1 Sol on Codex at
Intelligence XHigh. Cost runs GPT-6.1 Sol at Intelligence High (50.2) and
Quality Opus 5.5 at Effort XHigh (56.0). New conversation per
phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step6-calculators`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 6 is
       complete. You can now move
       on to Step 7." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 7.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - No validator is compiled in the browser: each model's
      validator is generated at build time, and the
      post-build headers check still finds no 'unsafe-eval';
      the Playwright CSP listener runs on every calculator
      it exercises.
    - Output, warning and problem text reaches the page as
      text, never as HTML; a test renders a problem whose
      detail holds markup and finds it escaped.
    - A POST run carries the user's values and is never
      cached or logged (ADR-0012 decision 12); the island
      keeps no input in localStorage, the URL or analytics.
    - Snippets name the public endpoint and the user's own
      inputs only, never a key, a cookie or a header from
      the page.
  </security>

  <context>
    pyeconomics. Phase 5. Step 6: calculators and web
    parity.

    Current state (post-Phase-5 Step 5):

    - Every model has a page at /models/<domain>/<name>/
      with its sections, JSON-LD and image; the staging site
      deploys on every merge and reaches the staging API on
      the same origin (decision 3).
    - The REST API: POST /v1/models/{id}/run takes the raw
      body and answers Result.to_json()'s bytes; a bound run
      takes ?profile=, ?as_of=, ?vintage=, ?concept= and
      ?param=, the body overriding what is bound; ?format=
      gives csv, xlsx, parquet, arrow, bundle or json, each
      carrying attributions and notices; problems are RFC
      9457 with type URIs under /problems/; hosted mode
      allows a 1 MiB body, holds runs to their cost class's
      budget and limits each client (429 with Retry-After).
    - core/plotting.py: figure_of draws line, scatter, bar
      and band charts from a result's document;
      registry.json carries each model's example_figure (no
      template) for its example_result. The [plot] extra's
      Plotly bundles Plotly.js 4.1.1 (mcp/apps.py,
      PLOTLY_JS_VERSION).
    - tests/golden/ holds 354 cited cases across 50 TOML
      files; tests/parity/ proves four surfaces return the
      same bytes; scripts/parity/check_installed.py repeats
      it on the built wheel.
    - Facts read on 2026-10-29 (re-check at kickoff): RJSF's
      precompiled validators (compileSchemaValidators at
      build time, createPrecompiledValidator at run time,
      the same schema in both) exist to avoid unsafe-eval;
      @rjsf/shadcn 6.11 targets Tailwind 4 (add its
      `@source`); Plotly.js's basic bundle (bar, pie,
      scatter; 401 kB gzipped) needs no eval, and with
      plotly.css loaded and the `plotly.js-style-global`
      no-inline-styles marker present it injects no style.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 8, 9
      and 11) and ADR-0012 decisions 3, 9, 10 and 12.
    - web/ in full; scripts/web/export_site_data.py.
    - src/pyeconomics/core/plotting.py, core/spec.py
      (ChartSpec) and mcp/apps.py.
    - src/pyeconomics/server/app.py, formats.py and
      surfaces/problems.py, budgets.py.
    - tests/parity/parity_support.py and
      scripts/parity/check_installed.py.
    - tests/golden/README.md and one golden TOML file.
  </context>

  <goal>
    Every model page runs its model from a form generated
    from its schema and shows the result, chart, warnings,
    sources, downloads and snippets; bound models use data
    where hosted mode can serve it; the island's requests
    return the Python API's bytes for every golden case; a
    deployed API is checked the same way.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Validators: scripts/web/compile_validators.mjs runs
      after the site data export and compiles each model's
      input schema with compileSchemaValidators into
      web/src/data/generated/validators/ (git-ignored); the
      island loads its model's module and builds the
      validator with createPrecompiledValidator against the
      same schema. A build with a stale validator fails.
      The server's validation stays the model's own (Surface
      rules); a 422 problem is shown field by field when its
      detail names a field.
    </requirement>

    <requirement>
      The island (client:visible): the RJSF form with the
      shadcn theme, labels and help from the schema's titles,
      descriptions and units, the first example as the
      prefilled values, a calculation selector where the
      schema has one; on submit, the inputs' JSON posted to
      POST /v1/models/{id}/run through the generated client
      with `Content-Type: application/json`; the response
      bytes kept as received for "copy JSON" and the JSON
      download. A test renders every model's form with each
      of its examples and finds no validation error.
    </requirement>

    <requirement>
      Results: outputs as a table driven by the output
      schema (units shown; long arrays paged), warnings, and
      a sources panel built from the manifest's data_sources
      (attribution, notices, licence class, terms page, as-of
      and retrieval time, `revised_data` explained when
      present). Problems show their title and detail as
      text, link /problems/<slug>/, and give the local-mode
      command for input-too-large and budget-exceeded; 429
      shows when to retry.
    </requirement>

    <requirement>
      Charts: web/src/lib/figure.ts ports figure_of
      (line, scatter, bar, band; the same trace and layout
      keys); a Vitest test holds figureOf(model,
      example_result) deep-equal to example_figure for every
      model with charts. Plotly.js's basic dist at the
      version mcp/apps.py's PLOTLY_JS_VERSION names (a test
      holds the two equal), imported dynamically when a chart
      first renders, with plotly.css self-hosted and the
      no-inline-styles marker in the layout.
    </requirement>

    <requirement>
      Downloads: CSV, XLSX, Parquet, Arrow, JSON and the
      reproducibility bundle through ?format= on a POST with
      the same body, saved under the response's filename; a
      Playwright test downloads a CSV and finds its
      attribution block.
    </requirement>

    <requirement>
      Bound models (decision 11): the export's hosted
      availability says, per bound model and profile,
      whether hosted mode can serve every field; where it
      can, a "live data" control posts with ?profile= (and
      an optional as-of date) and the form's values override
      what is bound; where it cannot, the page says which
      fields need data the hosted site may not serve and
      offers the user's own values or the local app. Step 10
      lights up local mode.
    </requirement>

    <requirement>
      Snippets from the same inputs: Python
      (`pyeconomics.run`), the CLI (`pyeconomics models run
      <id> --inputs -` with the JSON on standard input), curl
      against https://pyeconomics.dev, and the MCP
      `run_model` call's arguments; plain `<pre>` with a
      copy button. CI runs each kind for one model per
      domain: Python and the CLI from the locked
      environment, curl against a local `pyeconomics serve`,
      MCP through the in-memory client.
    </requirement>

    <requirement>
      Web parity (decision 8): the site data export also
      writes every golden case's inputs and the Python API's
      canonical bytes for them (computed in the same locked
      environment); web/tests/parity/ builds each request
      with the island's own request builder, posts it to a
      local `pyeconomics serve` in the web job, and compares
      the bytes. A difference is a bug in the side that
      changed them, never a loosened comparison.
      scripts/parity/check_deployed.py runs one golden case
      per domain through a deployed API (staging with the
      Access service token; production later) against
      expected bytes computed from the same commit's wheel
      under Python 3.14 with uv.lock's versions, as the
      container runs.
    </requirement>

    <requirement>
      Accessibility and performance: keyboard operation of
      every control, errors announced through aria-live,
      focus moved to the result; axe finds no WCAG 2.2 AA
      violation on a calculator before and after a run;
      model pages in decision 19's sample keep their
      Lighthouse scores with the island present.
    </requirement>

    <requirement>
      Filepath comment: every new TypeScript, JavaScript and
      Astro file starts with `// <path>`; a new Python file
      gets the three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 6 acceptance criteria

- Every model page runs its model from its schema with precompiled
  validators; every model's form renders each of its examples without a
  validation error; no `'unsafe-eval'` appears and no CSP violation is
  recorded.
- Results show outputs with units, warnings and the sources panel with
  attributions and notices; problems link their pages and give the local
  command where they point to local mode.
- `figureOf` equals `example_figure` for every charted model; the Plotly.js
  version equals `PLOTLY_JS_VERSION`; charts load only when rendered.
- Every download format works, and a downloaded CSV carries its
  attribution block.
- Bound models offer live data where the export says hosted mode can serve
  it, and say why not elsewhere.
- Each snippet kind runs for one model per domain in CI.
- The web parity suite returns the Python API's bytes for all 354 golden
  cases through the island's request builder in the `web` job.
- axe finds no WCAG 2.2 AA violation on a calculator before and after a
  run, and the sampled model pages keep decision 19's Lighthouse scores.
- **Deployed & verified:** with the service token,
  `https://staging.pyeconomics.dev/version.json` reports this step's merge
  SHA, a Playwright run against staging fills
  `/models/fixed-income/duration/`'s calculator and gets the result, and
  `scripts/parity/check_deployed.py` passes for one golden case per domain
  through the staging API.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — no validator compiles in the browser,
  result and problem text renders as text, and no input is stored, logged
  or sent anywhere but the run request.

---

## Step 7 — Navigation, Search, Syllabus Seed and Coverage Matrix

**Status:** Not started

> **Goal:** Make the catalog findable. Build the fifteen domain sections of
> ROADMAP §4 7.2 — the thirteen populated domains and `micro` and
> `alternatives` as planned sections that name Phase 7 and link the
> coverage matrix — with the header navigation, breadcrumbs and domain
> index pages; add Pagefind, built after the site, behind `/search/` and a
> header search box; create `syllabi/` in the format ADR-0013 decision 12
> fixes (a JSON Schema and one TOML file per syllabus version) with its
> seed, the 2027 CFA® Program topic areas for Levels I to III mapped to the
> fifty launch entries, factual names only, each linking to the issuing
> body, which the maintainer reviews; add filters on `/models/` by domain,
> syllabus level and topic, evidence status, cost class, data needs and
> tag, with neutral slugs that never carry a mark; compute related models
> at build time; publish `/coverage/`, the coverage matrix generated from
> the registry and `syllabi/`; and show the seed tags on the documentation's
> model pages too, rewording the cards' "Not yet mapped" note. Parent:
> ROADMAP §4 5.3 and 7.1; §5 "CFA Institute marks and content"; ADR-0013
> decisions 10 and 12.

**Branch:** `feature/phase05-step7-navigation-search`

**Deploys:** the staging site on `staging.pyeconomics.dev` (behind Access)
through `deploy-staging.yml`'s `site` job; the Read the Docs `main` preview
rebuilds with the cards' curriculum tags.

|               |          | Cost                 | Balanced             | Quality            |
| ------------- | -------- | -------------------- | -------------------- | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**      | **GPT-6.1 Sol**      | **Gemini 4 Argon** |
|               | Platform | Codex                | Codex                | Antigravity        |
|               | Level    | Low                  | High                 | High               |
|               | AA       | 42.1                 | 50.2                 | 52.6               |
|               | Price    | $1.36/1M             | $2.18/1M             | $4.00/1M*          |
| **Runner‑up** | Model    | **Gemini 3.8 Flash** | **Sonnet 5.5**       | **Opus 5.5**       |
|               | Platform | Antigravity          | Claude Code          | Claude Code        |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 39.8                 | 46.8                 | 53.6               |
|               | Price    | $2.19/1M             | $3.03/1M             | $6.02/1M           |
| **Backup**    | Model    | **Sonnet 5.5**       | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    |
|               | Platform | Claude Code          | Antigravity          | Codex              |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 40.8                 | 40.9                 | 50.2               |
|               | Price    | $2.69/1M             | $4.29/1M             | $2.18/1M           |

Ranked for coding, medium complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: navigation
and filter components, a build-time search index, a small data format with
its schema and loader, a generated matrix, and a seed mapping that needs a
charterholder's eye on fifty entries. Complexity is Medium — the patterns
are standard and the data is small — and the step is not novel. The
ladder's Balanced column runs: GPT-6.1 Sol on Codex at Intelligence High
(ChatGPT Pro; AA Intelligence Index 50.2), Runner-up Sonnet 5.5 on Claude
Code at Effort High, Backup Gemini 3.8 Flash on Antigravity. Cost runs
GPT-6.1 Sol at Intelligence Low (42.1) and Quality Gemini 4 Argon on
Antigravity at Effort High (52.6). New conversation per phase-boundary
hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step7-navigation-search`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 7 is
       complete. You can now move
       on to Step 8." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 8.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Search runs entirely in the browser from files the
      site serves: no query leaves the page, no third party
      is called, and the CSP stays decision 9's (Pagefind's
      WebAssembly allowed only as that decision says).
    - Filter state lives in the URL's query string and is
      read as data only: values are matched against the
      known sets, never inserted into the page as HTML.
    - syllabi/ stores no learning-outcome wording, reading
      title or exam content: topic names, levels, links and
      model ids only; a test refuses any text field longer
      than a topic name.
  </security>

  <context>
    pyeconomics. Phase 5. Step 7: navigation, search, the
    syllabus seed and the coverage matrix.

    Current state (post-Phase-5 Step 6):

    - Every model has a page with its calculator; /models/
      and the 13 domain index pages are minimal; problem
      pages, the sitemap and the ledger exist; the staging
      site deploys on every merge.
    - Model tags are topic words. Every card's curriculum
      section reads "Not yet mapped; syllabus crosswalks
      arrive in Phase 7" (core/cards.py, CURRICULUM_NOTE).
    - ROADMAP §5: syllabus mappings are factual tags that
      link to cfainstitute.org; the mark is used as an
      adjective with ® on first use; until CFA Institute's
      legal team answers (Step 16 asks), no URL path carries
      the mark, so filters use neutral slugs. No
      learning-outcome statement, reading or example is
      copied.
    - ROADMAP §4 7.1 keeps every other syllabus (FRM, CAIA,
      CIPM, CMT, CQF) and full coverage for Phase 7.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 2, 10
      and 12).
    - web/ in full; web/src/pages/models/.
    - src/pyeconomics/core/cards.py and the docs model page
      extension (docs/_ext/model_pages.py).
    - docs/roadmap/ROADMAP.md §4 7.1 and 7.2 and §5 "CFA
      Institute marks and content".
    - CFA Institute's published 2027 Program topic outline
      (topic names and levels only), read at kickoff.
  </context>

  <goal>
    A visitor reaches any model from the header, a domain
    page, search or a filter; the syllabus seed tags the
    launch catalog factually; the coverage matrix shows what
    is covered and what is not; the cards in the docs show
    the same tags.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Navigation: the fifteen domains in ROADMAP §4 7.2's
      order in the header (a disclosure menu on small
      screens, keyboard-operable), breadcrumbs on every page,
      a domain page for each populated domain (its models
      grouped by evidence status, with summary, cost class
      and data needs) and for `micro` and `alternatives` an
      empty-state page that says the domain arrives in Phase
      7 and links /coverage/.
    </requirement>

    <requirement>
      Search: Pagefind indexes dist/ after the build (model,
      domain, problem, source and legal pages; the 404 page
      and redirects excluded) and serves /search/ and a
      header box as a small island using Pagefind's own
      JavaScript API; results show the model's domain and
      summary. A test builds the index and finds every model
      by its title and by its id.
    </requirement>

    <requirement>
      syllabi/: a JSON Schema (syllabi/schema.json) and the
      seed for the 2027 outline, one entry per level and
      topic area (a neutral id, the displayed title, the
      level, a link to the issuing body's page), and per
      model id the topic ids it implements. Seed every one of
      the fifty launch entries the agent can map from the
      outline's topic names and the card's own content;
      put the full mapping to the maintainer for review in
      one batched question and record their corrections. One
      Python loader (scripts/web/syllabi.py) validates the
      files against the schema, refuses an unknown model id,
      and feeds both the site data export and the docs
      extension.
    </requirement>

    <requirement>
      Filters on /models/: domain, syllabus level and topic,
      evidence status, cost class, data needs (data-free or
      bound) and tag, combinable, reflected in the query
      string with neutral values, and computed from the
      build's data in a small island; counts shown per
      option. A Vitest suite holds the filter logic to the
      registry and the seed.
    </requirement>

    <requirement>
      Related models: at build time, up to four per page by
      shared syllabus topics, then shared tags, then shared
      references, then domain; deterministic order; shown on
      each model page.
    </requirement>

    <requirement>
      /coverage/: the matrix of the seed's topics by level
      against the registry: each topic's implemented models
      (all fifty are verified by the model definition of
      done), and the topics no model covers yet, marked as
      Phase 7's; a second view by domain counting models and
      planned domains. Generated, never hand-edited; a test
      holds its counts to the registry and the seed.
    </requirement>

    <requirement>
      Cards: the documentation's model pages list the
      model's seed tags (title and link) in the curriculum
      section, through docs/_ext/model_pages.py and the
      loader. The crosswalk is repository data the wheel
      does not carry (ROADMAP §4 7.1: data, never package
      structure), so core/cards.py's CURRICULUM_NOTE is
      reworded to point at the web and documentation pages
      instead of promising Phase 7; the registry snapshot is
      updated for the new text; no model's outputs or
      version change.
    </requirement>

    <requirement>
      Marks: every page that names the Program uses the mark
      as an adjective with ® on first use, and the footer's
      non-affiliation notice is present; a test scans dist/
      for `cfa` in any URL path or query value and fails on
      one.
    </requirement>

    <requirement>
      Tests: axe on /models/ with filters applied, /search/
      with results, /coverage/ and an empty-state domain
      page; keyboard navigation of the header menu and the
      filters (Playwright); the Lighthouse sample's
      /search/ and /coverage/ at decision 19's scores.
    </requirement>

    <requirement>
      Filepath comment: every new file gets the
      repo-relative path as the first line where its type
      allows a comment (JSON Schema carries `$comment`).
    </requirement>
  </requirements>
</task>
```

### Step 7 acceptance criteria

- The header lists fifteen domains; every populated domain page lists its
  models; `micro` and `alternatives` show their Phase 7 empty states; every
  page has breadcrumbs, and the menus work from the keyboard.
- `/search/` and the header box find every model by title and by id, with
  no request leaving the site.
- `syllabi/` holds the schema and the 2027 seed for all fifty launch
  entries, reviewed by the maintainer (corrections recorded in the PR);
  the loader refuses unknown ids and over-long text.
- Filters, related models and `/coverage/` render from the registry and
  the seed, with tests holding their counts; no URL carries the mark.
- The documentation's cards list each model's seed tags.
- axe finds no WCAG 2.2 AA violation on the new pages; `/search/` and
  `/coverage/` meet decision 19's Lighthouse scores in CI.
- **Deployed & verified:** through the staging edge with the service token,
  `/version.json` reports this step's merge SHA, `/search/` returns results
  for `duration`, `/coverage/` and `/models/micro/` answer 200, and a
  filtered `/models/` URL renders the expected count; the Read the Docs
  `main` build for the same SHA shows a card's curriculum tags.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean (Pagefind included) — search sends no
  query off the page, filter values never become HTML, and `syllabi/`
  holds no curriculum wording.

---

## Step 8 — Hosted Data Plane: Snapshots

**Status:** Not started

> **Goal:** Replace hosted mode's per-request fetches with scheduled
> snapshots of the originators (ADR-0012 decision 11; ADR-0013 decision 6),
> on staging first. Add `src/pyeconomics/data/snapshots/`: the declared
> snapshot set, computed from the catalog and the registry (every
> hosted-safe originator candidate of every concept, with parameterized
> concepts expanded over a declared list), never FRED, never an
> aggregator, and never a series whose terms forbid storage
> (`cache.policy.may_store` stays the one gate); a writer, run as a Cloud
> Run job in hosted mode, that fetches the set, writes one gzip-compressed
> canonical-JSON object per provider and run into a Cloud Storage bucket
> mounted into the job, keeps the last good object of a provider whose
> fetch failed, writes `current.json` last and reports to a heartbeat URL;
> and a reader that, when `PYECONOMICS_SNAPSHOT_DIR` names the bucket
> mounted read-only into the service, answers every hosted series from the
> snapshot with its retrieval time, refuses a series outside the set with a
> new `not-in-snapshot` problem that points to local mode, and serves a
> stale snapshot with a `stale_snapshot` warning rather than failing.
> Provision the staging bucket (versioned, public access prevented), the
> job's identity and provider keys in Secret Manager, the job, and a daily
> Cloud Scheduler trigger; deploy the job's image with every staging deploy,
> data before API; and write the snapshot runbooks. Parent: ROADMAP §3; §4
> 5.8 (the snapshot job); §5 "Data licensing policy" rules 3 and 4,
> "Operations & observability strategy" rule 6; ADR-0005; ADR-0011;
> ADR-0012 decision 11; ADR-0013 decision 6.

**Branch:** `feature/phase05-step8-snapshots`

**Deploys:** the staging snapshot job, its bucket and schedule, and the
staging API reading snapshots — this merge deploys the job's image and then
the API through `deploy-staging.yml`; the Deployed & verified check runs the
job once, then reads a series through the edge. Production gets the same
plane in Step 13.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | High               | High               | XHigh              |
|               | AA       | 50.2               | 52.6               | 56                 |
|               | Price    | $2.18/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | XHigh              | High               | High               |
|               | AA       | 51.9               | 53.6               | 52.6               |
|               | Price    | $3.56/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | XHigh              | XHigh              |
|               | AA       | not measured       | 51                 | 52.4               |
|               | Price    | $2.40/1M*          | $4.00/1M           | $16.36/1M          |

Ranked for coding, high complexity. Price: list $ per 1M tokens (3 in : 1 out) ×
the tokens the model uses at that level; * token use not yet measured, a typical
model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: a data-layer
store with a writer and a reader under the layering, storage and licence
rules Phase 3 fixed, a new error row, and a provisioning run for a bucket,
a job, a schedule and secrets. Complexity is High — a snapshot is
licensed data at rest, the reader is on every hosted series request, and
staleness and partial failure must degrade rather than break — but the
step is not novel: the cache already stores validated canonical-JSON
frames. The ladder's Balanced column runs: Gemini 4 Argon on Antigravity
at Effort High with Thinking on (Google AI Ultra; AA Intelligence Index
52.6), Runner-up Opus 5.5 on Claude Code at Effort High, Backup GPT-6.1
Sol on Codex at Intelligence XHigh. Cost runs GPT-6.1 Sol at Intelligence
High (50.2) and Quality Opus 5.5 at Effort XHigh (56.0). New conversation
per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step8-snapshots`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 8 is
       complete. You can now move
       on to Step 9." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 9.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Licence: the writer runs in hosted mode, so a source
      not hosted-safe is refused before any request; a test
      proves FRED, every library-only source and every
      storage-forbidden series are absent from the set and
      from every written object.
    - Keys: the job reads its provider keys (BEA, and BLS
      and Census for their limits) from Secret Manager by
      pinned version as `<PROVIDER>_API_KEY`; the service
      holds none. LeakCheck proves no key reaches a snapshot
      object, `current.json`, a log record or a problem.
    - Parsing: the reader validates every object back into
      frames with the cache's codec (canonical JSON, never a
      pickle, gzip with a decompressed-size cap) and checks
      each object's SHA-256 against `current.json` before
      trusting it; a bad object is reported and skipped,
      the previous one served.
    - Least privilege: the job's identity may write objects
      in its bucket and read its key secrets; the service's
      runtime identity may only read objects; the scheduler
      may only invoke the job; the bucket has public access
      prevention enforced and uniform access.
    - The heartbeat URL is a secret (whoever holds it can
      fake a heartbeat): Secret Manager only, registered with
      redaction, never logged.
  </security>

  <context>
    pyeconomics. Phase 5. Step 8: the hosted data plane.

    Current state (post-Phase-5 Step 7):

    - Hosted mode (PYECONOMICS_MODE=hosted) fetches
      hosted-safe originators per request through the
      worker pool, refusing every other class in the
      resolver and in the provider. The cache
      (data/cache/) stores canonical-JSON frame payloads
      validated back into frames; may_store refuses
      storage-forbidden terms before any store code;
      cache.bypass() and Fetched/Origin exist.
    - data/ rules: only data/transport/ opens a socket; a
      module that reads files or the clock joins IO_MODULES,
      a pure one PURE_MODULES (tests/data/test_layering.py);
      a new PyeconomicsError subclass gets a row in
      problems.ROWS; config refuses credential-like
      PYECONOMICS_* names except config._SERVER_SECRETS.
    - Staging: project pyeconomics-staging, service
      pyeconomics-api-staging (1 GiB, max 2), runtime and
      deploy identities (service-level role since Step 1),
      Secret Manager, deploy-staging.yml (job, then API,
      then site from Step 4).
    - Facts read on 2026-10-29 (re-check at kickoff): Cloud
      Run's Cloud Storage volume mounts are GA for services
      and jobs (gen2 execution environment; read-only
      option; writes upload on close; stat cache 60 s; a
      mount must finish within 30 s; not POSIX, no locks).
      Cloud Storage's Always Free tier gives 5 GB-months of
      Standard storage in us-central1 with 5,000 Class A
      and 50,000 Class B operations a month; noncurrent
      versions and soft-deleted objects bill as live ones
      (soft delete defaults to 7 days). Cloud Scheduler
      gives 3 free jobs per billing account. Cloud Run jobs
      cost $0.000018 per vCPU-second inside a free tier.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 5, 6
      and 15), ADR-0011 and ADR-0012 decisions 10 and 11.
    - src/pyeconomics/data/api.py, resolver, cache/
      (policy.py, store.py, the codec), modes.py, config.py,
      redaction.py and data/catalog/.
    - src/pyeconomics/surfaces/problems.py and the walking
      test; tests/data/test_layering.py; tests/data/
      leakcheck.py; tests/data/catalog/catalog_world.py.
    - Dockerfile, deploy-staging.yml and
      docs/operations/staging.md.
  </context>

  <goal>
    Staging's hosted series and bound runs read snapshots
    written daily by a job, never an upstream per request;
    a missing series is refused with a pointer to local
    mode; a failed or late run degrades to the last good
    data with its date; nothing library-only, storage-
    forbidden or secret is ever written.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      every command and its effect: create the staging
      bucket (us-central1, uniform access, public access
      prevention, object versioning, a lifecycle rule
      deleting noncurrent versions after 30 days), the job
      identity and its bindings (object user on the bucket,
      accessor on its key secrets), the runtime identity's
      object viewer binding, the scheduler identity's
      invoker binding on the job, the key secrets
      (`gcloud secrets versions add bea-api-key
      --data-file=-` and the others, from prompts), the job,
      and the daily schedule at decision 6's hour; and
      approve the merge. Record what was done, never a
      value, in the PR body.
    </requirement>

    <requirement>
      The set (data/snapshots/set.py, pure): computed from
      the catalog's concepts and every bound model's
      profiles; candidates that are hosted-safe originators
      only (no aggregator, no FRED); parameterized concepts
      expanded over a declared list kept in the module; each
      entry checked with may_store, storage-forbidden ones
      excluded and listed. A test pins the set's size and
      that it holds every hosted-safe candidate of every
      bound model's default profile.
    </requirement>

    <requirement>
      The writer (data/snapshots/writer.py, IO_MODULES; the
      job runs `python -m pyeconomics.data.snapshots write`
      in hosted mode inside cache.bypass()): fetches the set
      through data.get within each provider's declared rate
      limits; writes `<run-id>/<provider>.json.gz`
      (canonical-JSON frames, the cache's codec) under
      PYECONOMICS_SNAPSHOT_DIR; a provider that fails keeps
      its previous object in the new `current.json`, marked
      with its failure's problem slug; `current.json` (run
      id, completion time, per provider its object, SHA-256
      and per series the last observation and retrieval
      time) is written last. On completion it requests the
      heartbeat URL (PYECONOMICS_SNAPSHOT_HEARTBEAT, added
      to config._SERVER_SECRETS and redaction) through the
      data layer's transport, to the one host decision 15
      names, declared as a provider's hosts are, so no
      module outside data/transport/ opens a socket. Exit
      code non-zero only when no provider succeeded.
    </requirement>

    <requirement>
      The reader (data/snapshots/reader.py, IO_MODULES):
      with PYECONOMICS_SNAPSHOT_DIR set in hosted mode, every
      series fetch reads the snapshot after the licence gate
      and before any transport; `current.json` is re-read at
      most once a minute; provider objects are verified and
      cached in memory by SHA-256; a record's retrieval time
      is the snapshot's and its origin `snapshot`. A series
      outside the set raises SnapshotMissingError (a new
      DataError subclass; problems.ROWS `not-in-snapshot`,
      404, exit code 7, with budgets.local_command); a
      snapshot older than twice decision 6's cadence adds the
      `stale_snapshot` warning (cache.policy.NOTE_WARNINGS).
      Without PYECONOMICS_SNAPSHOT_DIR, hosted mode keeps
      Phase 4's per-request fetch (tests, self-hosting).
    </requirement>

    <requirement>
      Deploy: the image gains the job's entry point (no new
      dependency); deploy-staging.yml updates the job to the
      new image digest before deploying the API, mounts the
      bucket read-only into the service at /snapshots with
      PYECONOMICS_SNAPSHOT_DIR, keeps the API's verification,
      and adds one: a hosted-safe series through the edge
      reports a retrieval time from the newest snapshot.
    </requirement>

    <requirement>
      Tests: tests/data/snapshots/ (the set; a writer run
      over scripted providers into a temporary directory;
      the reader's round trip, refusal, staleness, bad
      object and partial-failure paths; LeakCheck over
      objects and logs; the layering test's new IO modules);
      the problem's walking-test row; a hosted-mode bound
      run over snapshots whose manifest records the
      snapshot's retrieval times; tests/parity's bound runs
      unchanged.
    </requirement>

    <requirement>
      docs/operations/staging.md: the snapshot topology, the
      schedule, running the job by hand, a silent job
      (ROADMAP §5 runbook), purging a source's snapshots
      when its terms stop allowing them (rule 7), restoring
      a previous run from object versioning, rotating the
      key secrets and the heartbeat URL, and the job's
      measured runtime against the free tier.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); YAML starts with `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 8 acceptance criteria

- The snapshot set is computed from the catalog and the registry, holds
  every hosted-safe candidate of every bound model's default profile, and
  holds nothing from FRED, an aggregator, a library-only source or a
  storage-forbidden series, under tests.
- The writer writes per-provider objects and `current.json` last, keeps a
  failed provider's previous object, reports to the heartbeat, and never
  writes a key; the reader verifies each object, serves hosted series and
  bound runs from snapshots, refuses a series outside the set with the
  `not-in-snapshot` problem, and warns on a stale snapshot.
- Without `PYECONOMICS_SNAPSHOT_DIR`, hosted mode behaves as in Phase 4;
  every earlier data, surface and parity suite passes.
- The staging bucket, job, identities, secrets and daily schedule exist as
  recorded, least-privilege, and the runbook covers them with the measured
  runtime.
- **Deployed & verified:** the `deploy-staging.yml` run on this step's
  merge commit updated the job and the API; an executed job run succeeded
  and its `current.json` lists the set; through the edge with the service
  token, a hosted-safe series (Treasury's par curve) answers 200 with a
  retrieval time from that run, a series outside the set answers 404
  `not-in-snapshot`, and a bound model's default-profile run records the
  snapshot's retrieval times; the next scheduled run succeeded.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the identities are least-privilege, the
  bucket is private, keys and the heartbeat URL live only in Secret
  Manager, and LeakCheck proves no key reaches an object or a log.

---

## Step 9 — Data Explorer and User Data

**Status:** Not started

> **Goal:** Let visitors find, transform, chart and download the series the
> models read, and run library-only models on their own data, without any
> file leaving the browser (ADR-0013 decision 11). Add `/data/`: an island
> that searches the concept catalog, shows each concept's unit, frequency,
> sources, licence classes and hosted availability, reads a series through
> `GET /v1/series/{target}`, charts it with the source's attribution and
> as-of date drawn on the chart, offers the catalog's own transforms, and
> downloads through `?format=` so every file carries its attribution; link
> each concept to the models that bind it. Make transforms a data-layer
> option every surface shares: `data.get(..., transform=)` validated by
> `core.transforms`, `pyeconomics data get --transform`, `?transform=` on the
> series route and a `transform` argument on MCP's `get_series`. On model
> pages, add "use my own data": CSV and XLSX files parsed in the browser
> (in a worker, with size limits), mapped to the model's array fields and
> sent only as the run's values; the models whose data is library-only
> (Ken French, Shiller, AQR and the rest) say so and point to the local
> app. Prove the privacy promise with a network-log test and a code check
> that the server keeps no body. Parent: ROADMAP §4 5.4; §5 "Data
> licensing policy" rules 2, 3 and 5 and "Data classification" (user
> uploads); ADR-0011; ADR-0012 decisions 9, 12 and 13; ADR-0013 decisions 6
> and 11.

**Branch:** `feature/phase05-step9-data-explorer`

**Deploys:** the staging API and site through `deploy-staging.yml` (the
transform option on the API first, then the explorer); production receives
both with Step 17's release candidate.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | High               | High               | XHigh              |
|               | AA       | 50.2               | 52.6               | 56                 |
|               | Price    | $2.18/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | XHigh              | High               | High               |
|               | AA       | 51.9               | 53.6               | 52.6               |
|               | Price    | $3.56/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | XHigh              | XHigh              |
|               | AA       | not measured       | 51                 | 52.4               |
|               | Price    | $2.40/1M*          | $4.00/1M           | $16.36/1M          |

Ranked for coding, high complexity. Price: list $ per 1M tokens (3 in : 1 out) ×
the tokens the model uses at that level; * token use not yet measured, a typical
model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY: an explorer island, a contract
addition to the data layer surfaced on four generated surfaces, and an
in-browser file pipeline. Complexity is High — user files are untrusted
input, the explorer must never replicate a provider's own product or show
a source hosted mode may not serve, and the transform option touches a
Phase 3 contract under the contract-change rule — but the step is not
novel. The ladder's Balanced column runs: Gemini 4 Argon on Antigravity at
Effort High with Thinking on (Google AI Ultra; AA Intelligence Index
52.6), Runner-up Opus 5.5 on Claude Code at Effort High, Backup GPT-6.1
Sol on Codex at Intelligence XHigh. Cost runs GPT-6.1 Sol at Intelligence
High (50.2) and Quality Opus 5.5 at Effort XHigh (56.0). New conversation
per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step9-data-explorer`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 9 is
       complete. You can now move
       on to Step 10." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 10.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - User files stay in the browser: they are parsed in a
      worker, capped (file size and each field's
      max_length), read as values only (formulas, links and
      macros ignored), and only the mapped numbers travel,
      in the run's body. A Playwright test records every
      request during an upload and a run and finds exactly
      one, the same-origin POST, holding no file bytes or
      file name; a static test proves the server logs no
      request body and answers POST runs `no-store`.
    - The XLSX and CSV parsers are permissive, maintained
      and audited (npm audit, the licence check); the
      unmaintained npm `xlsx` package is not used.
    - Transforms are parsed by core.transforms'
      check_transform (bounded names, arguments and
      periods); text a caller sends never becomes code, and
      a bad transform is a 422 problem.
    - The explorer offers only concepts hosted mode can
      serve on the hosted site and draws every chart with
      its source's attribution and as-of date; FRED and
      every library-only source appear only in local mode.
  </security>

  <context>
    pyeconomics. Phase 5. Step 9: the data explorer and
    user data.

    Current state (post-Phase-5 Step 8):

    - Staging's hosted series and bound runs read
      snapshots; a series outside the snapshot set answers
      404 not-in-snapshot. The site data export writes
      concepts.json with each concept's candidates and
      hosted availability, computed from the snapshot set.
    - GET /v1/series/{target} takes start, end, as_of,
      vintage and provider, and ?format= (json, csv, xlsx,
      parquet, arrow); the CLI's `data get` and MCP's
      `get_series` take the same options (server/work.py
      SERIES_OPTIONS, mcp/server.py). data.get has no
      transform option; core/transforms.py defines thirteen
      named transforms (pct_change, yoy, diff, lag, log,
      changes_only, ratio, add, convert, align_to, asof,
      period, window) parsed from text by check_transform.
    - Calculators post inputs to the run route; array
      fields are bounded by max_length; library-only models
      (asset_pricing.factor_regression over Ken French,
      equity.cape over Shiller, and others) bind sources
      hosted mode refuses.
    - ROADMAP §5 rule 5: the explorer feeds models and never
      replicates a provider's own product (FRED's API terms
      forbid replicating its essential user experience).

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 6, 8
      and 11) and ADR-0011 (transforms, decision 15).
    - src/pyeconomics/data/api.py, core/transforms.py,
      data/catalog/transforms.py and their tests.
    - src/pyeconomics/cli/data_commands.py,
      server/app.py, work.py, formats.py and
      mcp/server.py, tools.py.
    - tests/parity/ and the snapshot suites under
      tests/mcp/ and tests/server/ (openapi, tools/list).
    - web/ (the calculator island, the export).
  </context>

  <goal>
    /data/ finds, transforms, charts and downloads every
    series hosted mode serves, with attribution on every
    chart and file; transforms behave the same on every
    surface; library-only models run on the user's own
    files, which never leave the browser except as run
    values.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Transforms (contract-change rule, additive):
      `data.get(..., transform: str | None = None)` applies
      a single-series transform from core.transforms after
      resolution (pct_change, yoy, diff, lag, log, convert;
      others refused with a clear InputError), recording it
      in the result's DataSource; the CLI's `data get
      --transform`, the series route's `?transform=` and
      MCP get_series's `transform` argument pass it through
      generated code. The OpenAPI and tools/list snapshots
      are updated after review; every provider, concept and
      binding test stays green; the carry-over checklist
      records the Phase 3 contract addition.
    </requirement>

    <requirement>
      /data/: a concept search over concepts.json (title,
      id, unit, frequency, topic), a concept panel (unit,
      frequency, seasonal adjustment, candidates with
      licence class and terms page, hosted availability, the
      models that bind it, linked), a date range and a
      transform picker, a chart (the Plotly basic bundle as
      in Step 6) with the attribution and as-of date as an
      annotation, and downloads through ?format=. In hosted
      mode, concepts outside the snapshot set show the local
      command instead of a fetch; in local mode (Step 10)
      every concept is offered.
    </requirement>

    <requirement>
      User data on model pages: for each array field, "use
      my own data" accepts a CSV or XLSX file, parses it in
      a Web Worker (worker-src as decision 9 allows) with
      the parsers decision 11 names, caps the file at 5 MB
      and the rows at the field's max_length, previews the
      first rows, lets the user map columns to fields, and
      writes the values into the form; a template CSV per
      model is downloadable. Library-only models say which
      source the hosted site may not serve and give the
      local app's command.
    </requirement>

    <requirement>
      The privacy proof: tests/web (Playwright) uploads a
      CSV and an XLSX that hold formulas, an external link
      and a long column, runs the model, and asserts the
      network log (one same-origin POST, values only, no
      third-party request); tests/server asserts that run
      handlers and the request log never read or write a
      body and that POST runs answer `no-store`.
    </requirement>

    <requirement>
      Tests: transform parity — one concept through the
      Python API, the CLI, the REST route and MCP returns
      the same bytes with and without a transform; the
      explorer's search and availability logic (Vitest); a
      download carries its attribution; axe finds no WCAG
      2.2 AA violation on /data/ with a chart; /data/ meets
      decision 19's Lighthouse scores.
    </requirement>

    <requirement>
      Filepath comment: every new file gets the
      repo-relative path as the first line where its type
      allows a comment; a new Python file gets the
      three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 9 acceptance criteria

- `data.get` takes a single-series `transform`, and the CLI, the series
  route and MCP's `get_series` pass it through generated code; one concept
  returns the same bytes on all four surfaces with and without a
  transform; the API and tool snapshots are updated after review; every
  Phase 3 suite stays green.
- `/data/` searches the catalog, shows sources, licence classes and
  availability, charts a series with its attribution and as-of date, and
  downloads files carrying the attribution; hosted mode offers only the
  snapshot set.
- Model pages accept CSV and XLSX files parsed in a worker, capped and
  mapped to array fields; library-only models point to the local app.
- The network-log test and the server's no-body test pass.
- axe finds no WCAG 2.2 AA violation on `/data/`, and it meets decision
  19's Lighthouse scores in CI.
- **Deployed & verified:** with the service token, staging's `/v1/series/`
  for a hosted-safe concept with `?transform=yoy` answers 200 with the
  transform recorded, `/data/` charts the same concept with its
  attribution, and a run fed from an uploaded CSV through the staging site
  returns its result, with the browser's network log holding only the
  same-origin POST.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean for the new parsers — user files never
  leave the browser except as run values, transforms are parsed and
  bounded, and the explorer never shows a source hosted mode may not serve.

---

## Step 10 — Local App and the pyeconomics-app Wheel

**Status:** Not started

> **Goal:** Serve the same site on the user's machine, with every source
> the user can access, and release it in lockstep with the library. Make
> the repository a uv workspace with `packages/pyeconomics-app/` as its
> second member (ADR-0002, ADR-0013 decision 16): a pure-Python
> `pyeconomics_app` package whose wheel carries the built site under
> `pyeconomics_app/site/` and nothing else, at the same version as
> `pyeconomics`; add the `[app]` extra pinning `pyeconomics-app==<version>`,
> outside `[all]`, with a test that holds the two versions equal; teach
> `pyeconomics serve` to mount the site at `/` when the package is
> installed — after the API's own routes, with the same security headers
> as `_headers` (read from the packaged file, one source of truth), the
> loopback guard unchanged, and a one-line hint when it is not installed;
> let the site's local mode light up what only a local server can do —
> live data for library-only bindings with the user's keys and the
> explorer's whole catalog — from `/version`'s `mode`; and change
> `release.yml`, `release-smoke.yml` and the package checks to build,
> allowlist, check, publish and smoke both distributions through Trusted
> Publishing, with the maintainer creating `pyeconomics-app`'s pending
> publishers on TestPyPI and PyPI at kickoff. Parent: ROADMAP §4 5.5; §5
> "Deployable surfaces" (the PyPI row); ADR-0002; ADR-0006; ADR-0012
> decision 11.

**Branch:** `feature/phase05-step10-local-app`

**Deploys:** nothing beyond merge — the release workflow learns to publish
two distributions, but no tag is pushed; Step 17's TestPyPI rehearsal is
`pyeconomics-app`'s first upload, and its PyPI release the second. The
staging site redeploys as on every merge.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | High               | High               | XHigh              |
|               | AA       | 50.2               | 52.6               | 56                 |
|               | Price    | $2.18/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | XHigh              | High               | High               |
|               | AA       | 51.9               | 53.6               | 52.6               |
|               | Price    | $3.56/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | XHigh              | XHigh              |
|               | AA       | not measured       | 51                 | 52.4               |
|               | Price    | $2.40/1M*          | $4.00/1M           | $16.36/1M          |

Ranked for coding, high complexity. Price: list $ per 1M tokens (3 in : 1 out) ×
the tokens the model uses at that level; * token use not yet measured, a typical
model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: a second
distribution in a uv workspace, a static mount and headers middleware in
the local server, mode-aware site features, and a release pipeline that
must publish two projects through one OIDC exchange without ever letting
their versions drift. Complexity is High — packaging and the release
workflow are where a mistake becomes an irreversible upload — but the step
is not novel. The ladder's Balanced column runs: Gemini 4 Argon on
Antigravity at Effort High with Thinking on (Google AI Ultra; AA
Intelligence Index 52.6), Runner-up Opus 5.5 on Claude Code at Effort
High, Backup GPT-6.1 Sol on Codex at Intelligence XHigh. Cost runs GPT-6.1
Sol at Intelligence High (50.2) and Quality Opus 5.5 at Effort XHigh
(56.0). New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step10-local-app`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 10 is
       complete. You can now move
       on to Step 11." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 11.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The local server's guard is unchanged: a non-loopback
      bind needs --allow-remote, and a request addressed to a
      non-loopback name is refused, so a page that rebinds
      its domain to 127.0.0.1 cannot read the user's data;
      a test proves both with the site mounted.
    - The site is served with the same CSP and headers as
      production, from the packaged _headers file, and with
      `X-Robots-Tag: noindex`; the static mount never serves
      a path outside the package (no symlink follow, no `..`).
    - The app wheel holds static files only: a dist allowlist
      for it refuses any executable, archive, source map that
      names a local path, or file outside
      pyeconomics_app/site/; no key, `.env` or build cache
      reaches it.
    - One OIDC exchange mints a token for both projects
      because both name the same trusted publisher (workflow,
      environment); no API token is created or stored, and
      `id-token: write` stays on the two publish jobs only
      (Phase 1 check 36).
  </security>

  <context>
    pyeconomics. Phase 5. Step 10: the local app and the
    pyeconomics-app wheel.

    Current state (post-Phase-5 Step 9):

    - The site in web/ is complete for the launch: model
      pages, calculators, navigation, search, the coverage
      matrix and the data explorer, deployed to staging on
      every merge. It reads the API on its own origin and
      learns the mode from GET /version.
    - pyeconomics serve (cli/serve_command.py) runs
      create_app(mode="local") on 127.0.0.1:8000 with the
      loopback guard; the local app serves /docs and /redoc
      (Swagger UI and ReDoc from a CDN), /openapi.json, /v1,
      /mcp, /healthz and /version.
    - ADR-0002: the built site ships in its own
      pyeconomics-app wheel behind [app], versioned and
      released in lockstep through the same workflow; [app]
      and [bloomberg] appear only when their packages exist;
      [all] excludes [app].
    - release.yml builds one distribution and checks it with
      scripts/checks/dist_contents.py (the main wheel admits
      only .py files); release-smoke.yml installs it.
      server.json, CITATION.cff and pyproject.toml move
      together (tests/mcp/test_mcp_registry_entry.py,
      tests/unit/test_version.py).
    - PyPI's trusted publishing mints a token for every
      project that names the exchanging publisher; a new
      project is created on its first upload through a
      pending publisher the owner registers.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 2, 9,
      16 and 18), ADR-0002 and ADR-0006.
    - pyproject.toml, uv.lock's header, and
      scripts/checks/dist_contents.py.
    - src/pyeconomics/cli/serve_command.py and
      src/pyeconomics/server/app.py, settings.py.
    - .github/workflows/release.yml, release-smoke.yml and
      ci.yml (package job).
    - web/ (the build, _headers, the mode detection).
    - scripts/verify-phase01.sh checks 21 and 36,
      verify-phase02.sh and verify-phase04.sh's package
      checks.
  </context>

  <goal>
    `pip install "pyeconomics[app]"` then `pyeconomics serve`
    shows the same site as production at
    http://127.0.0.1:8000 with the user's local sources
    live; both distributions build, check, publish and smoke
    together at one version; nothing about the plain install
    or the loopback guard changes.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer: create
      the pending trusted publishers for `pyeconomics-app` on
      TestPyPI and PyPI with this repository, workflow
      `release.yml` and environments `testpypi` and `pypi`
      (the same as `pyeconomics`'s), and approve the merge
      when the checks are green. Record what was done, never
      a token, in the PR body.
    </requirement>

    <requirement>
      Workspace: `[tool.uv.workspace] members =
      ["packages/pyeconomics-app"]`; the member's
      pyproject.toml (name, the same version, Apache-2.0,
      the same `requires-python`, `uv_build`, no runtime
      dependency) and `src/pyeconomics_app/__init__.py`
      exposing `site_path()` (an importlib.resources
      Traversable) and nothing else. The built site is copied
      into `src/pyeconomics_app/site/` by
      `scripts/web/package_site.py` at build time and is
      git-ignored; a wheel built without it fails the
      allowlist. `uv lock --no-config` and `uv export
      --no-config` stay clean.
    </requirement>

    <requirement>
      The `[app]` extra: `pyeconomics-app==<version>` in
      [project.optional-dependencies], not in [all];
      tests/unit/test_app_version.py holds the extra's pin,
      the member's version, pyproject.toml, CITATION.cff and
      server.json equal, so a `uv version` bump that forgets
      one fails.
    </requirement>

    <requirement>
      `pyeconomics serve`: when `pyeconomics_app` imports,
      mount the site at `/` after every API route (so /v1,
      /mcp, /docs, /redoc, /openapi.json, /healthz and
      /version keep precedence), with directory index pages,
      the 404 page for unknown paths, and a middleware that
      applies the packaged _headers rules plus `X-Robots-Tag:
      noindex` to the site's responses; without it, serve
      behaves as today and logs one line suggesting
      `pip install "pyeconomics[app]"`. The site's own
      /version.json reports the packaged build.
    </requirement>

    <requirement>
      Local mode in the site: with `"mode": "local"` from
      /version, a bound model's calculator offers live data
      for every profile (library-only sources included, with
      the user's own keys, and the source's notices shown),
      and the explorer lists every concept rather than the
      snapshot set; hosted mode keeps decision 11's limits.
      No local-only feature ever runs against the hosted
      API.
    </requirement>

    <requirement>
      Release (decision 18): release.yml's build job builds
      the site once (`npm ci`, the site data export, `npm run
      build`), packages it, builds both distributions, runs
      each allowlist (scripts/checks/dist_contents.py for the
      main wheel, unchanged; scripts/checks/app_contents.py
      for the app wheel) and `twine check --strict`, and
      uploads both; each publish job uploads both through
      one Trusted Publishing exchange with attestations.
      release-smoke.yml installs `pyeconomics[app]` from the
      index under test, starts `pyeconomics serve` on a free
      port and checks `/`, a model page and a run. The
      package job in ci.yml does the same from the built
      wheels on every PR.
    </requirement>

    <requirement>
      Tests: tests/server/test_site_mount.py (route
      precedence, headers on site responses, noindex, the 404
      page, no path escape, the guard with the site mounted,
      the hint without the package), the version test above,
      and a Playwright run in the web job against a local
      `pyeconomics serve` with the packaged site: a page, a
      calculator run and a local-mode-only control.
    </requirement>

    <requirement>
      Cross-phase verification rule: Phase 1 check 21 (no
      `cfa` names; [app] has none), check 36 (id-token on the
      two publish jobs: unchanged) and the package checks in
      verify-phase02.sh and verify-phase04.sh (one wheel and
      one sdist) are narrowed only where they count
      distributions, to "the pyeconomics wheel and sdist pass
      dist_contents.py, and any other wheel is
      pyeconomics-app passing app_contents.py", each with an
      addendum line in that phase's roadmap.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); TOML and YAML start with
      `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 10 acceptance criteria

- The repository is a uv workspace whose second member builds
  `pyeconomics-app` with the site under `pyeconomics_app/site/` and
  nothing else; its allowlist refuses anything outside it.
- `[app]` pins `pyeconomics-app` to the package's version, stays out of
  `[all]`, and a test holds every version field equal.
- With `[app]` installed, `pyeconomics serve` serves the site at `/` with
  the production headers and `noindex`, keeps every API route's
  precedence and the loopback guard, and runs a calculator end to end in
  Playwright; without it, it behaves as before and logs its hint.
- The site's local mode offers live library-only data and the whole
  catalog; hosted mode is unchanged.
- `release.yml` builds, allowlists, checks and publishes both
  distributions through one Trusted Publishing exchange with
  attestations; `release-smoke.yml` and the package job install
  `pyeconomics[app]` and smoke `serve`; the pending publishers exist on
  TestPyPI and PyPI.
- The narrowed package checks carry their addendum lines, and
  `verify-phase01.sh` to `verify-phase04.sh --fast` pass.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, actionlint and zizmor clean on the
  release workflows — the loopback guard holds with the site mounted, the
  app wheel holds static files only, and no publishing token exists.

---

## Step 11 — Documentation: Tutorials, How-To Guides and Migration

**Status:** Not started

> **Goal:** Finish the 1.0 documentation people learn from. Add an ordered
> tutorial track in `docs/tutorials/` — install, the first model (which
> exists), data and keys, the command line, the REST API and the local app,
> and MCP (stdio and the hosted endpoint) — that teaches by doing, while the
> existing guide pages stay as references; add how-to guides in
> `docs/how-to/` for getting outputs into pandas, into R and into Excel
> (the XLSX export and Power Query over a REST download), and for using
> pyeconomics inside xlwings Lite, scoped to what Pyodide supports today
> (data-free models and values from the sheet; issues #114 and #116 keep
> live data in the browser out); add syllabus study paths generated from
> `syllabi/` (ordered model pages per level and topic); write the 0.2.x to
> 1.0 migration guide, mapping every public 0.2.x function to its 1.0
> equivalent with numbers that match the characterization fixtures; link
> every documentation model page to its web page and back; and run every
> example under Sybil or MyST-NB with warnings as errors. Parent: ROADMAP
> §4 5.6 (first and second bullets); ADR-0007; ADR-0013 decision 12.

**Branch:** `feature/phase05-step11-docs-guides`

**Deploys:** the Read the Docs `main` build (the 1.0 preview) — this merge
rebuilds it with the new pages; `stable` moves to 1.0 only at Step 19's
cutover.

|               |          | Cost                 | Balanced           | Quality            |
| ------------- | -------- | -------------------- | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6 Luna**       | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex                | Antigravity        | Claude Code        |
|               | Level    | XHigh                | High               | XHigh              |
|               | AA       | 34.6                 | 52.6               | 56                 |
|               | Price    | $0.19/1M             | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Haiku 5.5**        | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code          | Claude Code        | Antigravity        |
|               | Level    | High                 | High               | High               |
|               | AA       | 37.8                 | 53.6               | 52.6               |
|               | Price    | $0.20/1M*            | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    | **GPT-6.1 Sol**    |
|               | Platform | Antigravity          | Codex              | Codex              |
|               | Level    | Low                  | High               | XHigh              |
|               | AA       | 33.5                 | 50.2               | 51                 |
|               | Price    | $0.65/1M             | $2.18/1M           | $4.00/1M           |

Ranked for knowledge, medium complexity. Price: list $ per 1M tokens (3 in : 1
out) × the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Knowledge is PRIMARY and coding SECONDARY: tutorials
and guides that must be correct about economics, finance and the library's
behaviour, written for newcomers, with every example executed; the
migration guide needs the 0.2.x API read from `legacy/0.2.x`. Complexity
is Medium — the surfaces exist and the format is set — and the step is not
novel. The ladder's Balanced column runs: Gemini 4 Argon on Antigravity at
Effort High with Thinking on (Google AI Ultra; AA Intelligence Index 52.6),
Runner-up Opus 5.5 on Claude Code at Effort High, Backup GPT-6.1 Sol on
Codex at Intelligence High. Cost runs GPT-6 Luna on Codex at Intelligence
XHigh (34.6) and Quality Opus 5.5 at Effort XHigh (56.0). New conversation
per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step11-docs-guides`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 11 is
       complete. You can now move
       on to Step 12." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 12.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - No example prints, stores or embeds a key: the data
      and keys tutorial uses `pyeconomics keys set` with its
      hidden prompt and shows `keys list`'s source column,
      never a value; documentation examples that need a key
      run against recorded or synthetic responses, and the
      build's socket guard stays on.
    - Examples that read data name each source's licence
      class and carry its notices, and none shows FRED data
      reaching an LLM or the hosted service.
    - No page copies curriculum text, a learning outcome, a
      reading or an example; the study paths list our own
      pages only.
  </security>

  <context>
    pyeconomics. Phase 5. Step 11: documentation tutorials,
    how-to guides and the migration guide.

    Current state (post-Phase-5 Step 10):

    - Read the Docs builds main as the 1.0 preview with
      warnings as errors; stable and latest serve 0.2.6
      until Step 19. docs/ holds installation, quickstart,
      tutorials/first-model.md, the CLI, REST API, MCP,
      exports and AI guides, the data layer guides, and the
      generated model, provider, concept and problem
      reference. Sybil runs Markdown examples; MyST-NB runs
      notebooks; an audit hook blocks non-loopback sockets.
    - The web site has a page per model at
      /models/<domain>/<name>/ (ADR-0013 decision 2);
      syllabi/ holds the 2027 seed; pyeconomics[app] serves
      the site locally.
    - The core imports in Pyodide (ci.yml's pyodide job);
      HttpTransport and the SQLite cache have not run under
      Pyodide (#114, #116), so live data in the browser is
      unsupported.
    - The 0.2.x API lives on legacy/0.2.x (archived at
      v0.2.6); tests/fixtures/legacy/ holds its byte-exact
      characterization fixtures (never edit them).

    Files to read (every file before drafting):
    - docs/index.md, installation.md, quickstart.md,
      tutorials/first-model.md, cli.md, api.md, mcp.md,
      exports.md, data/index.md, data/keys.md.
    - docs/conf.py and docs/conftest.py (exclusions, Sybil).
    - The 0.2.x public API: `MSYS_NO_PATHCONV=1 git show
      legacy/0.2.x:<path>` for its modules, README and docs.
    - tests/fixtures/legacy/ (names only; read, never edit).
    - syllabi/ and scripts/web/syllabi.py.
    - docs/adr/0013-web-app-and-launch.md (decisions 2, 12
      and 16) and ADR-0007.
  </context>

  <goal>
    A newcomer can go from install to a model, data, the
    command line, the API, the local app and MCP by
    following one track; practitioners find recipes for
    pandas, R, Excel and xlwings Lite; a 0.2.x user can move
    to 1.0 with a guide whose numbers match the old outputs;
    study paths and cross-links tie the docs to the site.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Tutorials (docs/tutorials/, an ordered toctree):
      install (pip, uv, pipx; Python 3.12+; extras), first
      model (exists; update its links), data and keys (a
      keyless hosted-safe series; setting a key with the
      hidden prompt; licence classes; the cache; offline),
      the command line (run, describe, bind with --as-of,
      formats, --out, exit codes), the REST API and the
      local app (`pyeconomics serve`, a POST run, a GET run
      with ?inputs=, ?format=csv, the site at /), and MCP
      (stdio through uvx with a client config, the tools,
      and the hosted endpoint at https://pyeconomics.dev/mcp
      once Step 19 opens it). Each runs under Sybil or
      MyST-NB offline; the hosted-endpoint parts are text
      fences the tests do not run.
    </requirement>

    <requirement>
      How-to guides (docs/how-to/): outputs into pandas
      (to_pandas, the Parquet pipe from the CLI), into R
      (arrow::read_parquet on an export; jsonlite on a REST
      download), into Excel (the XLSX export and its
      manifest sheet; Power Query over a REST CSV download),
      and pyeconomics inside xlwings Lite (requirements.txt
      naming the core wheel; data-free models and values
      from the sheet; a plain statement that live data needs
      a local install until #114 and #116 close). R and
      Excel examples are text fences; the Python halves run.
    </requirement>

    <requirement>
      Study paths: a generated page per syllabus level
      (docs/_ext extension over scripts/web/syllabi.py) that
      lists, per topic, the documentation pages and the web
      pages of the models the seed maps to it, with the mark
      used as an adjective with ® on first use and the
      non-affiliation notice; no curriculum wording.
    </requirement>

    <requirement>
      Migration guide (docs/migration.md): what changed and
      why (registry, data layer, real-time vintages, the
      manifest, decimals for rates, the licence classes); a
      table from each public 0.2.x function, class and
      option to its 1.0 equivalent (or its removal and the
      reason); worked examples of the four monetary-policy
      rules whose numbers equal the characterization
      fixtures, held there by a test that reads the fixtures
      (never edits them); and the end-of-life date of 0.2.x
      at 1.0.0 (ADR-0003).
    </requirement>

    <requirement>
      Cross-links: each docs model page links its web page,
      and each web model page already links its docs page
      (Step 5); a test holds the two sets equal. Update
      docs/index.md's navigation for the tutorials, how-tos,
      study paths and migration guide.
    </requirement>

    <requirement>
      The docs build passes with warnings as errors, Sybil
      collects every new Markdown example, and the docs CI
      job stays inside its time limit; any notebook that
      needs data uses recorded responses or the stand-in
      world under PYECONOMICS_CACHE_DIR set by the build.
    </requirement>

    <requirement>
      Filepath comment: Markdown pages follow the sibling
      docs' conventions; a new Python file (an extension)
      gets the three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 11 acceptance criteria

- `docs/tutorials/` holds the six-part track, `docs/how-to/` the four
  guides, and `docs/migration.md` the guide whose rule examples equal the
  characterization fixtures under a test.
- Study paths are generated from `syllabi/` per level, with the mark as an
  adjective and the notice, and no curriculum wording.
- Every documentation model page links its web page and the reverse, under
  a test.
- The docs build passes with warnings as errors, and every new Python
  example runs under Sybil or MyST-NB offline in CI.
- **Deployed & verified:** the Read the Docs build for this step's merge
  SHA succeeded on `main`, and `/en/main/tutorials/`, a how-to page,
  `/en/main/migration.html` and a study-path page answer 200 (fetched with
  a non-default User-Agent); `stable` still serves 0.2.6.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — no example shows a key, data examples
  carry their notices, and no page copies curriculum content.

---

## Step 12 — Documentation: Gallery, In-Browser Examples and Finance Tutorials

**Status:** Not started

> **Goal:** Add the documentation that teaches through running code.
> Install sphinx-gallery (ADR-0007) and add `docs/examples/`, a gallery of
> short scripts — at least one per populated domain — executed during the
> documentation build, offline; add in-browser examples built with marimo's
> WebAssembly export (`marimo export html-wasm`), each loading the
> pyeconomics core from PyPI into Pyodide through micropip and running
> data-free models, linked from the documentation and checked in CI by a
> browser that waits for a result; and write the Python-for-finance
> tutorials ROADMAP §4 5.6 asks for — pandas with pyeconomics results,
> return statistics, Monte Carlo simulation and portfolio mathematics — in
> our own words, through pyeconomics, citing each method's originators and
> copying no curriculum or Practical Skills Module content. Parent: ROADMAP
> §4 5.6 (second and third bullets); §5 "CFA Institute marks and content";
> ADR-0007.

**Branch:** `feature/phase05-step12-docs-learning`

**Deploys:** the Read the Docs `main` build — this merge rebuilds it with
the gallery, the in-browser examples and the tutorials; `stable` moves at
Step 19.

|               |          | Cost                 | Balanced           | Quality            |
| ------------- | -------- | -------------------- | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6 Luna**       | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex                | Antigravity        | Claude Code        |
|               | Level    | XHigh                | High               | XHigh              |
|               | AA       | 34.6                 | 52.6               | 56                 |
|               | Price    | $0.19/1M             | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Haiku 5.5**        | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code          | Claude Code        | Antigravity        |
|               | Level    | High                 | High               | High               |
|               | AA       | 37.8                 | 53.6               | 52.6               |
|               | Price    | $0.20/1M*            | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    | **GPT-6.1 Sol**    |
|               | Platform | Antigravity          | Codex              | Codex              |
|               | Level    | Low                  | High               | XHigh              |
|               | AA       | 33.5                 | 50.2               | 51                 |
|               | Price    | $0.65/1M             | $2.18/1M           | $4.00/1M           |

Ranked for knowledge, medium complexity. Price: list $ per 1M tokens (3 in : 1
out) × the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Knowledge is PRIMARY and coding SECONDARY: finance
tutorials that must be right and original, a gallery of executed scripts,
and in-browser notebooks whose only moving part is Pyodide loading the
core. Complexity is Medium — the core already imports in Pyodide and the
documentation stack is set — and the step is not novel. The ladder's
Balanced column runs: Gemini 4 Argon on Antigravity at Effort High with
Thinking on (Google AI Ultra; AA Intelligence Index 52.6), Runner-up Opus
5.5 on Claude Code at Effort High, Backup GPT-6.1 Sol on Codex at
Intelligence High. Cost runs GPT-6 Luna on Codex at Intelligence XHigh
(34.6) and Quality Opus 5.5 at Effort XHigh (56.0). New conversation per
phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step12-docs-learning`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 12 is
       complete. You can now move
       on to Step 13." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 13.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - In-browser examples run data-free models and values a
      reader types; they fetch nothing but the pinned
      Pyodide runtime and the pinned pyeconomics wheel, hold
      no key and call no data source (live data in Pyodide
      stays out until #114 and #116 close).
    - New documentation dependencies (sphinx-gallery,
      marimo for the export) join the docs group only, with
      `uv add --no-config`, and pass pip-audit; neither
      reaches the runtime closure.
    - The tutorials copy no curriculum text, reading,
      learning outcome, example or Practical Skills Module
      content; each method cites its originators, and the
      mark appears only as an adjective with the notice.
  </security>

  <context>
    pyeconomics. Phase 5. Step 12: the gallery, in-browser
    examples and Python-for-finance tutorials.

    Current state (post-Phase-5 Step 11):

    - The 1.0 documentation has the tutorial track, the
      how-to guides, the study paths and the migration
      guide; the build runs with warnings as errors, MyST-NB
      executes notebooks, Sybil runs Markdown examples, and
      an audit hook blocks non-loopback sockets.
    - ci.yml's pyodide job proves the core wheel imports and
      runs a model in Pyodide; HttpTransport and the cache
      have not run there (#114, #116).
    - Models the tutorials can use, all data-free:
      foundations.returns, risk_statistics, simulation and
      time_value; portfolio.mean_variance and utility;
      performance.return_measurement and risk_adjusted;
      risk.value_at_risk.
    - Facts read on 2026-10-29 (re-check at kickoff):
      sphinx-gallery 0.22.1 (BSD-3-Clause); marimo 0.25.2
      (Apache-2.0), whose `export html-wasm` output runs on
      Pyodide 314 (Python 3.14), installs pure-Python wheels
      from PyPI through micropip, must be served over HTTP,
      and needs cross-origin isolation only for interrupts;
      WebAssembly needs 'wasm-unsafe-eval' where a CSP
      applies.

    Files to read (every file before drafting):
    - docs/conf.py, docs/conftest.py, docs/index.md and the
      tutorial track from Step 11.
    - .github/workflows/ci.yml (the docs and pyodide jobs)
      and .readthedocs.yaml.
    - The cards of the models above (docs/reference/models/).
    - ROADMAP §4 5.6 and §5 "CFA Institute marks and
      content"; ADR-0007.
  </context>

  <goal>
    The documentation has an executed gallery across the
    domains, in-browser examples that run the core in
    Pyodide, and four original finance tutorials, all built
    and checked in CI and live on the `main` preview.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Gallery: sphinx-gallery in docs/conf.py over
      docs/examples/ (one script per populated domain at
      least, each with a title, a short explanation, a model
      run and, where the model has a chart, its figure),
      executed at build time offline; the generated gallery
      directories are git-ignored; the docs job's time limit
      holds.
    </requirement>

    <requirement>
      In-browser examples: docs/wasm/ holds three marimo
      notebooks (time value of money, a bond's price and
      duration, a portfolio's mean-variance frontier), each
      installing the pinned pyeconomics wheel through
      micropip; scripts/docs/export_wasm.py exports them with
      `marimo export html-wasm` into the build's static
      files; each page says it runs entirely in the browser
      and needs no install. A CI job (or the docs job) serves
      the exported files over HTTP and drives each with
      Playwright until its first result renders.
    </requirement>

    <requirement>
      Python-for-finance tutorials (docs/tutorials/finance/,
      MyST-NB notebooks executed at build time): pandas with
      pyeconomics results (to_pandas, exports, joining
      results), return statistics (simple and log returns,
      annualisation, risk statistics), Monte Carlo
      simulation (seeded runs, convergence, the model's
      cost class), and portfolio mathematics (mean-variance,
      utility, risk-adjusted measures), each in our own
      words with the originators cited and no copied
      curriculum content.
    </requirement>

    <requirement>
      Link the gallery, the in-browser examples and the
      finance tutorials from docs/index.md and from the web
      site's documentation links where Step 5 placed them.
    </requirement>

    <requirement>
      Filepath comment: gallery scripts and new Python files
      get the three-line header (CPY001); marimo notebooks
      keep their own header after it.
    </requirement>
  </requirements>
</task>
```

### Step 12 acceptance criteria

- The gallery holds at least one executed script per populated domain and
  builds offline inside the docs job's time limit.
- Three in-browser examples export with marimo, load the pinned core in
  Pyodide and render a result under Playwright in CI.
- Four finance tutorials execute at build time, cite their methods'
  originators, and copy no curriculum content.
- The documentation build passes with warnings as errors, and the new
  dependencies sit in the docs group only and pass pip-audit.
- **Deployed & verified:** the Read the Docs build for this step's merge
  SHA succeeded on `main`; the gallery index, one in-browser example and
  one finance tutorial answer 200 on `/en/main/` (fetched with a
  non-default User-Agent), and the in-browser example renders a result in
  a browser.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the in-browser examples fetch only the
  pinned runtime and wheel, and no page copies curriculum content.

---

## Step 13 — Production Platform

**Status:** Not started

> **Goal:** Stand production up where the launch will run, private until
> the cutover (ADR-0013 decisions 3–7). With the maintainer's approvals
> batched at kickoff, create the Google Cloud project
> `pyeconomics-production` in `us-central1` — Artifact Registry, the
> runtime, deploy, job and scheduler identities (the deploy identity bound
> on the service from the start, #211's lesson), Workload Identity
> Federation bound to this repository's id, the protected `production`
> environment, and `main` or a `v*` tag, so no service-account key ever
> exists; production's own secrets (a new Upstash Redis database, a new
> edge credential, the job's provider keys); the snapshot bucket, job and
> daily schedule from Step 8; the Cloud Run service `pyeconomics-api`
> (minimum 0, maximum 3 instances); a $10 monthly budget with 50/90/100%
> alerts; and in Cloudflare the Worker `pyeconomics-web` on
> `pyeconomics.dev` behind Access until Step 19, `www` and the `.com`,
> `.org` and `.io` redirects prepared but off, HSTS on the zone, the
> managed WAF ruleset, the Worker's edge cache for cacheable GET runs and
> the rate rule covering production's API paths. Add
> `.github/workflows/deploy-production.yml`: on a non-`.dev` `v*` tag (and a
> maintainer-approved dispatch from `main` for this step's bootstrap and
> for redeploys), it checks that staging verified the same commit, then
> deploys data, API and site in that order — the image promoted by digest
> from staging, never rebuilt — verifies each through the edge with
> production's Access service token, and rolls each back on failure (the
> API to its previous revision with latest traffic restored, the site to
> its previous Worker version). Write `docs/operations/production.md`.
> Parent: ROADMAP §4 5.8; §5 "Release & deployment strategy" (promotion,
> staged rollout, rollback), "Security controls by layer" and "Cost
> projection"; ADR-0006; ADR-0012 decisions 19 and 20; ADR-0013 decisions
> 3–7.

**Branch:** `feature/phase05-step13-production`

**Deploys:** production on Google Cloud and Cloudflare, behind Access — the
first deploy is a dispatched `deploy-production.yml` run on this step's
merge commit, approved by the maintainer; from Step 17 a release tag
deploys it. Nothing is public until Step 19 removes the Access
application.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: the longest
provisioning run of the phase — a new cloud project, identities, a
federation, secrets, a bucket, a job, a schedule, a budget, a Worker, an
Access application, zone rules and a protected environment — driven by
commands the step prints for the maintainer, plus a promotion workflow
with staged verification and rollback. Complexity is High and
security-critical: this is the public service's trust boundary and its
budget. It is not novel: it repeats Phase 4's staging pattern with the
findings of #210 and #211 applied. The ladder's Balanced column runs:
Sonnet 5.5 on Claude Code at Effort XHigh (claude.ai Max; AA Intelligence
Index 51.9), Runner-up GPT-6.1 Sol on Codex at Intelligence High, Backup
Gemini 4 Argon on Antigravity at Effort Medium. Cost runs GPT-6.1 Sol at
Intelligence Medium (47.8) and Quality Opus 5.5 at Effort XHigh (56.0).
New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step13-production`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 13 is
       complete. You can now move
       on to Step 14." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 14.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - No service-account key exists: the federation's
      attribute condition names the repository's numeric id,
      the `production` environment and `refs/heads/main` or
      a `refs/tags/v` ref; each identity lists only
      Google-managed keys.
    - Least privilege from the start: the deploy identity
      holds its Cloud Run role on the service and job only,
      writes only production's repository and reads only
      staging's for promotion; the runtime identity reads
      only its secrets and the bucket; nothing holds a
      project-level role it does not need.
    - Production shares no secret with staging: a new edge
      credential, a new Upstash database, its own Access
      service token and Cloudflare API token, each set by a
      command that prompts or pipes, proven by an
      authenticated round-trip, and recorded by name and
      expiry only.
    - The `production` environment requires the maintainer's
      approval and admits only `main` and `v*` refs;
      deploy-production.yml sets permissions {} at the top,
      grants `id-token: write` only to its Google Cloud jobs,
      pins every action by SHA and passes actionlint and
      zizmor; Phase 3 check 78 and Phase 4 check 64 are
      narrowed to admit exactly its secrets from
      `production`.
    - Until the cutover, nothing in production is reachable
      without Access: the site, the API paths and /mcp; the
      origin still refuses any request without the edge
      credential.
  </security>

  <context>
    pyeconomics. Phase 5. Step 13: the production platform.

    Current state (post-Phase-5 Step 12):

    - Staging runs the API, the snapshot job and the site
      (staging.pyeconomics.dev, behind Access) from
      deploy-staging.yml on every merge: job, then API, then
      site, each verified through the edge; the deploy
      restores latest traffic (#210) and its identity holds
      a service-level role (#211). Staging's registry keeps
      only the newest images (cleanup policy).
    - The site's production flavour refuses indexing for a
      pre-release version and allows it for a final one
      (Step 5); web/wrangler.jsonc declares env `production`.
    - pyeconomics-app publishes with pyeconomics from
      release.yml (Step 10); no `v1.0.0rc1*` tag exists.
    - Facts read on 2026-10-29 (re-check at kickoff): the
      Free plan has one rate rule (path-based, by IP), 10
      Single Redirect rules, 10 Cache Rules and 10 Transform
      Rules per zone, the managed WAF ruleset on by default
      and HSTS on any plan; Cloudflare Zero Trust is free for
      50 users; Cloud Scheduler's 3 free jobs are counted per
      billing account (staging uses one); Google publishes no
      default project quota per billing account (staging's
      first account hit its limit), and the console offers a
      quota request.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 3–7
      and 18) and ADR-0012 decisions 19 and 20.
    - .github/workflows/deploy-staging.yml,
      staging-health.yml and release.yml.
    - docs/operations/staging.md, web/wrangler.jsonc and
      tools/node/edge/.
    - scripts/verify-phase03.sh (check 78) and
      scripts/verify-phase04.sh (check 64).
    - Google's Cloud Run, Artifact Registry, Workload
      Identity Federation, Secret Manager, Cloud Storage and
      budget documentation, and Cloudflare's Workers, Access,
      redirect, cache and rate-limiting documentation, read
      at kickoff.
  </context>

  <goal>
    A dispatched or tag-triggered deploy promotes the
    staging-verified image and deploys data, API and site to
    production in order, each verified through the edge and
    rolled back by itself on failure; production runs
    privately behind Access with its own secrets, budget,
    snapshot schedule and rules; the runbooks say how to
    deploy, roll back, rotate and cut over.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      every command and its effect: create the project and
      link billing (request the quota first if the account
      is at its limit); enable the APIs; create the
      repository (a cleanup policy that keeps every image
      tagged `v*`, and the same keep rule added to staging's
      policy), the identities and their bindings, the
      federation pool and provider with the condition above;
      the Upstash database, its URL into `gcloud secrets
      versions add ratelimit-url --data-file=-`; a new edge
      credential piped into Secret Manager and `npx wrangler
      secret put EDGE_CREDENTIAL --env production` without
      display; the job's key secrets; the bucket, job and
      schedule as in Step 8; the budget with its Pub/Sub
      topic, subscription and email recipients; the
      Cloudflare custom domain, Access application (the
      maintainer and the new `pyeconomics-production-ci`
      service token, expiry recorded), HSTS, the
      redirect rules (disabled), the rate rule's coverage,
      and a production-scoped API token; the `production`
      GitHub environment (required reviewer: the
      maintainer; refs `main` and `v*`) with its secrets and
      variables; and approval to merge and to approve the
      first deploy. Record what was done, never a value.
    </requirement>

    <requirement>
      Cloud Run: service `pyeconomics-api` with minimum 0 and
      maximum 3 instances, request-based billing with CPU
      throttling, the gen2 execution environment (for the
      read-only bucket mount at /snapshots), the measured
      memory, concurrency 8, a 60-second request timeout,
      secrets by pinned version, the startup probe on
      /healthz:8080 (Google Frontend reserves /healthz on
      *.run.app), unauthenticated invocations because the
      edge credential is the origin's gate, and previous
      revisions kept.
    </requirement>

    <requirement>
      deploy-production.yml: triggers on `v*` tags whose
      version is not `.devN` and on workflow_dispatch from
      main; one concurrency group that never cancels a
      deploy; every job in the `production` environment.
      Jobs: `check` (the commit is on main, and its
      deploy-staging run succeeded, read with
      GITHUB_TOKEN's actions: read); `data` (copy the
      staging-verified digest into production's registry,
      update the job, execute it, wait, and verify
      `current.json` is from this run); `api` (deploy the
      digest, restore latest traffic, verify through the
      edge with the production service token — /version
      equals the commit, a data-free run equals the wheel's
      bytes, a hosted-safe series answers from the new
      snapshot, a library-only source 403, a direct origin
      request without the credential 403 — and on failure
      route to the previous revision, restore latest on the
      next deploy, and fail); `site` (build the production
      flavour from the commit, deploy with the production
      token, verify /version.json, the headers and the API
      through the host, and on failure roll back the Worker
      version and fail).
    </requirement>

    <requirement>
      Cloudflare: web/wrangler.jsonc's env `production`
      (pyeconomics-web; custom domain pyeconomics.dev;
      ORIGIN_URL production's origin); the shared Worker
      module caches GET runs with the Workers Cache API as
      the origin's Cache-Control allows (decision 7), never
      a POST run or a problem, with worker.test.mjs cases for
      a hit, a miss and a no-store answer; the redirect rules
      for www and the `.com`, `.org` and `.io` zones (301 to
      the same path on pyeconomics.dev) exist but stay off
      until Step 19.
    </requirement>

    <requirement>
      docs/operations/production.md (excluded from the site,
      like staging's): the topology and trust boundary, the
      identities and their exact roles, deploying by tag and
      by dispatch, the promotion gate, rolling back the API
      (and restoring latest traffic), the site (`wrangler
      rollback`) and the data (restoring the previous
      `current.json` from object versioning), the cutover
      (removing Access and enabling the redirects, Step
      19), rotating every production secret and token with
      its expiry, disabling a provider, a cost spike (lower
      the maximum, tighten the rule), and the free-tier and
      budget arithmetic.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      and Phase 4 check 64 to admit deploy-production.yml
      reading only `production` environment secrets, each
      with an addendum line in that phase's roadmap; Phase 1
      check 36 is unchanged (id-token stays on release.yml's
      two publish jobs within release.yml).
    </requirement>

    <requirement>
      Filepath comment: YAML starts with `# <path>`; JSONC
      with `// <path>`; a new Python file gets the three-line
      header.
    </requirement>
  </requirements>
</task>
```

### Step 13 acceptance criteria

- Production exists as recorded: the project, registry, identities with
  only Google-managed keys and service-level roles, the federation
  condition on the repository id, the `production` environment and `main`
  or `v*` refs, its own secrets, the bucket, job and daily schedule, the
  service at minimum 0 and maximum 3, and the $10 budget with its alerts.
- Cloudflare serves `pyeconomics.dev` from `pyeconomics-web` behind Access,
  with HSTS, the managed ruleset, the Worker's GET-run cache and the rate
  rule covering production's API paths; the redirect rules exist, disabled.
- `deploy-production.yml` refuses a commit staging did not verify,
  promotes the digest, and deploys data, API and site in order with
  verification and rollback; Phase 3 check 78 and Phase 4 check 64 are
  narrowed with their addendum lines.
- `docs/operations/production.md` holds the runbooks and the cost
  arithmetic.
- **Deployed & verified:** the dispatched `deploy-production.yml` run on
  this step's merge commit, approved by the maintainer, succeeded in every
  job; with the production service token from the maintainer's keyring,
  `https://pyeconomics.dev/version` and `/version.json` report that SHA, a
  model page answers 200 with its CSP and `X-Robots-Tag: noindex`, a
  data-free run equals the wheel's bytes, a hosted-safe series answers
  from that run's snapshot, and MCP Inspector passes over Streamable HTTP
  at `/mcp` with the Access headers; without the token every path answers
  Access's login.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, actionlint and zizmor clean on
  `deploy-production.yml` — IAM is least-privilege, no key exists, no
  secret is shared with staging, and no value appears in the repository, a
  log or the PR.

---

## Step 14 — Observability and Operations

**Status:** Not started

> **Goal:** Make production observable and prove every alarm fires before
> anyone outside can reach it (ADR-0013 decision 15; ROADMAP §5
> "Operations & observability strategy"). Add error tracking with Sentry —
> the backend through `sentry-sdk` in hosted mode only, scrubbed through
> the error table's scrubber, with no personal data, request body, query
> string or header; the browser through `@sentry/browser` in the islands
> only, with no replay and query strings stripped; add OpenTelemetry
> metrics and sampled traces to Grafana Cloud through the project's own
> middleware — route templates, status classes, route kinds, model ids and
> cost classes, never inputs or addresses — flushed on shutdown because
> Cloud Run throttles the CPU between requests; install both from a
> `hosted` dependency group in the image only, never an extra, so no user's
> install sends telemetry; add Better Stack uptime monitors for the site,
> the version endpoints, the API's health and a small run, heartbeats for
> both snapshot jobs, and the public status page at
> `status.pyeconomics.dev`; add `production-health.yml`, an hourly
> synthetic check through the edge that runs one model per domain and
> downloads a CSV carrying its attribution, opening a `production-health`
> issue on failure; connect the budget's alerts; fire every alarm once with
> a synthetic failure and record each proof; and publish the production
> runbooks with an incident procedure. Parent: ROADMAP §4 5.8 (second
> bullet); §5 "Operations & observability strategy" ("Health signals",
> "Rules", "Runbooks", "Acceptance") and "Security controls by layer"
> (logging); ADR-0013 decision 15.

**Branch:** `feature/phase05-step14-observability`

**Deploys:** staging and production — this merge redeploys staging; a
dispatched, approved `deploy-production.yml` run puts the instrumentation
in production behind Access; the monitors, the status page and the
synthetic check run against both. Their proofs are part of the step.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: four vendor
setups (Sentry, Grafana Cloud, Better Stack and the budget's channels), a
scheduled synthetic check, deliberate alarm injections and runbooks,
around a small amount of instrumentation code that must never carry
personal data. Complexity is High — telemetry is a new path for data to
leave the service, and an alarm nobody has seen fire is noise — and the
step is not novel. The ladder's Balanced column runs: Sonnet 5.5 on Claude
Code at Effort XHigh (claude.ai Max; AA Intelligence Index 51.9),
Runner-up GPT-6.1 Sol on Codex at Intelligence High, Backup Gemini 4 Argon
on Antigravity at Effort Medium. Cost runs GPT-6.1 Sol at Intelligence
Medium (47.8) and Quality Opus 5.5 at Effort XHigh (56.0). New
conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step14-observability`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 14 is
       complete. You can now move
       on to Step 15." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 15.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Telemetry carries no personal data: Sentry is
      initialised without `send_default_pii` and never with
      a `data_collection` dict (which switches to permissive
      defaults that include addresses and bodies); every
      event passes `before_send` through problems.scrub;
      spans and metrics carry route templates, never paths,
      queries, inputs, client addresses or keys. A canary
      test plants a key, an address and an input value in a
      request and finds none in a captured event, span or
      metric.
    - The Sentry DSN, the OTLP authorization header and the
      heartbeat URLs live in Secret Manager (and the browser
      DSN, which is public by design, in the build's
      configuration); none is logged; each is registered with
      redaction.
    - The telemetry libraries (sentry-sdk, opentelemetry-sdk
      and its OTLP HTTP exporter, Apache-2.0 and MIT) join a
      `hosted` dependency group that the image installs from
      uv.lock with hashes, pass the licence allowlist and
      pip-audit, and are never imported by a local server;
      the beta FastAPI instrumentation package is not used.
    - production-health.yml sets permissions {} at the top,
      grants issues: write only to its report job, reads the
      production service token from the `production`
      environment only, and passes actionlint and zizmor;
      Phase 3 check 78 and Phase 4 check 64 are narrowed
      for it.
  </security>

  <context>
    pyeconomics. Phase 5. Step 14: observability and
    operations.

    Current state (post-Phase-5 Step 13):

    - Production runs privately: deploy-production.yml
      (dispatch from main or a v* tag, approved) deploys the
      snapshot job, the API and the site behind Access; the
      budget's 50/90/100% alerts publish to Pub/Sub and
      email. Staging has staging-health.yml (hourly, opening
      issues) and its own budget notification, both proven
      in Phase 4.
    - The server logs one line per request naming its route
      template, and problems as scrubbed records
      (server/logs.py, problems.report); server/work.py runs
      tasks in spawned worker processes.
    - The snapshot writer requests its heartbeat URL on
      completion (Step 8) when one is configured.
    - Facts read on 2026-10-29 (re-check at kickoff):
      Sentry's free Developer plan gives one user, 5,000
      errors and 5 million spans a month with 30-day
      lookback; sentry-sdk 2.73.0 (MIT); @sentry/browser
      11.10.0 (MIT; @sentry/astro needs a Node runtime);
      Grafana Cloud's free tier gives 10,000 metric series
      and 50 GB of traces with 14-day retention through an
      OTLP gateway authenticated by Basic auth;
      opentelemetry-sdk and the OTLP HTTP exporter 1.45.2
      (Apache-2.0); Better Stack's free plan gives 10
      monitors and heartbeats, one status page, 3-minute
      checks and email alerts (whether the status page takes
      a custom domain on the free plan is to be confirmed at
      kickoff).

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 9 and
      15) and ROADMAP §5 "Operations & observability
      strategy" in full.
    - src/pyeconomics/server/ (app.py, logs.py, settings.py,
      work.py, __main__.py), surfaces/problems.py and
      data/redaction.py, data/config.py.
    - Dockerfile, deploy-production.yml, deploy-staging.yml
      and staging-health.yml.
    - docs/operations/production.md and staging.md.
    - tests/surfaces/test_problem_canary.py and
      tests/data/leakcheck.py.
  </context>

  <goal>
    Every runtime surface — the API, the site, both snapshot
    jobs and the budget — has a health signal, an alarm that
    reached the maintainer once on a synthetic failure, and
    a runbook; errors and telemetry reach their vendors with
    no personal data; the status page is public.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer: create
      the Sentry organization and its two projects with an
      alert rule that emails on a new issue; the Grafana
      Cloud stack and an access-policy token limited to
      metrics, logs and traces writes; the Better Stack
      account, its monitors (with the production service
      token's headers until the cutover), heartbeats, status
      page and its DNS record; store the DSN, the OTLP
      header and both heartbeat URLs with `gcloud secrets
      versions add <name> --data-file=-`; confirm the email
      and push channels; and approve the merge and the
      production deploy. Record what was done, never a value.
    </requirement>

    <requirement>
      Backend (server/observability.py, imported only when
      hosted mode starts and its variables are set):
      sentry-sdk initialised with the release (package
      version and git SHA), environment, a low traces sample
      rate, no default personal data and before_send through
      problems.scrub; an OpenTelemetry meter and tracer with
      the OTLP HTTP exporter, recording from the existing
      request middleware and the worker results, flushed on
      SIGTERM; the snapshot job records its run, rows and
      failures. Workers report through the parent's records,
      never their own exporters.
    </requirement>

    <requirement>
      Browser: @sentry/browser initialised in the calculator
      and explorer islands only, `sendDefaultPii: false`, no
      replay or tracing, URLs with query strings removed in
      beforeSend; its ingest origin joins connect-src
      (decision 9); the post-build headers check still
      passes.
    </requirement>

    <requirement>
      Monitors (Better Stack): `/`, `/version.json`,
      `/healthz` and a GET run with a small ?inputs= on
      production (and the staging equivalents if the free
      plan's count allows), each with a keyword; heartbeats
      for the production and staging snapshot jobs at 26
      hours; the status page with the production monitors,
      linked from the site's footer. Until the cutover the
      monitors send the production service token's headers;
      if the free plan cannot send headers, a separate
      Access application covering only the monitored paths
      bypasses Access for the vendor's published probe
      addresses, and Step 19 removes it with the rest.
    </requirement>

    <requirement>
      production-health.yml: hourly and on dispatch (with a
      simulate_failure input); through the edge with the
      production service token until the cutover, without it
      after; /version equals /version.json's SHA, one model
      per populated domain runs and equals the expected
      bytes, and one CSV download carries its attribution; a
      report job opens a `production-health` issue on failure
      and closes older ones.
    </requirement>

    <requirement>
      Alarm proofs, each recorded in
      docs/operations/production.md's alarm table with its
      date, run or event link and the maintainer's
      confirmation that the notification arrived: a Better
      Stack monitor against a path that fails; a heartbeat
      left unpinged by pausing a schedule for one cycle; a
      Sentry test event from production; production-health's
      simulated failure and its issue; a budget notification
      pulled from the subscription. Each injected failure is
      undone, and the newest real run of each is green.
    </requirement>

    <requirement>
      docs/operations/production.md gains the incident
      procedure (status page, triage, rollback, post-incident
      note) and the ROADMAP §5 runbooks applied to
      production: deploy regressed, snapshot job silent,
      secret leaked, upstream down or changed, data terms
      changed, bad release, model error and cost spike, each
      naming its alarm.
    </requirement>

    <requirement>
      Tests: the telemetry canary (no key, address or input
      in any captured event, span or metric), the
      observability module's absence in local mode, and the
      hosted group's installation in the container job's
      smoke.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      and Phase 4 check 64 for production-health.yml's
      `production` secrets, with addendum lines.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header (CPY001); YAML starts with `# <path>`;
      TypeScript with `// <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 14 acceptance criteria

- Sentry receives scrubbed errors from production's API and islands, and
  Grafana Cloud receives its metrics and sampled traces, with no personal
  data, input, address or key, proven by the canary test; the libraries
  come from the `hosted` group and never load in local mode.
- Better Stack monitors the site, both version endpoints, the API's
  health and a run; heartbeats watch both snapshot jobs; the status page
  is live and linked from the footer.
- `production-health.yml` runs hourly and is green on `main`.
- Every alarm — a monitor, a heartbeat, Sentry, the synthetic check and
  the budget — fired once on a synthetic failure, reached the maintainer,
  and is recorded with its proof; every injected failure was undone.
- `docs/operations/production.md` holds the incident procedure and the
  runbooks, each naming its alarm; Phase 3 check 78 and Phase 4 check 64
  are narrowed with their addendum lines.
- **Deployed & verified:** the dispatched `deploy-production.yml` run on
  this step's merge commit succeeded; production `/version` (service
  token) reports that SHA; a Sentry event and a Grafana metric from that
  revision are visible; the status page shows every production monitor
  up; the newest `production-health` run passed.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit and licence allowlist clean for the `hosted`
  group — no telemetry carries personal data, and every telemetry secret
  lives in Secret Manager.

---

## Step 15 — Feedback Channels and Gate G2 Instrumentation

**Status:** Not started

> **Goal:** Make demand measurable from the first day, without tracking
> anyone (ROADMAP §5 Gate G2; ADR-0013 decisions 13, 14 and 19). Configure
> GitHub Discussions for the launch (announcements, questions, ideas, show
> and tell) and route questions there from the issue forms; add the
> newsletter and the waitlist through the one email processor decision 14
> chose, with plain HTML forms that post straight to it — double opt-in,
> a tier-interest field on the waitlist, no key in the site and no address
> through our API or logs; add `/pro/`, the priced "Pro" preview: the
> planned features and indicative prices, a plain statement that nothing
> exists, is sold or is charged yet, and the waitlist — a fake door that
> records intent and sells nothing; add cookie-less analytics from decision
> 13's provider, its tracker served from our own origin, with an allowlist
> of custom events (`calculator_run`, `download`, `pro_preview_click`,
> `newsletter_submit`, `waitlist_submit`, `search`) whose properties never
> hold an input, a value, a query or an address; and add
> `growth-metrics.yml`, a weekly job that writes counts only — analytics
> totals and events, sign-ups by list and tier, API and MCP requests by
> route kind, PyPI downloads and GitHub stars — as a comment on a pinned
> "Gate G3 ledger" issue. Parent: ROADMAP §4 5.9 (feedback channels, the
> Pro preview, Gate G2 metrics); §5 "Monetization strategy & validation
> gates" and "Data classification" (waitlist emails, analytics); ADR-0013
> decisions 13, 14 and 19.

**Branch:** `feature/phase05-step15-growth-signals`

**Deploys:** the staging site (built without analytics) through
`deploy-staging.yml`, and production through a dispatched, approved
`deploy-production.yml` run, behind Access until the cutover; the ledger
workflow runs from `main`. The forms and events are verified live in
production before launch with the maintainer's own sessions.

|               |          | Cost                 | Balanced             | Quality            |
| ------------- | -------- | -------------------- | -------------------- | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**      | **GPT-6.1 Sol**      | **Gemini 4 Argon** |
|               | Platform | Codex                | Codex                | Antigravity        |
|               | Level    | Low                  | High                 | High               |
|               | AA       | 42.1                 | 50.2                 | 52.6               |
|               | Price    | $1.36/1M             | $2.18/1M             | $4.00/1M*          |
| **Runner‑up** | Model    | **Gemini 3.8 Flash** | **Sonnet 5.5**       | **Opus 5.5**       |
|               | Platform | Antigravity          | Claude Code          | Claude Code        |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 39.8                 | 46.8                 | 53.6               |
|               | Price    | $2.19/1M             | $3.03/1M             | $6.02/1M           |
| **Backup**    | Model    | **Sonnet 5.5**       | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    |
|               | Platform | Claude Code          | Antigravity          | Codex              |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 40.8                 | 40.9                 | 50.2               |
|               | Price    | $2.69/1M             | $4.29/1M             | $2.18/1M           |

Ranked for coding, medium complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and knowledge SECONDARY: static
forms, a preview page, a vendored tracker with an event allowlist, and a
small scheduled collector, around privacy rules that leave no room for a
convenient shortcut. Complexity is Medium — each piece is small and the
vendors are chosen — and the step is not novel. The ladder's Balanced
column runs: GPT-6.1 Sol on Codex at Intelligence High (ChatGPT Pro; AA
Intelligence Index 50.2), Runner-up Sonnet 5.5 on Claude Code at Effort
High, Backup Gemini 3.8 Flash on Antigravity. Cost runs GPT-6.1 Sol at
Intelligence Low (42.1) and Quality Gemini 4 Argon on Antigravity at
Effort High (52.6). New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step15-growth-signals`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 15 is
       complete. You can now move
       on to Step 16." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 16.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Email addresses go only to the processor: the forms
      post directly to it (never through our API, a Worker,
      a log or analytics), it confirms by double opt-in, its
      account has two-factor authentication and one owner,
      and a deletion request is honoured through it.
    - Analytics is cookie-less and aggregate: no cookie, no
      localStorage, no fingerprint, no cross-site tracking,
      query strings excluded; the tracker is served from our
      origin at a pinned version; a test holds every event
      name and property to the allowlist and proves none
      carries an input, a value, a search query, an email or
      a model result.
    - The Pro preview takes no payment detail and no account:
      its only input is the waitlist form; its disclosure
      that nothing is sold or charged is tested to be
      present.
    - growth-metrics.yml writes counts only (never an
      address or an identifier), reads its tokens from a
      `growth` environment that admits only `main`, grants
      issues: write only to its report job, and passes
      actionlint and zizmor; Phase 3 check 78 and Phase 4
      check 64 are narrowed for it.
  </security>

  <context>
    pyeconomics. Phase 5. Step 15: feedback channels and
    Gate G2 instrumentation.

    Current state (post-Phase-5 Step 14):

    - Production runs privately and is observed: Sentry,
      Grafana Cloud (request counts by route kind, including
      /mcp), Better Stack, production-health.yml, and the
      alarm proofs recorded.
    - GitHub Discussions is enabled on the repository with
      no launch categories; categories are created in the
      repository's settings, not through the API.
    - ROADMAP §5 Gate G2: cookie-less analytics, a
      newsletter, a waitlist with tier interest, a priced
      "Pro" preview (fake door), API and MCP usage, downloads
      and stars — all recording, instrumentation verified
      live. Gate G3 (decision 19): the window and thresholds
      the maintainer confirmed in Step 2.
    - Facts read on 2026-10-29 (re-check at kickoff): Umami
      Cloud's free Hobby plan records 100,000 events a month
      with custom events and properties, no cookies, US and
      EU servers; Buttondown's plain form posts to
      `https://buttondown.com/api/emails/embed-subscribe/
      <username>` with no key (not by fetch), takes hidden
      `metadata__<key>` fields, requires double opt-in, is
      free to 100 subscribers and $9 a month to 1,000, and
      offers a DPA; pypistats.org's API gives recent
      downloads without a key.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 9, 13,
      14 and 19) and ROADMAP §5 "Monetization strategy &
      validation gates" and "Data classification".
    - web/ (the layout, the islands, the headers check) and
      the Step 9 network-log test.
    - .github/ISSUE_TEMPLATE/ (the forms and config.yml) and
      CONTRIBUTING.md.
    - .github/workflows/production-health.yml (the report
      job's pattern) and the providers-live issue pattern.
    - The processor's and the analytics provider's current
      documentation, read at kickoff.
  </context>

  <goal>
    Discussions, the newsletter, the waitlist with tier
    interest, the Pro preview and cookie-less analytics are
    live in production behind Access, each recorded by a
    test event; the weekly ledger holds every G2 count; no
    address, input or identifier reaches anywhere but the
    processor.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer: create
      the processor account (two-factor authentication on,
      double opt-in on, the DPA accepted) and the analytics
      site; create the Discussions categories; create the
      `growth` environment (refs: main) with the read-only
      tokens the ledger needs (`gh secret set <NAME> --env
      growth` from prompts), where the plans offer an API;
      confirm the Pro preview's tiers and indicative prices
      (decision 19's anchors); and approve the merge and the
      production deploy. Record what was done, never a
      value.
    </requirement>

    <requirement>
      Forms: /newsletter/ and a footer form post with `method
      post` to the processor's embed endpoint (form-action
      allows only it, decision 9), with an email input, a
      hidden `metadata__source`, and on /pro/ a
      `metadata__tier` choice (personal, commercial, team);
      each says what is collected, that confirmation is by
      email, and links the privacy policy. No JavaScript
      sends an address.
    </requirement>

    <requirement>
      /pro/: the planned Pro features from ROADMAP §5
      (saved models and scenarios, batch runs and exports,
      higher API quotas, a commercial-use licence), the
      indicative prices the maintainer set, a prominent
      statement that Pro does not exist yet and that nothing
      is sold, charged or collected here but the optional
      waitlist, per-tier "notify me" controls that record
      `pro_preview_click` with the tier and open the
      waitlist form. No account, payment field or checkout.
    </requirement>

    <requirement>
      Analytics (production builds only; staging builds
      omit it): the provider's tracker vendored at a pinned
      version under web/public/, configured to exclude query
      strings and hashes, its collector origin added to
      connect-src; web/src/lib/events.ts the only caller,
      with the event allowlist; the calculator, downloads,
      search and forms emit their events with allowlisted
      properties (model id, format, tier, list) only.
    </requirement>

    <requirement>
      Ledger: scripts/growth_metrics.py (standard library
      only; it runs in the workflow, never in the package)
      collects PyPI downloads for pyeconomics and
      pyeconomics-app (pypistats), stars, forks and
      Discussions activity (GITHUB_TOKEN), analytics totals
      and events, sign-ups by list and tier, and API and MCP
      requests by route kind, and formats one Markdown table
      of counts; where a vendor's plan has no API, the row
      says "manual" and the maintainer adds the figure. The
      workflow (weekly and on dispatch) posts it on the
      pinned "Gate G3 ledger" issue it creates on first run;
      the first comment is the pre-launch baseline.
    </requirement>

    <requirement>
      Issue forms: config.yml's contact links send questions
      to Discussions; CONTRIBUTING and the site footer link
      Discussions and the newsletter.
    </requirement>

    <requirement>
      Tests: the event allowlist (Vitest); the forms' action,
      method and fields and the absence of fetch (Playwright);
      the network-log test from Step 9 rerun with analytics
      on, finding only allowlisted event properties; the Pro
      disclosure's presence; the ledger script over recorded
      responses (pytest); axe and Lighthouse on /pro/ and
      /newsletter/ at decision 19's scores.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      and Phase 4 check 64 for growth-metrics.yml's `growth`
      secrets, with addendum lines.
    </requirement>

    <requirement>
      Filepath comment: every new file gets the
      repo-relative path as the first line where its type
      allows a comment; a new Python file gets the
      three-line header.
    </requirement>
  </requirements>
</task>
```

### Step 15 acceptance criteria

- Discussions has its launch categories, and the issue forms and the site
  route questions to it.
- The newsletter and waitlist forms post straight to the processor with
  double opt-in and a tier field; no address passes through the site's
  code, the API, a log or analytics.
- `/pro/` shows the planned features, indicative prices and the statement
  that nothing is sold, with per-tier intent recorded and no payment field.
- Production pages load the vendored, cookie-less tracker; every event
  passes the allowlist; the network-log test finds no input, value, query
  or address in any request.
- `growth-metrics.yml` posted the baseline comment with every count (or a
  "manual" row) on the pinned ledger issue; Phase 3 check 78 and Phase 4
  check 64 are narrowed with their addendum lines.
- **Deployed & verified:** the dispatched `deploy-production.yml` run on
  this step's merge commit succeeded; from a maintainer session through
  Access, production records a page view and each custom event in the
  analytics dashboard, a test sign-up with its tier reaches the processor
  and is then deleted through it, Grafana shows API and MCP requests by
  route kind, and the newest ledger comment lists them.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — email addresses reach only the
  processor, analytics is cookie-less with allowlisted events, the Pro
  page takes no payment detail, and the ledger writes counts only.

---

## Step 16 — Legal, Trust and Brand

**Status:** Not started

> **Goal:** Get the launch's legal, attribution and trademark obligations
> right before anyone outside can see the site (ROADMAP §4 5.7; ADR-0013
> decision 20). Publish `/legal/terms/` — with the New York Fed's and the
> OECD's conditions passed through as their terms require — `/legal/privacy/`
> generated from one data-flows file that names every processor, what it
> holds, where and for how long, `/legal/disclaimers/` (educational use, not
> advice, no registration, as is, the hypothetical-results legends from
> FINRA Rule 2214 and CFTC Rule 4.41 as templates, the data notices and the
> CFA® notice), `/sources/`, the "Data sources & licences" page generated
> from provider metadata, `/legal/licence/` with the third-party licences of
> the shipped bundle, and `/.well-known/security.txt` per RFC 9116; check
> that every chart, table and download carries its source's attribution
> and notices; draft the permissions programme's letters — to the St. Louis
> Fed, Ken French, Robert Shiller, the IMF, the Philadelphia, Atlanta and
> Cleveland Feds, and CFA Institute about the mark in URL paths — for the
> maintainer to send, each tracked as an issue, a grant becoming a
> reclassification and silence leaving a source library-only; record the
> trademark clearance search ADR-0009 asks for and any filing counsel
> advises; and assemble the counsel packet the readiness gate needs.
> Parent: ROADMAP §4 5.7; §5 "Data licensing policy", "Legal & brand
> guardrails" and "Data classification"; ADR-0005; ADR-0009; ADR-0013
> decision 20.

**Branch:** `feature/phase05-step16-legal-trust`

**Deploys:** the staging site through `deploy-staging.yml`, and production
through a dispatched, approved `deploy-production.yml` run behind Access,
so the pages are live where Step 18 checks them; the letters and the
clearance search are the maintainer's, sent and commissioned during the
step.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Gemini 4 Argon** | **Opus 5.5**       |
|               | Platform | Codex              | Antigravity        | Claude Code        |
|               | Level    | Medium             | High               | XHigh              |
|               | AA       | 47.8               | 52.6               | 56                 |
|               | Price    | $1.61/1M           | $4.00/1M*          | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **Opus 5.5**       | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Claude Code        | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 53.6               | 52.6               |
|               | Price    | $3.03/1M           | $6.02/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **GPT-6.1 Sol**    | **GPT-6.1 Sol**    |
|               | Platform | Antigravity        | Codex              | Codex              |
|               | Level    | Low                | High               | XHigh              |
|               | AA       | not measured       | 50.2               | 51                 |
|               | Price    | $2.40/1M*          | $2.18/1M           | $4.00/1M           |

Ranked for knowledge, high complexity. Price: list $ per 1M tokens (3 in : 1
out) × the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Knowledge is PRIMARY and coding SECONDARY: legal and
regulatory texts that must say exactly what the data flows and the data
terms are, notices that must be verbatim, letters that must ask the right
question of each source, and a few generated pages and checks. Complexity
is High — a wrong privacy statement or a missing pass-through is a real
liability at launch — but the step is not novel: ROADMAP §5 fixes the
guardrails, and counsel reviews the result. The ladder's Balanced column
runs: Gemini 4 Argon on Antigravity at Effort High with Thinking on
(Google AI Ultra; AA Intelligence Index 52.6), Runner-up Opus 5.5 on
Claude Code at Effort High, Backup GPT-6.1 Sol on Codex at Intelligence
High. Cost runs GPT-6.1 Sol at Intelligence Medium (47.8) and Quality Opus
5.5 at Effort XHigh (56.0). New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step16-legal-trust`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 16 is
       complete. You can now move
       on to Step 17." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 17.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The privacy policy is generated from
      web/src/content/legal/data-flows.json, and a test fails
      when an origin in the CSP's connect-src or form-action,
      a vendor in decisions 13–15, or a log the service keeps
      is missing from it; the policy states that GET runs'
      URLs, inputs included, reach the host's request logs,
      and that the calculator uses POST to keep inputs out.
    - security.txt names the private vulnerability
      reporting route and SECURITY.md as its policy, expires
      within a year, and a test fails when fewer than 30 days
      remain.
    - The letters, the clearance search and the counsel
      packet hold no secret and no personal data beyond the
      maintainer's published name and the project's address;
      the institutions' contacts are those their own pages
      publish.
    - Nothing in this step changes a provider's licence
      class: a grant arrives later as its own reclassification
      pull request with tests, and the hosted snapshots follow
      it.
  </security>

  <context>
    pyeconomics. Phase 5. Step 16: legal, trust and brand.

    Current state (post-Phase-5 Step 15):

    - The site's footer carries the CFA® notice, "As is; not
      investment advice" and links to /legal/disclaimers/,
      /sources/ and the licence, which do not exist yet; the
      status page, Discussions, the newsletter, the waitlist,
      the Pro preview and analytics are live behind Access.
    - Every provider carries its licence class, terms page,
      attribution and notices (sources.json in the site
      data); exports carry them per file (Phase 4); the
      calculator's sources panel and the explorer's chart
      annotation show them (Steps 6 and 9).
    - Facts read on 2026-10-29 (re-check at kickoff): the New
      York Fed's terms (2023-06-09) require a redistributor to
      pass its permissions, conditions and restrictions on
      unchanged, to imply no endorsement, to label
      modifications, and for SOFR and BGCR to carry the DTCC
      Solutions notice; the OECD's terms (2024-07-01) let
      data be shared for any purpose with its citation and
      warn that third-party data may carry more restrictions;
      FINRA Rule 2214's required legend begins "IMPORTANT:
      The projections or other information generated by";
      CFTC Rule 4.41(b)(1) prescribes the statement beginning
      "These results are based on simulated or hypothetical
      performance results that have certain inherent
      limitations"; RFC 9116 requires Contact and Expires;
      FRED's terms say the St. Louis Fed cannot grant
      permission for third-party series; CFA Institute
      publishes no rule on URL paths (its trademark contact
      is the one to ask).

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 9 and
      13–15, 20), ADR-0005 and ADR-0009.
    - docs/roadmap/ROADMAP.md §5 "Data licensing policy",
      "Legal & brand guardrails" and "Data classification",
      in full.
    - docs/notices.md, SECURITY.md, NOTICE and LICENSE.
    - src/pyeconomics/data/providers/ (each provider's
      terms metadata) and scripts/web/export_site_data.py.
    - Each source's terms page and each institution's
      contact page, read at kickoff.
  </context>

  <goal>
    The terms, privacy policy, disclaimers, sources page,
    licence page and security.txt are live and match the
    service's real data flows and the sources' terms; every
    chart and file carries its attribution; the letters are
    sent and tracked; the clearance search is recorded; the
    counsel packet is with counsel.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer: the
      legal entity and contact address the pages name, the
      governing law (or "TBD by counsel"), the counsel and
      the clearance-search provider they engage, approval to
      send each letter from the project's address, and
      approval to merge and to deploy. Record the answers.
    </requirement>

    <requirement>
      Pages (generated where the source is data): terms of
      use (the service and its licence, acceptable use and
      rate limits, the data terms with the New York Fed's
      and the OECD's conditions passed through and every
      hosted source's terms linked, no warranty, a liability
      cap, changes, contact); privacy policy from
      data-flows.json (each processor — Cloudflare, Google
      Cloud, Sentry, Grafana Cloud, Better Stack, the
      analytics provider, the email processor, GitHub, Read
      the Docs — what it holds, why, where, for how long,
      and its DPA; cookie-less analytics; rights and the
      contact; the open counsel questions marked);
      disclaimers (ROADMAP §5's list, with FINRA Rule 2214's
      legend wording as the template wherever a model shows
      simulated or hypothetical outcomes, and CFTC Rule
      4.41(b)(1)'s statement where futures appear);
      /sources/ from sources.json (class, terms page,
      attribution, notices, hosted availability, snapshot
      cadence) with ROADMAP §5's required-notices table;
      /legal/licence/ (Apache-2.0, NOTICE, and the shipped
      bundle's third-party licences generated from the
      production dependency tree); security.txt.
    </requirement>

    <requirement>
      Simulated outcomes: the models whose outputs are
      simulated or hypothetical (the Monte Carlo and
      backtest families of the launch catalog, listed in the
      PR) carry the legend on their pages, next to the
      result; a test holds the list to a property the
      registry exposes (tags or evidence), not to a
      hand-kept list of ids.
    </requirement>

    <requirement>
      Attribution audit: a test per provider asserts its
      attribution and notices appear in the calculator's
      sources panel, the explorer's chart annotation and
      each download format (Phase 4's export notice test is
      reused for files); FRED's notice appears only on
      local surfaces.
    </requirement>

    <requirement>
      Permissions programme: docs/operations/permissions.md
      holds one letter per recipient (what pyeconomics is,
      the exact use asked about — display on the hosted
      site, snapshots, downloads, LLM use where it applies —
      the attribution offered, the non-commercial status at
      launch, and the contact), the institutions' published
      contacts, and a table of sent dates and answers; one
      issue per letter (label `permissions`) tracks it. CFA
      Institute's letter asks about the mark in URL paths and
      filter values. The page says a grant becomes a
      reclassification PR and silence leaves the source
      library-only.
    </requirement>

    <requirement>
      ADR-0009: the clearance search's result and any filing
      counsel advises are recorded as a dated entry in its
      Consequences (the exception ADR-0009 allows for actions
      it asks to be recorded); if the search is not back
      before Step 18, the record says when it is expected.
    </requirement>

    <requirement>
      Counsel packet: docs/operations/counsel-review.md lists
      the pages, the data-flows file, ROADMAP §5's licensing
      policy and guardrails, and the questions (FRED content
      at inference time, an EU or UK representative, the
      governing law, the liability cap, analytics without a
      banner, the New York Fed and OECD pass-through, the
      Pro preview's wording); the maintainer sends it; Step
      18 records the outcome.
    </requirement>

    <requirement>
      Tests: the data-flows completeness test, security.txt's
      fields and expiry, the attribution audit, the legend
      test, every legal page's presence in the sitemap and
      footer, and axe and Lighthouse on /legal/privacy/ at
      decision 19's scores.
    </requirement>

    <requirement>
      Filepath comment: every new file gets the
      repo-relative path as the first line where its type
      allows a comment; JSON files carry none (JSON allows no
      comments).
    </requirement>
  </requirements>
</task>
```

### Step 16 acceptance criteria

- `/legal/terms/`, `/legal/privacy/`, `/legal/disclaimers/`, `/sources/`,
  `/legal/licence/` and `/.well-known/security.txt` are live; the terms
  pass through the New York Fed's and the OECD's conditions; the privacy
  policy is generated from the data-flows file, which a test holds
  complete against the CSP and the vendors.
- Simulated-outcome models carry the legend; every provider's attribution
  and notices appear on charts, tables and downloads under tests.
- The letters are in `docs/operations/permissions.md`, each sent by the
  maintainer and tracked by an issue; CFA Institute's asks about URL paths.
- ADR-0009 records the clearance search (or its expected date) and any
  filing; `docs/operations/counsel-review.md` is with counsel.
- **Deployed & verified:** the dispatched `deploy-production.yml` run on
  this step's merge commit succeeded; through Access, production's six
  legal and trust URLs answer 200 with their headers,
  `/.well-known/security.txt` parses with Contact and Expires, and
  `/sources/` lists every provider with its class and notices.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the privacy policy matches the real data
  flows, security.txt is valid and current, and no licence class changed.

---

## Step 17 — Public-API Freeze, Release Candidate and Production Soak

**Status:** Not started

> **Goal:** Freeze what 1.0.0 promises and put the exact candidate into
> production for its soak (ADR-0013 decisions 17 and 18). Write
> `docs/public-api.md`, the inventory of everything ADR-0003 makes public
> at 1.0.0 — the Python API's `__all__`s, the command tree and options, the
> REST paths and schemas, the MCP tool names and schemas, the problem slugs
> and type URIs, `registry.json`'s format, the export formats, the settings
> and environment variables, the extras and the site's page URLs — with a
> test that derives the inventory from the code and fails on any change the
> inventory and the changelog do not record; dispose of #197 as decision 17
> says; rehearse the exact candidate on TestPyPI by tagging `main`'s head
> `v1.0.0rc1.dev1`, both distributions' first joint upload, with clean
> installs; then set `1.0.0rc1`, write its release notes and the first
> released-page ledger, merge, tag `v1.0.0rc1`, approve the PyPI and
> production deployments, publish the GitHub pre-release and the MCP
> Registry entry (stdio only), freeze Dependabot to security fixes, and
> start the seven-day production soak behind Access, with its start
> recorded. Parent: ROADMAP §4 5.9 ("`1.0.0rc1` soaked in production-like
> conditions"); §5 "Release & tagging" and "Readiness gate before an
> irreversible cutover"; ADR-0003; ADR-0013 decisions 17 and 18.

**Branch:** `feature/phase05-step17-release-candidate`

**Deploys:** TestPyPI (`v1.0.0rc1.dev1`, before the PR merges), then PyPI
(`v1.0.0rc1`, both distributions, a pre-release that plain `pip install`
ignores), the GitHub pre-release, the MCP Registry entry at `1.0.0rc1`,
and production through `deploy-production.yml` on the tag, behind Access;
the soak runs for seven days from that deploy.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and coding SECONDARY: a release
run across TestPyPI, PyPI, GitHub, the MCP Registry and production, with
maintainer approvals at three gates, around a public-API inventory and its
test. Complexity is High — every upload is permanent, and the inventory
fixes what 2.0.0 alone may break — but the step is not novel: it repeats
Phase 4's rehearse-then-release pattern with a second distribution. The
ladder's Balanced column runs: Sonnet 5.5 on Claude Code at Effort XHigh
(claude.ai Max; AA Intelligence Index 51.9), Runner-up GPT-6.1 Sol on
Codex at Intelligence High, Backup Gemini 4 Argon on Antigravity at Effort
Medium. Cost runs GPT-6.1 Sol at Intelligence Medium (47.8) and Quality
Opus 5.5 at Effort XHigh (56.0). New conversation per phase-boundary
hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step17-release-candidate`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 17 is
       complete. You can now move
       on to Step 18." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 18.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Every upload goes through Trusted Publishing with PEP
      740 attestations for both distributions; no token is
      created; each published file's SHA-256 equals a local
      `uv build --no-config` of the same commit, or the
      difference is explained.
    - The production deploy promotes the image staging
      verified for the tagged commit; nothing is rebuilt for
      production; the site stays behind Access and refuses
      indexing (a pre-release build).
    - During the soak only security fixes merge (Dependabot
      security updates and `hotfix/` branches); every other
      change waits for Step 19, so the candidate soaked is
      the candidate released.
  </security>

  <context>
    pyeconomics. Phase 5. Step 17: the public-API freeze,
    the release candidate and the production soak.

    Current state (post-Phase-5 Step 16):

    - main reads 1.0.0rc1.dev1; staging and production
      (behind Access) run the complete site, API, snapshot
      jobs, observability and growth signals; the legal
      pages are live behind Access; the alarm proofs are
      recorded.
    - release.yml publishes both distributions (`.devN` to
      TestPyPI, other tags to PyPI behind the `pypi`
      approval); the pending publishers for pyeconomics-app
      exist on TestPyPI and PyPI; release-smoke.yml installs
      pyeconomics[app] and smokes serve; mcp-registry.yml
      publishes server.json on a published release.
      deploy-production.yml deploys a non-`.dev` `v*` tag
      after the maintainer's approval.
    - ADR-0003: from 1.0.0 a breaking change needs 2.0.0;
      removals follow one minor release of warnings; model
      ids are permanent. The Public-API rule in this roadmap
      says this step freezes the surfaces.
    - #197 (the MCP tool list costs about 69k tokens of
      context) is open; decision 17 says how it is disposed
      of.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 16–18),
      ADR-0003 and ADR-0012.
    - src/pyeconomics/__init__.py and every public
      package's `__all__`; cli/app.py; server/openapi.py and
      the OpenAPI snapshot; mcp/tools.py and the tools/list
      snapshot; surfaces/problems.py; data/config.py.
    - docs/releases/1.0.0b1.md and 1.0.0b1-readiness.md
      (the shapes), CHANGELOG.md, CITATION.cff, server.json.
    - .github/workflows/release.yml, release-smoke.yml,
      mcp-registry.yml and deploy-production.yml.
    - web/released-pages.json and its test (Step 5).
  </context>

  <goal>
    The public API is inventoried and pinned by a test;
    1.0.0rc1 of both distributions is on PyPI with
    attestations after a clean TestPyPI rehearsal; production
    runs it behind Access; the seven-day soak has begun and
    only security fixes may merge until Step 19.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      each action and its effect: push the rehearsal tag
      `v1.0.0rc1.dev1` on main's head; approve the
      `testpypi` deployment; after the PR merges, push
      `v1.0.0rc1`; approve the `pypi`, `production` and
      `mcp-registry` deployments; publish the GitHub
      pre-release; hold Dependabot's non-security PRs until
      Step 19. Record the approvals in the PR.
    </requirement>

    <requirement>
      Rehearsal first (a failed rehearsal is a NO-GO: the
      fix lands on a `fix/` branch that moves main to the
      next `.devN`, and the rehearsal repeats): on the
      `v1.0.0rc1.dev1` tag, release.yml publishes both
      distributions to TestPyPI; verify each file's
      provenance and SHA-256 against a local build, then in
      clean venvs install from TestPyPI (`uv venv
      --no-config`; `uv pip install --no-config`) the core,
      `[econometrics,plot]`, `[server]`, `[app]` (and
      `pyeconomics serve` serving `/` and a model page) and
      `[mcp]` through uvx with the Inspector.
    </requirement>

    <requirement>
      docs/public-api.md and tests/repo/test_public_api.py:
      the inventory in sections, and a test that derives each
      section from the code (the `__all__` lists, the Cyclopts
      command tree and options, the OpenAPI paths and
      operation ids, the MCP tool names, problems.ROWS'
      slugs, registry.json's format number, the export
      formats, the settings keys and environment variables,
      the extras, and web/released-pages.json) and fails on
      a difference the inventory does not record. A later
      change updates the inventory and the changelog, and
      after 1.0.0 follows ADR-0003.
    </requirement>

    <requirement>
      #197 per decision 17: by default it stays open as a
      compatible 1.x change (slimmer schemas keep every tool
      name and its validation), relabelled to its owner with
      the reason; if the maintainer chose to fix it before
      the freeze, the fix lands here with the agent
      evaluation rerun and docs/mcp-evaluations.md
      committed.
    </requirement>

    <requirement>
      The candidate: `uv version 1.0.0rc1 --no-config` with
      CITATION.cff, server.json (stdio entry only; no remote
      until production is public) and the app's version to
      match; CHANGELOG.md `[1.0.0rc1] - <date>`;
      docs/releases/1.0.0rc1.md (what 1.0 contains, the
      counts — models, providers, concepts, pages — install
      commands with `--pre`, known limitations and their
      issues); web/released-pages.json filled with the
      candidate's page URLs. Then merge, tag, approve, and
      read back: both files on PyPI with provenances, the
      GitHub pre-release (`--prerelease --latest=false`), the
      registry entry at 1.0.0rc1, and production's deploy.
    </requirement>

    <requirement>
      The soak (decision 18): seven days from production's
      deploy of the candidate, with the start time recorded
      in the PR and in docs/releases/1.0.0-readiness.md's
      first section (created here as a skeleton); its
      criteria, which Step 18 evaluates: no unexplained 5xx;
      uptime on the status page of at least 99.5%; every
      scheduled snapshot run green; every Sentry issue
      triaged; production-health green; spend inside the
      budget; no Critical or High security finding open.
      Monitors and the synthetic check run through Access
      throughout.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; Markdown follows the sibling
      conventions.
    </requirement>
  </requirements>
</task>
```

### Step 17 acceptance criteria

- `docs/public-api.md` inventories every public surface, and
  `tests/repo/test_public_api.py` derives the inventory from the code and
  passes; #197 is disposed of as decision 17 says.
- The `v1.0.0rc1.dev1` rehearsal put both distributions on TestPyPI with
  provenances matching local builds, and the clean installs (core, extras,
  `[app]` with `serve`, `[mcp]` through uvx with the Inspector) passed.
- `pyproject.toml`, `CITATION.cff`, `server.json` and the app read
  `1.0.0rc1`; `CHANGELOG.md` has its dated section;
  `docs/releases/1.0.0rc1.md` exists; `web/released-pages.json` holds the
  candidate's pages.
- **Deployed & verified:** PyPI lists `1.0.0rc1` of `pyeconomics` and
  `pyeconomics-app`, each wheel and sdist with a provenance; a clean
  `pip install --pre "pyeconomics[app]==1.0.0rc1"` runs `pyeconomics
  --version`, `scripts/smoke.py` and `pyeconomics serve`; plain `pip
  install pyeconomics` still resolves 0.2.6; the GitHub pre-release and the
  MCP Registry entry at `1.0.0rc1` exist; `deploy-production.yml` on the tag
  succeeded and production `/version` (service token) reports the tagged
  SHA; the soak's start is recorded.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — every upload carries attestations with
  no token created, production runs the staging-verified digest, and only
  security fixes are admitted during the soak.

---

## Step 18 — Launch Readiness Gate

**Status:** Not started

> **Goal:** Decide, on evidence, whether 1.0.0 may launch (ROADMAP §4 5.9;
> §5 "Readiness gate before an irreversible cutover"; ADR-0013 decisions
> 18–20). After the seven-day soak ends, complete
> `docs/releases/1.0.0-readiness.md` in sixteen sections, each with its
> evidence and a PASS, FAIL or WAIVED verdict (a waiver names the
> maintainer's reason): the candidate and its digests; the soak record;
> scope against ROADMAP §4 5; CI at the candidate; web quality (the
> Lighthouse sample, axe, the CSP-violation run, web parity through the
> deployed API, MCP Inspector over Streamable HTTP against production);
> legal pages and attributions; counsel's review; the trademark clearance
> search; the permissions programme's status; indexing (robots, sitemap
> and the indexable final build); monitoring and every alarm's proof;
> rollback rehearsed in production for the API, the site and the data;
> the load test and its cost projection; security (the OWASP ZAP baseline
> with no High finding, the header check, the image scan, `npm audit`, the
> uploads network-log test, the privacy policy against the data flows,
> waitlist access); the growth instruments and the Gate G3 window and
> thresholds; and the decision — the known limitations with their owners,
> then a `Decision: GO` or `Decision: NO-GO` line in the maintainer's
> words. A FAIL forces NO-GO; a NO-GO's fixes land on
> `fix/` branches, the next candidate is `1.0.0rc2` with a soak the
> maintainer sets, and this step runs again. Parent: ROADMAP §4 5.9; §5
> "Release & deployment strategy" and "Operations & observability
> strategy" ("Acceptance"); ADR-0013 decisions 18–20.

**Branch:** `feature/phase05-step18-launch-gate`

**Deploys:** nothing beyond merge — a readiness record. The rollback
rehearsals touch production (behind Access) and restore it, and the load
test runs against staging; neither changes what is released.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and knowledge SECONDARY: a long
evidence-gathering run across production, staging, PyPI, the registries,
the vendors' dashboards and the scanners, three deliberate production
rollbacks, a load test, and a record that must hold the maintainer's
decision up to scrutiny. Complexity is High — the gate guards an
irreversible public launch — and it is not novel: it repeats Phase 4's
readiness pattern with launch-specific sections. The ladder's Balanced
column runs: Sonnet 5.5 on Claude Code at Effort XHigh (claude.ai Max; AA
Intelligence Index 51.9), Runner-up GPT-6.1 Sol on Codex at Intelligence
High, Backup Gemini 4 Argon on Antigravity at Effort Medium. Cost runs
GPT-6.1 Sol at Intelligence Medium (47.8) and Quality Opus 5.5 at Effort
XHigh (56.0). New conversation per phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step18-launch-gate`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 18 is
       complete. You can now move
       on to Step 19." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 19.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - The ZAP baseline runs against production and staging
      through Access (the service token's headers added by
      ZAP's replacer), with `fail_action` on and
      `allow_issue_writing` off; a High finding is a FAIL; a
      Medium is fixed or recorded with its issue.
    - The load test stays inside the budget: Locust against
      staging through the edge with the service token, for a
      bounded time and rate decided in advance, with its
      cost measured from billing, never against an upstream
      source (the API reads snapshots).
    - The rollback rehearsals restore production exactly:
      latest traffic restored after the API's, the newest
      Worker version after the site's, and the newest
      `current.json` after the data's; production-health is
      green afterwards.
    - The record holds no secret, no token and no personal
      data; evidence links point to runs, dashboards and
      issues, never to values.
  </security>

  <context>
    pyeconomics. Phase 5. Step 18: the launch readiness gate.

    Current state (post-Phase-5 Step 17):

    - 1.0.0rc1 of both distributions is on PyPI; production
      runs it behind Access since the recorded soak start;
      staging runs main; only security fixes have merged
      since the tag.
    - docs/releases/1.0.0-readiness.md exists as Step 17's
      skeleton; docs/releases/1.0.0b1-readiness.md is the
      shape (fourteen sections ending in the decision).
    - The alarm proofs are in docs/operations/production.md;
      the legal pages are live behind Access; the letters
      are sent; counsel and the clearance search were
      engaged in Step 16; the G3 ledger has its baseline.
    - Facts read on 2026-10-29 (re-check at kickoff): the
      ZAP baseline action is zaproxy/action-baseline v0.15.0
      (commit de8ad967d3548d44ef623df22cf95c3b0baf8b25), with
      `rules_file_name`, `fail_action` and
      `allow_issue_writing`; Locust 2.47.0 is MIT (k6 is
      AGPL-3.0, so it is not used); the MDN HTTP Observatory
      scans only public hosts, so its scan runs in Step 19
      right after the Access application is removed.

    Files to read (every file before drafting):
    - docs/adr/0013-web-app-and-launch.md (decisions 15,
      18, 19 and 20).
    - docs/releases/1.0.0b1-readiness.md and the skeleton of
      1.0.0-readiness.md.
    - docs/operations/production.md (the alarm table, the
      rollback runbooks) and staging.md.
    - docs/phase04-qa-findings.md "Pre-ship items and
      owners" and every open issue (`gh issue list`).
    - ROADMAP §4 Phase 5's acceptance criteria and §5 Gate
      G2 and G3.
  </context>

  <goal>
    docs/releases/1.0.0-readiness.md holds every section's
    evidence and verdict and ends in the maintainer's
    decision; a GO lets Step 19 release and open the site, a
    NO-GO names what must change and the next candidate.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Start only after the soak's seventh day; summarise it
      from the status page, Sentry, Grafana, the snapshot
      runs, production-health and billing against Step 17's
      criteria.
    </requirement>

    <requirement>
      Web quality at production (through Access): Lighthouse
      on decision 19's page sample (median of three mobile
      runs, at least 90 in performance, accessibility, best
      practices and SEO on every page); axe with the WCAG 2.2
      AA tags on the same pages with no violation; the
      Playwright CSP-violation run on every sampled page;
      scripts/parity/check_deployed.py for one golden case
      per domain; MCP Inspector over Streamable HTTP at /mcp.
    </requirement>

    <requirement>
      Rollback rehearsed in production, each timed: deploy a
      label-only revision, route traffic back to the previous
      revision, then restore latest; deploy the same site
      build as a new Worker version, roll back to the
      previous version, then forward again; restore the
      previous `current.json` from object versioning, then
      the newest. Record each command, its duration and the
      green check after it.
    </requirement>

    <requirement>
      Load test (decision 19): scripts/load/locustfile.py (a
      `load` dependency group with Locust) weights requests
      by cost class and includes series reads; run it against
      staging through the edge for the agreed duration and
      rate, record p50 and p95 per cost class, 429s, any 5xx
      (none expected but budget-exceeded), the instance count
      and the billed vCPU-seconds, and project a month at
      decision 19's planning traffic against production's
      budget.
    </requirement>

    <requirement>
      Security: the ZAP baseline (a workflow,
      zap-baseline.yml, dispatched against production and
      staging with the Access headers, the rules file
      .zap/rules.tsv for recorded false positives); the
      headers check against production's live responses; the
      image scan of the candidate digest; `npm audit` for
      web/ and tools/node/; the uploads network-log test; the
      data-flows completeness test; the processor account's
      two-factor authentication and single owner, confirmed by
      the maintainer.
    </requirement>

    <requirement>
      Legal and outside parties: counsel's review recorded
      (date, scope, outcome, and every change it asked for
      made); the clearance search's result (or WAIVED with
      the maintainer's reason and the expected date); each
      permission letter's sent date and any answer; a grant
      that arrived handled as its own reclassification PR.
    </requirement>

    <requirement>
      Indexing: a final-version production build (built
      locally from the candidate with the version set to
      1.0.0) writes an indexable robots.txt and sitemap, and
      the pre-release build refuses indexing; the canonical
      links and the redirect rules (still disabled) are
      ready.
    </requirement>

    <requirement>
      Growth: each Gate G2 signal shows its test events
      (analytics, sign-ups by tier, API and MCP counts,
      downloads, stars); the maintainer confirms or adjusts
      the Gate G3 window and thresholds, and the parent
      roadmap's G3 row is amended in this PR if they change.
    </requirement>

    <requirement>
      Known limitations: every open issue and every Phase 4
      pre-ship item listed with its owner and whether it
      blocks the launch (none may, or the decision is
      NO-GO). The decision section ends with the
      maintainer's line, `Decision: GO — <date> — Nathan
      Ramos, CFA` or `Decision: NO-GO — <date> — <reason>`,
      asked in one question with the evidence summary and
      relayed into the record.
    </requirement>

    <requirement>
      Cross-phase verification rule: narrow Phase 3 check 78
      and Phase 4 check 64 for zap-baseline.yml, which reads
      the Access service tokens from `staging` and
      `production` only, with addendum lines.
    </requirement>

    <requirement>
      Filepath comment: YAML starts with `# <path>`; a new
      Python file gets the three-line header; the rules file
      carries a comment line where ZAP allows one.
    </requirement>
  </requirements>
</task>
```

### Step 18 acceptance criteria

- `docs/releases/1.0.0-readiness.md` holds all sixteen sections, each with
  evidence and a verdict, no unresolved FAIL, every WAIVED item's reason,
  and the maintainer's `Decision:` line.
- The soak met Step 17's criteria; Lighthouse scored at least 90 in all
  four categories on every sampled page; axe found no WCAG 2.2 AA
  violation; no CSP violation occurred; web parity and MCP Inspector
  passed against production.
- The API, site and data rollbacks were rehearsed in production, timed and
  restored; the load test's projection fits the budget.
- The ZAP baseline found no High issue on production or staging; the
  header, image, npm and uploads checks passed; the privacy policy matches
  the data flows.
- Counsel's review, the clearance search and the permissions programme are
  recorded; the Gate G3 window and thresholds are confirmed.
- On a NO-GO, the record names each blocking item, its `fix/` branch or
  issue, and the next candidate; this step's completion line waits for a
  GO.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean, actionlint and zizmor clean on
  `zap-baseline.yml` — the ZAP baseline found no High issue, production
  was restored after every rehearsal, and the record holds no secret or
  personal data.

---

## Step 19 — Cutover and the 1.0.0 Release

**Status:** Not started

> **Goal:** Release pyeconomics 1.0.0 and open the site, only after the
> maintainer's GO (ROADMAP §4 5.10; ADR-0013 decision 18). Set `1.0.0` —
> the stable classifier, `CITATION.cff`, `server.json` with its remote
> entry for `https://pyeconomics.dev/mcp`, the app's version, the README
> and PyPI description, `docs/index.md`, the documentation's title and
> banner, `SECURITY.md`'s supported versions with 0.2.x at end of life, the
> changelog, the release notes and the announcement draft; narrow the
> earlier phases' checks that pin 0.2.6 as the stable release or the README
> as a beta; merge, tag `v1.0.0`, compare both distributions with the
> candidate's (only version metadata may differ), and approve the PyPI,
> production and registry deployments; then cut over — remove production's
> Access application, enable the `www`, `.com`, `.org` and `.io`
> redirects, confirm the indexable build is live, point Read the Docs'
> default branch at `main` and its default version at `stable` (now 1.0),
> set the repository's homepage, lock `legacy/0.2.x`, publish the GitHub
> release as the latest, lift the Dependabot hold — and run the
> post-launch verification, including the MDN HTTP Observatory scan the
> public host now allows. The maintainer posts the announcement; its date
> opens the Gate G3 window in the ledger. Parent: ROADMAP §4 5.10; §5
> "Release & tagging", "Rollback" and Gate G3; ADR-0002; ADR-0003;
> ADR-0007; ADR-0009; ADR-0012 decision 16; ADR-0013 decision 18.

**Branch:** `feature/phase05-step19-launch`

**Deploys:** PyPI (`v1.0.0`, both distributions, stable), the GitHub
release, the MCP Registry with its remote entry, production through
`deploy-production.yml` on the tag, the public cutover on
`pyeconomics.dev` and its redirects, and Read the Docs' `stable` and
defaults; the post-launch checks run against the public site with no
token.

|               |          | Cost               | Balanced           | Quality            |
| ------------- | -------- | ------------------ | ------------------ | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**    | **Sonnet 5.5**     | **Opus 5.5**       |
|               | Platform | Codex              | Claude Code        | Claude Code        |
|               | Level    | Medium             | XHigh              | XHigh              |
|               | AA       | 47.8               | 51.9               | 56                 |
|               | Price    | $1.61/1M           | $3.56/1M           | $8.46/1M           |
| **Runner‑up** | Model    | **Sonnet 5.5**     | **GPT-6.1 Sol**    | **Gemini 4 Argon** |
|               | Platform | Claude Code        | Codex              | Antigravity        |
|               | Level    | High               | High               | High               |
|               | AA       | 46.8               | 50.2               | 52.6               |
|               | Price    | $3.03/1M           | $2.18/1M           | $4.00/1M*          |
| **Backup**    | Model    | **Gemini 4 Argon** | **Gemini 4 Argon** | **GPT-6 Astra**    |
|               | Platform | Antigravity        | Antigravity        | Codex              |
|               | Level    | Low                | Medium             | XHigh              |
|               | AA       | not measured       | not measured       | 52.4               |
|               | Price    | $2.40/1M*          | $3.20/1M*          | $16.36/1M          |

Ranked for agentic, high complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Agentic is PRIMARY and knowledge SECONDARY: the
release and cutover run — version files, cross-phase narrowings, a tag,
four approved deployments, edge, documentation-host and repository
settings — then a post-launch verification of every public surface.
Complexity is High: the stable upload, the end of 0.2.x and the opening
of the site cannot be undone, only rolled back around. It is not novel:
Step 18's GO rests on a rehearsed candidate, and every action has a
runbook. The ladder's Balanced column runs: Sonnet 5.5 on Claude Code at
Effort XHigh (claude.ai Max; AA Intelligence Index 51.9), Runner-up
GPT-6.1 Sol on Codex at Intelligence High, Backup Gemini 4 Argon on
Antigravity at Effort Medium. Cost runs GPT-6.1 Sol at Intelligence Medium
(47.8) and Quality Opus 5.5 at Effort XHigh (56.0). New conversation per
phase-boundary hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step19-launch`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 19 is
       complete. You can now move
       on to Step 20." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Step 20.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO:
    - Nothing ships without the GO: the step reads
      `Decision: GO` in docs/releases/1.0.0-readiness.md
      before any version file changes, and stops otherwise.
    - The release is the soaked candidate: both
      distributions' archives differ from 1.0.0rc1's only
      in version metadata, and production promotes the
      digest staging verified; anything else is explained in
      the PR before the tag.
    - Opening the site removes Access and nothing else: the
      origin still refuses requests without the edge
      credential, the rate rule and the managed WAF stay on,
      and the rollback is to restore the Access application
      (minutes), recorded in the runbook.
    - The remote MCP entry names only the public endpoint;
      no header, token or secret is declared in server.json.
  </security>

  <context>
    pyeconomics. Phase 5. Step 19: the cutover and the
    1.0.0 release.

    Current state (post-Phase-5 Step 18):

    - docs/releases/1.0.0-readiness.md ends in the
      maintainer's decision. Production runs 1.0.0rc1 behind
      Access; its redirect rules exist, disabled; staging
      runs main; only security fixes merged during the soak.
    - Read the Docs: default branch legacy/0.2.x, default
      version stable (0.2.6); `stable` tracks the greatest
      stable release, so a v1.0.0 tag makes it 1.0.0; the
      defaults change in Admin or through API v3
      (`default_version`, `default_branch`). The legacy
      branch builds from its own .readthedocs.yml.
    - Earlier checks that pin the pre-launch world: Read
      the Docs stable serving 0.2.6 and main titled "1.0
      preview" (Phase 1 V4.4, Phase 2 V7.3, Phase 3 V11.3,
      Phase 4 V15.2); a plain `pip install pyeconomics`
      resolving 0.2.6 (Phase 2 V14.3, Phase 3 V19.3, Phase 4
      V15.3); the README naming `1.0.0b1` (Phase 4 check 58,
      a static check every pull request runs).
    - server.json's remote entry: `"remotes": [{"type":
      "streamable-http", "url": ".../mcp"}]`; a remote must
      be publicly reachable (registry docs, read
      2026-10-29); mcp-registry.yml runs on a published
      release.
    - ADR-0003: 0.2.x reaches end of life at 1.0.0;
      SECURITY.md promises 0.2.x security fixes until then.

    Files to read (every file before drafting):
    - docs/releases/1.0.0-readiness.md (the decision) and
      1.0.0rc1.md.
    - pyproject.toml, packages/pyeconomics-app/pyproject.toml,
      CITATION.cff, server.json, README.md, docs/index.md,
      docs/conf.py, SECURITY.md and CHANGELOG.md.
    - scripts/verify-phase01.sh (V4.4), verify-phase02.sh
      (V7.3, V14.3), verify-phase03.sh (V11.3, V19.3) and
      verify-phase04.sh (check 58, V15.2, V15.3), and the
      end of each earlier phase roadmap.
    - docs/operations/production.md (the cutover runbook)
      and docs/releases/1.0.0b1.md (the notes' shape).
  </context>

  <goal>
    1.0.0 of both distributions is on PyPI and is what a
    plain `pip install pyeconomics` gives; pyeconomics.dev
    serves the indexable site and the API to everyone, with
    the other domains redirecting; Read the Docs' default is
    1.0; the MCP Registry lists the remote endpoint; 0.2.x
    is at end of life; the earlier ledgers still hold; the
    G3 window is open.
  </goal>

  <requirements>
    <requirement>
      Read all files listed in context before making any
      changes.
    </requirement>

    <requirement>
      Kickoff, ONE batched request to the maintainer with
      each action and its effect, in order: push `v1.0.0`
      after the merge; approve `pypi`, `production` and
      `mcp-registry`; remove the Access application for
      pyeconomics.dev and enable the redirect rules (or let
      the step run the API calls); change Read the Docs'
      defaults; set the repository homepage; lock
      `legacy/0.2.x`; publish the GitHub release; lift the
      Dependabot hold; post the announcement. Record the
      approvals in the PR.
    </requirement>

    <requirement>
      Release files: `uv version 1.0.0 --no-config`; the
      classifier `Development Status :: 5 -
      Production/Stable`; CITATION.cff's version and
      `date-released`; server.json's versions and its remote
      entry; the app's version; CHANGELOG.md `[1.0.0] -
      <date>`; docs/releases/1.0.0.md; docs/releases/
      1.0.0-announcement.md (the text the maintainer posts);
      README.md and docs/index.md describing 1.0.0 (plain
      `pip install pyeconomics`, the site, the docs, the
      local app, MCP), keeping the CFA® notice verbatim and
      the `mcp-name:` marker; docs/conf.py's title
      "pyeconomics" with no preview banner; SECURITY.md's
      table (1.0.x supported; 0.2.x end of life on the
      release date).
    </requirement>

    <requirement>
      Cross-phase verification rule, in this PR, each with
      an addendum line in that phase's roadmap: Phase 4
      check 58 narrows to "the README describes the current
      release's install command and the shipped surfaces";
      the documentation checks (Phase 1 V4.4, Phase 2 V7.3,
      Phase 3 V11.3, Phase 4 V15.2) narrow to "`stable`
      serves the greatest stable release (0.2.6 until
      1.0.0) and `main` builds main"; the plain-install
      checks (Phase 2 V14.3, Phase 3 V19.3, Phase 4 V15.3)
      narrow to "a plain install resolves the newest final
      release, never a pre-release". `verify-phase01.sh` to
      `verify-phase04.sh --fast` pass on the PR.
    </requirement>

    <requirement>
      Release: after the merge, the tag; release.yml
      publishes both distributions with attestations;
      compare each archive with 1.0.0rc1's (only METADATA,
      RECORD, PKG-INFO and the version fields differ, or the
      PR explains why); deploy-production.yml promotes the
      tagged commit's digest (data, API, site; the site
      build is indexable now); the GitHub release from
      docs/releases/1.0.0.md as the latest; mcp-registry.yml
      publishes 1.0.0 with the remote.
    </requirement>

    <requirement>
      Cutover (docs/operations/production.md's runbook):
      remove the Access application on pyeconomics.dev
      (keep staging's); enable the `www` and `.com`, `.org`
      and `.io` redirects; set Read the Docs' default branch
      to main and default version to stable, keeping the
      0.2.6 version active and visible; set the repository's
      homepage to https://pyeconomics.dev; lock
      `legacy/0.2.x` with branch protection; lift the
      Dependabot hold; production-health.yml now runs
      without the token. The maintainer posts the
      announcement on Discussions, the newsletter and the
      channels they choose; growth-metrics.yml's next run
      (or a dispatch) records the announcement date as day 1
      of the Gate G3 window.
    </requirement>

    <requirement>
      Post-launch verification (a script,
      scripts/verify_launch.py, reused by Step 20's --live):
      the public checks in this step's Deployed & verified
      bullet, each printed as PASS or FAIL; a FAIL in a
      security header or the Observatory grade restores
      Access while it is fixed.
    </requirement>

    <requirement>
      Filepath comment: every new Python file gets the
      three-line header; TOML and YAML start with `# <path>`.
    </requirement>
  </requirements>
</task>
```

### Step 19 acceptance criteria

- The version files read `1.0.0` with the stable classifier; the README,
  `docs/index.md`, the documentation title, `SECURITY.md`, the changelog,
  the release notes and the announcement describe the release; the earlier
  checks are narrowed with their addendum lines, and every earlier phase's
  `--fast` passes.
- Both distributions' 1.0.0 archives differ from 1.0.0rc1's only in
  version metadata, or the PR explains each difference.
- The Access application on `pyeconomics.dev` is gone, the redirects are
  on, Read the Docs' defaults are `main` and `stable`, the homepage is set,
  `legacy/0.2.x` is locked, the Dependabot hold is lifted, and the
  announcement date is in the ledger.
- **Deployed & verified:** without any token, `https://pyeconomics.dev/
  version` and `/version.json` report the `v1.0.0` SHA; a synthetic check
  runs one model per domain and downloads a CSV carrying its attribution;
  the snapshot heartbeat is green; `https://pyeconomics.com/models/` (and
  `.org`, `.io`, `www`) answers 301 to `https://pyeconomics.dev/models/`;
  robots.txt allows indexing and the sitemap lists every model page; the
  MDN HTTP Observatory grades `pyeconomics.dev` A or better with the CSP,
  HSTS and frame-ancestors present; the ZAP baseline against the public
  site finds no High issue; Read the Docs `stable` serves 1.0.0; a clean
  `pip install pyeconomics` on Python 3.12 and 3.15 installs 1.0.0 and
  passes `scripts/smoke.py`; `pip install "pyeconomics[app]"` then
  `pyeconomics serve` serves the pages locally with a library-only source
  live; `uvx --from "pyeconomics[mcp]==1.0.0" pyeconomics mcp` and the
  hosted `https://pyeconomics.dev/mcp` both pass MCP Inspector; the MCP
  Registry lists 1.0.0 with the remote; `scripts/parity/check_deployed.py`
  passes against production.
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff — secret/PII scan clean, SAST
  clean, dependency audit clean — the release is the soaked candidate, the
  origin still requires the edge credential, and the public site passes
  the Observatory and ZAP checks.

---

## Step 20 — QA and Verification Script

**Status:** Not started

> **Goal:** Package the phase's verification matrix into
> `scripts/verify-phase05.sh` — Phase 4's `--fast`, `--python`, `--node`,
> `--container`, `--security`, `--live`, `--all` and `--post` modes, with
> `--node` now covering the web project (build, tests, axe, Lighthouse,
> audits) beside `tools/node`, and `--live` covering production, the
> monitors and both registries — with independent static checks for every
> Step 1–19 deliverable, Step 20 self-checks and the V1–V20 matrix, plus its
> pytest twin `tests/repo/test_phase05.py` and its live helper
> `scripts/verify_phase05_live.py` (which reuses `scripts/verify_launch.py`);
> produce `docs/phase05-qa-findings.md`, the rollup of every finding, its
> class, its destination and its guard, with the alarm evidence and the
> pre-ship owners for Phases 6 and 7; add `"05"` to
> `.github/workflows/phase-verify.yml`'s matrix and make both `phase-verify`
> jobs for `05` required; re-fire production-health's alarm once on the
> public path; run `verify-phase04.sh --post` (which runs Phases 3, 2 and
> 1's) to show the earlier ledgers still hold; and mark Phase 5 complete
> here and in the parent roadmap. Parent: ROADMAP §5 "Operations &
> observability strategy" ("Acceptance") and this roadmap's
> Post-Implementation Verification.

**Branch:** `feature/phase05-step20-verify`

**Deploys:** nothing beyond merge — the CI matrix entry is live on merge;
the required-check update and the alarm re-fire are part of the step, and
staging redeploys on the merge as on every merge.

|               |          | Cost                 | Balanced             | Quality            |
| ------------- | -------- | -------------------- | -------------------- | ------------------ |
| **Pick**      | Model    | **GPT-6.1 Sol**      | **GPT-6.1 Sol**      | **Gemini 4 Argon** |
|               | Platform | Codex                | Codex                | Antigravity        |
|               | Level    | Low                  | High                 | High               |
|               | AA       | 42.1                 | 50.2                 | 52.6               |
|               | Price    | $1.36/1M             | $2.18/1M             | $4.00/1M*          |
| **Runner‑up** | Model    | **Gemini 3.8 Flash** | **Sonnet 5.5**       | **Opus 5.5**       |
|               | Platform | Antigravity          | Claude Code          | Claude Code        |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 39.8                 | 46.8                 | 53.6               |
|               | Price    | $2.19/1M             | $3.03/1M             | $6.02/1M           |
| **Backup**    | Model    | **Sonnet 5.5**       | **Gemini 3.8 Flash** | **GPT-6.1 Sol**    |
|               | Platform | Claude Code          | Antigravity          | Codex              |
|               | Level    | Medium               | High                 | High               |
|               | AA       | 40.8                 | 40.9                 | 50.2               |
|               | Price    | $2.69/1M             | $4.29/1M             | $2.18/1M           |

Ranked for coding, medium complexity. Price: list $ per 1M tokens (3 in : 1 out)
× the tokens the model uses at that level; * token use not yet measured, a
typical model's at that level assumed.

**Conversation:** New

**Runs:** Balanced — the user-context's Budget priority is `balanced`. If that
column's usage pool reads `tight` or `exhausted`, run the first of its Runner-up
and Backup whose pool has headroom; on a `tight` pool an option marked ↓ (the
Pick one level lower) also runs. With none, a `tight` column runs the Cost
column and an `exhausted` one its Backup.

**Model rationale:** Coding is PRIMARY and agentic SECONDARY: the
mechanical translation of `verify-phase04.sh` into this phase's
deliverables, a wider `--node` and `--live`, a QA rollup, one alarm re-fire
and a required-check update. Complexity is Medium — the template, the
check list and the V-matrix are fixed here — and it is not novel. The
ladder's Balanced column runs: GPT-6.1 Sol on Codex at Intelligence High
(ChatGPT Pro; AA Intelligence Index 50.2), Runner-up Sonnet 5.5 on Claude
Code at Effort High, Backup Gemini 3.8 Flash on Antigravity. Cost runs
GPT-6.1 Sol at Intelligence Low (42.1) and Quality Gemini 4 Argon on
Antigravity at Effort High (52.6). New conversation per phase-boundary
hygiene.

```xml
<task>
  <lifecycle>
    This step MUST follow all six
    stages, in order. Stages 1, 3,
    4, 5, 6 are AS BINDING as any
    `<requirement>` below. Do not
    emit the Stage 6 completion
    line until the PR is merged and
    every acceptance criterion for
    this step is affirmatively met.

    1. CREATE THE BRANCH. Before
       any Read / Edit / Bash, run
       `git checkout -b
       feature/phase05-step20-verify`
       from a clean, up-to-date
       `main`. The exact branch
       name is in this step's
       `**Branch:**` line above.
       If the Worktree rule
       applies, use `git fetch
       origin && git worktree add
       -b <branch> <path>
       origin/main` instead, then
       bootstrap the worktree.

    2. WORK ON THE BRANCH. All
       commits land here. `main`
       is protected with
       `enforce_admins: true` —
       direct pushes will be
       rejected.

    3. OPEN THE PR, THEN MARK THE
       STEP. `gh pr create --base
       main --head <branch>` with a
       Conventional Commits title
       and a body that references
       this roadmap step and its
       acceptance criteria. One PR
       per step. Then, in this
       roadmap file: set this
       step's `**Status:**` line
       (directly under its heading)
       to `Complete — PR #<n>
       (<YYYY-MM-DD>)`, append ` ✅`
       to the step's `## Step`
       heading, and set its
       Summary Table Status cell to
       `Complete — PR #<n>`. Commit
       that edit on the step
       branch and push — the PR
       carries its own completion
       mark, so the roadmap on
       `main` marks this step
       complete exactly when the PR
       merges (Status rule). Same
       commit: on the phase's first
       step, set this roadmap's
       phase-level `**Status:**`
       (under its title) and the
       parent project roadmap's
       Phase 5 `**Status:**` to
       `In progress`; on the final
       step, both to `Complete`,
       with ` ✅` appended to this
       roadmap's `# ` title and to
       the parent's `### Phase 5`
       heading.

    4. WAIT FOR GREEN CHECKS, THEN
       SQUASH-MERGE. Every required
       check must pass. If the PR
       falls behind main, refresh
       with `gh pr update-branch
       --rebase` — never merge main
       into the branch
       (`required_linear_history:
       true`). Once green:
       `gh pr merge <PR> --squash
       --delete-branch`. If this
       step's `**Deploys:**` line
       names a surface, the merge
       is not the finish line: run
       the Deployed & verified
       check against the target
       environment before
       declaring the step complete.

    5. RETIRE THE BRANCH. Sync
       local: `git switch main &&
       git pull --ff-only origin
       main && git fetch --prune
       origin`. Prune any local
       `[gone]` branches. If the
       step ran in a worktree,
       `git worktree remove <path>`
       FIRST — the branch prune
       fails while the branch is
       checked out there.

    6. DISPOSE OF EVERY FINDING,
       DECLARE COMPLETION, THEN
       NEW CONVERSATION. First
       send every finding this
       step surfaced to its
       destination (Triage rule):
       a note for a later step →
       edit that step's <task>
       block now; spec rot → edit
       this roadmap now; a bug →
       fixed in-step or an issue
       number; a judgement call in
       the diff → the PR body; a
       process lesson → written
       where the next conversation
       reads it. A finding you can
       only describe is NOT
       disposed of, and counts as
       an unmet criterion. Only
       once the PR is merged — and
       `main` therefore carries
       this step's `Complete`
       Status line — every
       acceptance criterion is
       affirmatively met, and every
       finding has a destination,
       say so plainly: end your
       final response with an
       explicit, unhedged
       completion line — verbatim
       shape "Step 20 is
       complete. Phase 5 is
       complete. You can now move
       on to Phase 6." That
       line is the LAST line of
       the response. NOTHING
       follows it — no "Follow-ups
       (non-blocking)", "Notes",
       "Next", "worth a glance",
       or suggested improvements.
       A short ledger may PRECEDE
       it, one entry per finding
       naming its destination
       (issue #, file edited, PR
       body) — never an open item.
       If any criterion is unmet
       or any finding has no
       destination, state plainly
       that the step is NOT
       complete, name what is
       outstanding, and omit the
       completion line. "Done"
       means done. Then, for
       phase-boundary hygiene, the
       operator closes this
       session and opens a fresh
       one before Phase 6.
  </lifecycle>

  <security>
    Security is a gate on THIS
    step, not a later phase. It is
    AS BINDING as any
    `<requirement>` below. Before
    the Stage-2 commit, this
    step's work MUST pass the
    local, fail-closed security
    gate — the SAME gate wired
    into the pre-commit hook and
    re-run in CI:

    1. SECRET / PII SCAN. No
       credentials, API keys,
       tokens, or real PII in the
       diff (gitleaks /
       detect-secrets or the
       project's equivalent).
       Secrets go in the secrets
       manager, never in source or
       committed env files.

    2. SAST. No new injection,
       unsafe deserialization,
       weak crypto, path
       traversal, or unsafe-eval
       pattern (bandit / semgrep /
       eslint-plugin-security per
       the stack). Suppress a
       finding ONLY with an inline
       justification comment.

    3. DEPENDENCY AUDIT. Any new
       or bumped dependency passes
       the audit (pip-audit / npm
       audit / osv-scanner); no
       known-vulnerable, yanked,
       or typo-squatted package.

    4. SENSITIVE-DATA REVIEW.
       Whatever this step touches
       stays least-privilege,
       encrypted in transit + at
       rest, and out of logs and
       client bundles. If the step
       adds a data path, name how
       PII/secrets are protected.

    A finding blocks the commit —
    fix it in this step, do not
    defer. Do not declare the step
    complete until the gate is
    clean. This is the safety net
    that stops a security issue
    from reaching the branch, the
    PR, or `main`.

    THIS STEP ALSO AUTHORS the --security mode, so its own
    diff must pass the gate before commit. The verifier
    prints no credential, token, environment value or
    personal data: live checks read the service tokens from
    the maintainer's keyring and report PASS or FAIL only,
    and secrets are checked by name, their values proven by
    authenticated round-trips.
  </security>

  <context>
    pyeconomics. Phase 5. Step 20: QA and the verification
    script.

    Steps 1 through 19 have been implemented: 1.0.0 is on
    PyPI and pyeconomics.dev is public. Now create the
    verification script, the QA findings document and the
    CI matrix update.

    Reference scripts (pattern templates):
    - scripts/verify-phase04.sh (closest precedent: modes,
      record/check/vcheck/vstatic helpers, the bash guard
      Step 1 added, the summary ending in `RESULT: PASS`),
      scripts/verify_phase04_live.py and
      tests/repo/test_phase04.py.
    - scripts/verify-phase03.sh (secondary reference).

    Phase 5 deliverables to verify (about 74 static checks
    across Steps 1 to 19, plus 5 self-checks):

    Step 1 (baseline) — the roadmap and kit tracked; the
    bash guard and the status-keeping trap in all four
    earlier verifiers; actionlint pinned in the gate;
    deploy-staging.yml restores latest traffic.
    Step 2 (ADR-0013) — Accepted and indexed; the parent
    roadmap names it where it amended; AGENTS.md's layout
    and web rules.
    Step 3 (web foundation) — web/ lockfile, .nvmrc and
    engines; static output with security.csp and no
    inlining; the post-build headers script refusing unsafe
    sources; ESLint with the security plugin; the `web` job
    in the aggregate; npm audit and Dependabot for /web; the
    bundle licence check.
    Step 4 (staging site) — wrangler.jsonc's
    run_worker_first list with workers.dev off; the Worker's
    tests; deploy-staging.yml's site job with rollback;
    staging-health probing the site.
    Step 5 (pages) — the model route; the problem pages'
    test; robots and sitemap by version; the released-page
    ledger and its test.
    Step 6 (calculators) — precompiled validators; the
    figure port and its test; the Plotly version test; the
    web parity suite and check_deployed.py.
    Step 7 (navigation) — syllabi/ schema and seed;
    Pagefind in the build; /coverage/; the no-mark-in-URL
    test.
    Step 8 (snapshots) — data/snapshots/ on IO_MODULES; the
    not-in-snapshot row; stale_snapshot in NOTE_WARNINGS;
    the job update and read-only mount in deploy-staging.
    Step 9 (explorer) — the transform option on four
    surfaces; /data/; the upload worker; the network-log and
    no-body tests.
    Step 10 (local app) — the workspace member and its
    allowlist; [app] pinned and outside [all]; serve's site
    mount; release.yml building both.
    Step 11 and 12 (docs) — the tutorial track, how-tos,
    migration guide with its fixture test and study paths;
    the gallery, the marimo exports and the finance
    tutorials.
    Step 13 (production) — deploy-production.yml's triggers,
    environment, order and rollbacks; the production
    runbook; the narrowed secret boundary.
    Step 14 (observability) — the hosted-only observability
    module and `hosted` group; the telemetry canary;
    production-health.yml; the alarm table.
    Step 15 (growth) — forms posting to the processor;
    /pro/'s disclosure; the event allowlist;
    growth-metrics.yml.
    Step 16 (legal) — the legal pages; the data-flows test;
    security.txt; permissions.md and counsel-review.md;
    ADR-0009's dated record.
    Step 17 (candidate) — public-api.md and its test;
    `v1.0.0rc1` on main; the rc release notes.
    Step 18 (gate) — the readiness record's sixteen
    sections and its GO; zap-baseline.yml and the rules
    file; the locustfile.
    Step 19 (release) — `v1.0.0` on main; the dated
    changelog; server.json's remote; the README and index
    for 1.0.0; SECURITY.md's end of life; the earlier
    phases' addendum lines; the permanent ledgers
    unchanged.
    Step 20 self-checks — verify-phase05.sh executable and
    indexed; docs/phase05-qa-findings.md; this roadmap;
    both matrices include 05; the credential backstop,
    hooks and workflow secret boundary.

    Files to read:
    - scripts/verify-phase04.sh, verify_phase04_live.py,
      tests/repo/test_phase04.py and
      scripts/verify_launch.py.
    - docs/phase04-qa-findings.md (the rollup's shape) and
      every Phase 5 PR body (the findings to roll up).
    - All Phase 5 implementation files from Steps 1–19.
  </context>

  <goal>
    Create scripts/verify-phase05.sh with about 74 static
    deliverable checks, 5 self-checks and the V1-V20 matrix
    in eight modes; its twin and live helper; the QA
    findings document; matrix entry 05, required; and the
    phase marked complete.
  </goal>

  <requirements>
    <requirement>
      Read scripts/verify-phase04.sh end-to-end for
      structure, flag parsing, output format, the record /
      check / vcheck / vstatic conventions and the final
      summary table. Mirror the format exactly so the Phase
      5 script is visually continuous with Phase 4's in CI
      logs, including Step 1's bash guard and trap.
    </requirement>

    <requirement>
      Modes: `--fast` (default; static checks only, CI-safe
      on Ubuntu, standard library Python plus a Bash
      credential backstop, under 30 seconds); `--python`
      (the suite with the floors, parity, the docs build, the
      package and app builds and their allowlists); `--node`
      (web/: npm ci, the site data export, astro check, lint,
      Vitest, the build and headers check, Playwright with
      axe, Lighthouse CI, npm audit and the licence check;
      tools/node/: the client, the edge Worker tests and the
      Inspector); `--container` (the image build, scan and
      smoke, with the `hosted` group); `--security` (the
      whole-tree gate, licences for Python and the bundle,
      the cassette scan, npm audit for both projects, the
      headers check over a fresh build); `--live` (GitHub:
      26 strict required checks, the `staging`, `production`
      and `growth` environments' refs and secret names, no
      repository secret; staging and production through
      their edges; Read the Docs; PyPI for both
      distributions; the MCP Registry; the status page; the
      Observatory grade; the newest runs of every deploy,
      probe and ledger workflow and of both snapshot jobs;
      the budgets); `--all` (fast, python, node, container,
      security); `--post` (all, live, published installs,
      the alarm evidence, `verify-phase04.sh --post`, and
      `gh pr checks`). At least one static check confirms
      the gate is wired and no credential pattern is
      committed (the last self-check's backstop).
    </requirement>

    <requirement>
      The V1–V20 checks as this roadmap's Post-Implementation
      Verification lists them, each reported by id; V20.1 to
      V20.4 are the CI and security checks, V20.5 the alarm
      evidence, V20.6 the earlier phases' `--post`.
    </requirement>

    <requirement>
      tests/repo/test_phase05.py (the twin: the script
      exists, is executable, is in the index, lists every
      mode, and its static checks pass) and
      scripts/verify_phase05_live.py (subcommands for the
      published installs, the edges and the launch checks,
      reusing scripts/verify_launch.py; a non-default
      User-Agent for Read the Docs; gcloud called with
      MSYS_NO_PATHCONV unset).
    </requirement>

    <requirement>
      .github/workflows/phase-verify.yml: append "05" to both
      matrices, preserving every prior entry; after both
      jobs pass on the PR, add `phase-verify-fast (05)` and
      `phase-verify-security (05)` to main's required checks
      (26, strict) with the maintainer's approval, batched at
      kickoff with the alarm re-fire.
    </requirement>

    <requirement>
      Operations: re-fire production-health.yml's simulated
      failure once on the public path, confirm its issue and
      the maintainer's notification, close it with a link to
      the QA record, and confirm the newest real run of every
      probe, monitor and snapshot job is green.
    </requirement>

    <requirement>
      docs/phase05-qa-findings.md: a rollup section per step
      (finding, class, destination, guard), the Step 20
      rollup, the alarm evidence (Step 14's table and this
      step's re-fire), the Phase 5 acceptance audit against
      ROADMAP §4 5's criteria, the pre-ship items and owners
      (every open issue with its owner; Phase 6 and Phase 7's
      inherited items), and the final verification evidence
      (the canonical `--post` run's counts per mode).
    </requirement>

    <requirement>
      Before the canonical `--post`: dispatch
      providers-live.yml and providers-heartbeat.yml and wait
      for green runs, because Phase 3's V6.3 needs a
      providers-live success within eight days; run the
      canonical `HYPOTHESIS_PROFILE=ci ./scripts/verify-phase05.sh
      --post` on the frozen branch head, edit no tracked file
      while it runs, and after stopping any run confirm its
      uv and pytest descendants stopped.
    </requirement>

    <requirement>
      Mark the phase complete in the parent project roadmap
      (docs/roadmap/ROADMAP.md, beside this file) in the SAME
      Stage-3 commit that marks this step (Status rule):
      - `### Phase 5` gets `**Status:** Complete —
        <YYYY-MM-DD>; PR #<n>; v1.0.0; phase05-roadmap.md`
        directly under its heading, and the heading ends in
        ✅.
      - Its row in the "Phase Complexity Summary" table
        reads `Complete` (Step 1's PR set it to `In
        progress`).
      - The header `> **Status:**` line names Phase 5 as
        shipped (with `v1.0.0` on PyPI) and Phases 6 and 7
        as next, in parallel.
      - Consistency audit: the Phase 5 "Acceptance criteria"
        there match this roadmap's V1-V20 checks.
      And in THIS roadmap, same commit: its phase-level
      `**Status:**` line (under the title) reads `Complete —
      <YYYY-MM-DD>`, the title and every step heading end in
      ✅, and every step's Summary Table Status cell reads
      `Complete — PR #<n>`.
    </requirement>

    <requirement>
      Script must be executable (`git update-index
      --chmod=+x`), print a clear PASS / FAIL per check, exit
      0 on success and 1 on any failure, and mirror
      verify-phase04.sh's output format, check numbering and
      summary table so CI log diffing across phases is
      frictionless. `--fast` must complete in under 30
      seconds on Ubuntu CI.
    </requirement>

    <requirement>
      Filepath comment: every new file gets the
      repo-relative path as the first line (Bash `# <path>`
      after the shebang; Python the three-line header).
    </requirement>
  </requirements>
</task>
```

### Step 20 acceptance criteria

- `scripts/verify-phase05.sh` exists, is executable, and passes on a clean
  tree post-implementation, with about 74 static checks, 5 self-checks and
  the V1–V20 matrix in all eight modes.
- `--fast` runs in under 30 seconds on Ubuntu CI, and `--post` passes on the
  maintainer's machine with every live check and published install green.
- `docs/phase05-qa-findings.md` is complete with every rollup section, the
  alarm evidence, the acceptance audit and the pre-ship owners.
- `.github/workflows/phase-verify.yml`'s matrix includes `05`, both jobs
  pass on every PR, and `main` requires them, strictly (26 checks).
- `--security` exists and exits 0 (secret/PII scan, SAST, dependency audit
  for Python and both Node projects, licences for Python and the bundle,
  the cassette scan and the headers check clean over the phase's surface);
  V20.4 is green.
- Branch protection still passes on the resulting PR, and
  `verify-phase04.sh --post` passes, including its nested Phase 3, 2 and 1
  runs.
- **Operations:** the runtime surfaces this phase added — the production
  API, the public site, both snapshot jobs and the production budget — each
  have a health signal (the version endpoints, Better Stack's monitors and
  heartbeats, `production-health.yml`, the budget's alerts) and an alarm
  seen to fire once (Step 14's proofs, recorded, and this step's public
  re-fire of `production-health`, with the maintainer's confirmation),
  recorded in `docs/phase05-qa-findings.md` (ROADMAP §5 "Operations &
  observability strategy").
- **Security gate clean** (always the final criterion): the pre-commit
  security gate passed on this step's diff and the security workflow is
  green.
- **Phase closed, nothing carried.** Every finding recorded in
  `docs/phase05-qa-findings.md` has a destination (fixed, an issue number,
  or a named phase that owns it), the "Not in scope" section below is
  current, and no un-tracked item remains. Every step of this roadmap, this
  one included, reads `**Status:** Complete — PR #…` on `main` under a ✅
  heading, the Summary Table's Status column and this roadmap's phase-level
  Status line say `Complete` under a ✅ title, and the parent project
  roadmap's Phase 5 entry (under a ✅ heading), its summary-table row, and
  its header status line say `Complete` — all landed in this step's PR. This
  step's final response ends with two lines and nothing after them: "Step 20
  is complete. Phase 5 is complete. You can now move on to Phase 6." — same
  Stage 6 rule: no "Follow-ups", no trailer.

---

## Post-Implementation Verification

Every V1–V20 check below runs **automatically in CI** on every push and
pull request — no manual invocation required — except four kinds. The
`--live` and `--post` checks read state that needs the maintainer's
authenticated `gh` session, gcloud and keyring (branch protection, the
`staging`, `production` and `growth` environments by name, the newest
deploy, probe, ledger and snapshot runs, the staging and production edges
through their Access service tokens while they are private, PyPI and
TestPyPI, the MCP Registry, Read the Docs, the status page and the
Observatory), plus clean-venv installs from PyPI; they run on the
maintainer's machine with `./scripts/verify-phase05.sh --post` before
Phase 5 is declared complete. The seven-day soak (Step 17) is wall-clock
time. Counsel's review, the trademark clearance search and the permission
letters are outside parties' work that Steps 16 and 18 record. The alarm
notifications are confirmed by the maintainer and recorded in
`docs/operations/production.md` and `docs/phase05-qa-findings.md`.

| Mode | Runs in | Covers |
| --- | --- | --- |
| `--fast` | `phase-verify.yml`, matrix `05` | static checks; V*.1; V20.1–3 |
| `--python` | `ci.yml` jobs; local | suite, parity, docs, builds |
| `--node` | `ci.yml` web, clients, inspector | the site and tools/node |
| `--container` | `ci.yml` container job; local | image, scan, smoke |
| `--security` | `phase-verify.yml` security job | V3.3, V20.4 |
| `--live` | the maintainer's machine | GitHub, edges, registries |
| `--all` | local | fast to security |
| `--post` | the maintainer's machine | all, live, installs, nested |

Local invocations remain available for ad-hoc runs and pre-release
sweeps:

```bash
./scripts/verify-phase05.sh --post   # static + V1-V20 + live + post checks
```

`--post` is the canonical command to run before declaring Phase 5
complete, and before tagging a later phase's release.

Other modes:

```bash
./scripts/verify-phase05.sh              # static checks (= --fast)
./scripts/verify-phase05.sh --fast       # static checks only (CI)
./scripts/verify-phase05.sh --python     # + tests, parity, docs, builds
./scripts/verify-phase05.sh --node       # site, TS client, Worker, Inspector
./scripts/verify-phase05.sh --container  # image build, scan, smoke
./scripts/verify-phase05.sh --security   # gate, licences, audits, headers
./scripts/verify-phase05.sh --live       # GitHub, edges, registries, vendors
./scripts/verify-phase05.sh --all        # all but --live and --post
```

The script reports each V-check by id (V1.1, V2.1, …) so a failure in any
workflow above maps directly to the corresponding row below.

### V1 — Launch baseline and carried fixes

> **Automated in CI.** `phase-verify.yml` → V1.1; `ci.yml` → V1.2;
> `--live` → V1.3.

| ID | Check | Run by |
| --- | --- | --- |
| V1.1 | Step 1's static checks pass | `--fast` |
| V1.2 | The portability test and check 16's twin pass | `--python` |
| V1.3 | #210–#213 and #217 closed; staging at latest | `--live` |

### V2 — ADR-0013

> **Automated in CI.** `phase-verify.yml` → V2.1 and V2.2.

| ID | Check | Run by |
| --- | --- | --- |
| V2.1 | ADR-0013 Accepted and indexed; parent amended | `--fast` |
| V2.2 | AGENTS.md's layout and web rules present | `--fast` |

### V3 — Web foundation

> **Automated in CI.** `phase-verify.yml` → V3.1 and V3.3; `ci.yml` web
> job → V3.2.

| ID | Check | Run by |
| --- | --- | --- |
| V3.1 | Step 3's static checks pass | `--fast` |
| V3.2 | Build, headers, lint, tests, axe, Lighthouse pass | `--node` |
| V3.3 | npm audit and the bundle licence check clean | `--security` |

### V4 — Staging site

> **Automated in CI.** `phase-verify.yml` → V4.1; `ci.yml` → V4.2;
> `deploy-staging.yml` and `staging-health.yml`, read by `--live` → V4.3.

| ID | Check | Run by |
| --- | --- | --- |
| V4.1 | Step 4's static checks pass | `--fast` |
| V4.2 | The edge Worker's tests pass | `--node` |
| V4.3 | Staging site: SHA, headers, API; Access refuses | `--live` |

### V5 — Generated model pages

> **Automated in CI.** `phase-verify.yml` → V5.1; `ci.yml` web job → V5.2
> and V5.3.

| ID | Check | Run by |
| --- | --- | --- |
| V5.1 | Step 5's static checks pass | `--fast` |
| V5.2 | Pages, problems, links and JSON-LD tests pass | `--node` |
| V5.3 | The released-page ledger holds | `--node` |

### V6 — Calculators and web parity

> **Automated in CI.** `phase-verify.yml` → V6.1; `ci.yml` web job → V6.2
> and V6.3; `--live` → V6.4.

| ID | Check | Run by |
| --- | --- | --- |
| V6.1 | Step 6's static checks pass | `--fast` |
| V6.2 | Forms, figure equality and snippets pass | `--node` |
| V6.3 | 354 golden cases return the API's bytes | `--node` |
| V6.4 | check_deployed.py passes on production | `--live` |

### V7 — Navigation, search and coverage

> **Automated in CI.** `phase-verify.yml` → V7.1; `ci.yml` → V7.2 and
> V7.3.

| ID | Check | Run by |
| --- | --- | --- |
| V7.1 | Step 7's static checks pass | `--fast` |
| V7.2 | Search, filters, seed and coverage tests pass | `--node` |
| V7.3 | No mark in a URL; docs cards show seed tags | `--python` |

### V8 — Snapshot data plane

> **Automated in CI.** `phase-verify.yml` → V8.1; `ci.yml` → V8.2;
> `--live` → V8.3.

| ID | Check | Run by |
| --- | --- | --- |
| V8.1 | Step 8's static checks pass | `--fast` |
| V8.2 | Snapshot suites and the new problem row pass | `--python` |
| V8.3 | Staging and production series from snapshots | `--live` |

### V9 — Data explorer and user data

> **Automated in CI.** `phase-verify.yml` → V9.1; `ci.yml` → V9.2 and
> V9.3.

| ID | Check | Run by |
| --- | --- | --- |
| V9.1 | Step 9's static checks pass | `--fast` |
| V9.2 | Transforms equal on four surfaces | `--python` |
| V9.3 | The network-log and no-body tests pass | `--node` |

### V10 — Local app

> **Automated in CI.** `phase-verify.yml` → V10.1; `ci.yml` tests and
> package jobs → V10.2 and V10.3.

| ID | Check | Run by |
| --- | --- | --- |
| V10.1 | Step 10's static checks pass | `--fast` |
| V10.2 | Site-mount tests pass; both distributions check | `--python` |
| V10.3 | `[app]` from the built wheels serves the site | `--python` |

### V11 — Documentation guides

> **Automated in CI.** `phase-verify.yml` → V11.1; `ci.yml` docs job →
> V11.2.

| ID | Check | Run by |
| --- | --- | --- |
| V11.1 | Step 11's static checks pass | `--fast` |
| V11.2 | Docs build, Sybil and the migration test pass | `--python` |

### V12 — Documentation learning content

> **Automated in CI.** `phase-verify.yml` → V12.1; `ci.yml` docs job →
> V12.2.

| ID | Check | Run by |
| --- | --- | --- |
| V12.1 | Step 12's static checks pass | `--fast` |
| V12.2 | Gallery runs; in-browser examples render | `--python` |

### V13 — Production platform

> **Automated in CI.** `phase-verify.yml` → V13.1;
> `deploy-production.yml`, read by `--live` → V13.2 and V13.3.

| ID | Check | Run by |
| --- | --- | --- |
| V13.1 | Step 13's static checks pass | `--fast` |
| V13.2 | Newest production deploy green in every job | `--live` |
| V13.3 | Production: SHA, headers, runs, snapshots, MCP | `--live` |

### V14 — Observability and operations

> **Automated in CI.** `phase-verify.yml` → V14.1; `ci.yml` → V14.2;
> `production-health.yml` and the vendors, read by `--live` → V14.3.

| ID | Check | Run by |
| --- | --- | --- |
| V14.1 | Step 14's static checks pass | `--fast` |
| V14.2 | The telemetry canary passes | `--python` |
| V14.3 | Monitors up; probes green; alarm proofs logged | `--live` |

### V15 — Growth signals

> **Automated in CI.** `phase-verify.yml` → V15.1; `ci.yml` web job →
> V15.2; `growth-metrics.yml`, read by `--live` → V15.3.

| ID | Check | Run by |
| --- | --- | --- |
| V15.1 | Step 15's static checks pass | `--fast` |
| V15.2 | The event allowlist and form tests pass | `--node` |
| V15.3 | The newest ledger comment holds every count | `--live` |

### V16 — Legal, trust and brand

> **Automated in CI.** `phase-verify.yml` → V16.1; `ci.yml` web job →
> V16.2; `--live` → V16.3.

| ID | Check | Run by |
| --- | --- | --- |
| V16.1 | Step 16's static checks pass | `--fast` |
| V16.2 | Data-flows, security.txt, attribution tests | `--node` |
| V16.3 | The legal pages answer on production | `--live` |

### V17 — Release candidate

> **Automated in CI.** `phase-verify.yml` → V17.1; `ci.yml` → V17.2;
> `--live` → V17.3.

| ID | Check | Run by |
| --- | --- | --- |
| V17.1 | Step 17's static checks pass | `--fast` |
| V17.2 | The public-API test passes | `--python` |
| V17.3 | rc1.dev1 and rc1 published with provenances | `--live` |

### V18 — Launch readiness gate

> **Automated in CI.** `phase-verify.yml` → V18.1; `--live` → V18.2.

| ID | Check | Run by |
| --- | --- | --- |
| V18.1 | The record: sixteen sections and a GO | `--fast` |
| V18.2 | The newest ZAP baseline found no High issue | `--live` |

### V19 — Cutover and 1.0.0

> **Automated in CI.** `phase-verify.yml` → V19.1; `--live` → V19.2;
> `--post` → V19.3.

| ID | Check | Run by |
| --- | --- | --- |
| V19.1 | Step 19's static checks pass | `--fast` |
| V19.2 | 1.0.0 on PyPI; registry remote; RTD stable 1.0 | `--live` |
| V19.3 | Clean installs, serve, MCP and launch checks | `--post` |

### V20 — CI integration + security

> **Automated in CI.** `phase-verify.yml` → V20.1 through V20.4 and the
> `01`–`04` entries behind V20.6 on every push/PR; `--post` → V20.5 and
> V20.6; `--live` → V20.7 and V20.8.

| ID | Check | Run by |
| --- | --- | --- |
| V20.1 | `verify-phase05.sh --fast` exits 0 on Ubuntu CI | `--fast` |
| V20.2 | `phase-verify.yml` matrix includes `05` | `--fast` |
| V20.3 | All static checks pass | `--fast` |
| V20.4 | `--security` exits 0 | `--security` |
| V20.5 | Alarm proofs and the public re-fire recorded | `--post` |
| V20.6 | Phases 1–4 green; their `--post` passes | `--post` |
| V20.7 | `main` requires 26 strict checks | `--live` |
| V20.8 | Environments' refs and secrets; no repo secret | `--live` |

---

## Summary Table

| Step | Scope                          | Model          | Status             |
| ---- | ------------------------------ | -------------- | ------------------ |
| 1    | Launch baseline, fixes         | GPT-6.1 Sol    | Complete — PR #219 |
| 2    | ADR-0013                       | Opus 5.5       | Not started        |
| 3    | Web foundation                 | Gemini 4 Argon | Not started        |
| 4    | Staging site                   | Sonnet 5.5     | Not started        |
| 5    | Generated model pages          | GPT-6.1 Sol    | Not started        |
| 6    | Calculators + web parity       | Gemini 4 Argon | Not started        |
| 7    | Navigation, search, coverage   | GPT-6.1 Sol    | Not started        |
| 8    | Snapshot data plane            | Gemini 4 Argon | Not started        |
| 9    | Data explorer + user data      | Gemini 4 Argon | Not started        |
| 10   | Local app + app wheel          | Gemini 4 Argon | Not started        |
| 11   | Docs: guides + migration       | Gemini 4 Argon | Not started        |
| 12   | Docs: gallery, WASM, finance   | Gemini 4 Argon | Not started        |
| 13   | Production platform            | Sonnet 5.5     | Not started        |
| 14   | Observability + operations     | Sonnet 5.5     | Not started        |
| 15   | Growth signals (Gate G2)       | GPT-6.1 Sol    | Not started        |
| 16   | Legal, trust + brand           | Gemini 4 Argon | Not started        |
| 17   | API freeze, rc1 + soak         | Sonnet 5.5     | Not started        |
| 18   | Launch readiness gate          | Sonnet 5.5     | Not started        |
| 19   | Cutover + 1.0.0                | Sonnet 5.5     | Not started        |
| 20   | QA + verify-phase05.sh         | GPT-6.1 Sol    | Not started        |
| V1   | Baseline + carried fixes       | CI             | --                 |
| V2   | ADR-0013                       | CI             | --                 |
| V3   | Web foundation                 | CI             | --                 |
| V4   | Staging site                   | CI             | --                 |
| V5   | Model pages                    | CI             | --                 |
| V6   | Calculators + web parity       | CI             | --                 |
| V7   | Navigation + coverage          | CI             | --                 |
| V8   | Snapshots                      | CI             | --                 |
| V9   | Explorer + user data           | CI             | --                 |
| V10  | Local app                      | CI             | --                 |
| V11  | Docs guides                    | CI             | --                 |
| V12  | Docs learning content          | CI             | --                 |
| V13  | Production                     | CI             | --                 |
| V14  | Observability                  | CI             | --                 |
| V15  | Growth signals                 | CI             | --                 |
| V16  | Legal + trust                  | CI             | --                 |
| V17  | Release candidate              | CI             | --                 |
| V18  | Readiness gate                 | CI             | --                 |
| V19  | 1.0.0 + cutover                | CI             | --                 |
| V20  | CI integration                 | CI             | --                 |

---

## Model selection blocks

Each block restates the column its step's **Runs:** line names (Balanced,
the user context's budget priority); the step's own table holds the Cost
and Quality columns and the runners-up and backups the runner switches to
when a pool reads `tight` or `exhausted`.

```text
PROMPT: Step 1 — Launch Baseline and Carried Fixes
MODEL: GPT-6.1 Sol
BACKUP: Gemini 3.8 Flash
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — five small fixes in the
verifiers, the gate and the staging deploy path, and the version move.
PICK: the ladder's Balanced column for coding at Medium (AA Intelligence
Index 50.2). EFFORT: High, the ladder's value, because two fixes touch the
deploy path and must be proven by a real deploy.

PROMPT: Step 2 — ADR-0013: Web App, Hosting, Data Plane and Launch
MODEL: Opus 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: High
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: planning — twenty interacting decisions, several public
at 1.0.0. PICK: the ladder's Balanced column for planning at High (AA
Intelligence Index 53.6). EFFORT: High, the ladder's value; every decision
arrives with a drafted default and checked facts.

PROMPT: Step 3 — Web Foundation
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding — a new toolchain and the strict CSP every page
inherits. PICK: the ladder's Balanced column for coding at High (AA
Intelligence Index 52.6). EFFORT: High with thinking on, for the CSP's
interacting constraints.

PROMPT: Step 4 — Staging Site on Cloudflare
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic — Cloudflare and GitHub provisioning around a
Worker change and a deploy job. PICK: the ladder's Balanced column for
agentic at High (AA Intelligence Index 51.9). EFFORT: XHigh, the ladder's
value, for a new deploy credential and edge trust boundary.

PROMPT: Step 5 — Generated Model Pages
MODEL: GPT-6.1 Sol
BACKUP: Gemini 3.8 Flash
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding — templates and generators over a fixed registry.
PICK: the ladder's Balanced column for coding at Medium (AA Intelligence
Index 50.2). EFFORT: High, the ladder's value.

PROMPT: Step 6 — Calculators and Web Parity
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding — schema-driven forms over fifty schemas, a chart
port and a cross-language parity harness. PICK: the ladder's Balanced
column for coding at High (AA Intelligence Index 52.6). EFFORT: High with
thinking on, because a byte difference is what the step must catch.

PROMPT: Step 7 — Navigation, Search, Syllabus Seed and Coverage Matrix
MODEL: GPT-6.1 Sol
BACKUP: Gemini 3.8 Flash
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — navigation, search, a
small data format and a generated matrix. PICK: the ladder's Balanced
column for coding at Medium (AA Intelligence Index 50.2). EFFORT: High,
the ladder's value.

PROMPT: Step 8 — Hosted Data Plane: Snapshots
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — a data-layer store under the
licence and layering rules, plus staging provisioning. PICK: the ladder's
Balanced column for coding at High (AA Intelligence Index 52.6). EFFORT:
High with thinking on, for licensed data at rest and graceful degradation.

PROMPT: Step 9 — Data Explorer and User Data
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding — an explorer, a contract addition on four
surfaces and an in-browser file pipeline. PICK: the ladder's Balanced
column for coding at High (AA Intelligence Index 52.6). EFFORT: High with
thinking on, for untrusted files and the licence boundary.

PROMPT: Step 10 — Local App and the pyeconomics-app Wheel
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, agentic secondary — a second distribution, a
static mount and a two-project release pipeline. PICK: the ladder's
Balanced column for coding at High (AA Intelligence Index 52.6). EFFORT:
High with thinking on, because a packaging mistake becomes a permanent
upload.

PROMPT: Step 11 — Documentation: Tutorials, How-To Guides and Migration
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: knowledge, coding secondary — tutorials and guides with
executed examples and a migration guide tied to fixtures. PICK: the
ladder's Balanced column for knowledge at Medium (AA Intelligence Index
52.6). EFFORT: High, the ladder's value.

PROMPT: Step 12 — Documentation: Gallery, In-Browser Examples and
Finance Tutorials
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: knowledge, coding secondary — original finance tutorials,
an executed gallery and Pyodide notebooks. PICK: the ladder's Balanced
column for knowledge at Medium (AA Intelligence Index 52.6). EFFORT: High,
the ladder's value.

PROMPT: Step 13 — Production Platform
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — the phase's longest
provisioning run and a promotion workflow with rollback. PICK: the
ladder's Balanced column for agentic at High (AA Intelligence Index 51.9).
EFFORT: XHigh, the ladder's value, for the public service's trust
boundary and budget.

PROMPT: Step 14 — Observability and Operations
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — four vendor setups, alarm
injections and privacy-safe instrumentation. PICK: the ladder's Balanced
column for agentic at High (AA Intelligence Index 51.9). EFFORT: XHigh,
the ladder's value, because telemetry is a new path for data to leave.

PROMPT: Step 15 — Feedback Channels and Gate G2 Instrumentation
MODEL: GPT-6.1 Sol
BACKUP: Gemini 3.8 Flash
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: coding, knowledge secondary — static forms, a preview
page, an event allowlist and a weekly collector. PICK: the ladder's
Balanced column for coding at Medium (AA Intelligence Index 50.2). EFFORT:
High, the ladder's value.

PROMPT: Step 16 — Legal, Trust and Brand
MODEL: Gemini 4 Argon
BACKUP: GPT-6.1 Sol
PLATFORM: Antigravity
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: knowledge, coding secondary — legal texts that must
match the data flows and terms, letters and generated pages. PICK: the
ladder's Balanced column for knowledge at High (AA Intelligence Index
52.6). EFFORT: High with thinking on; counsel reviews the result.

PROMPT: Step 17 — Public-API Freeze, Release Candidate and Production Soak
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, coding secondary — a release run across four
registries and production around an inventory test. PICK: the ladder's
Balanced column for agentic at High (AA Intelligence Index 51.9). EFFORT:
XHigh, the ladder's value, because every upload is permanent.

PROMPT: Step 18 — Launch Readiness Gate
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, knowledge secondary — evidence across every
surface, three production rollbacks and a load test. PICK: the ladder's
Balanced column for agentic at High (AA Intelligence Index 51.9). EFFORT:
XHigh, the ladder's value, for a gate before an irreversible launch.

PROMPT: Step 19 — Cutover and the 1.0.0 Release
MODEL: Sonnet 5.5
BACKUP: Gemini 4 Argon
PLATFORM: Claude Code
EFFORT: XHigh
ORCHESTRATION: None
CONVERSATION: New
RATIONALE: TASK: agentic, knowledge secondary — the stable release, the
cutover and the post-launch verification. PICK: the ladder's Balanced
column for agentic at High (AA Intelligence Index 51.9). EFFORT: XHigh,
the ladder's value, for actions that cannot be undone.

PROMPT: Step 20 — QA and Verification Script
MODEL: GPT-6.1 Sol
BACKUP: Gemini 3.8 Flash
PLATFORM: Codex
EFFORT: High
THINKING: On
CONVERSATION: New
RATIONALE: TASK: mechanical translation of the prior verify-script
template into this phase's deliverables, plus the alarm re-fire. PICK:
known pattern, no novel reasoning — the ladder's Balanced column for coding
at Medium (AA Intelligence Index 50.2). EFFORT: High, the ladder's value.
```

---

## Not in scope (from product roadmap)

The parent ROADMAP's Phase 5 section has no list of its own; every item
below is deferred by its phase boundaries and its §6 "Out of Scope"
([`docs/roadmap/ROADMAP.md`](ROADMAP.md)):

- Bring-your-own-key vendors, the Bloomberg provider, the OpenBB bridge,
  the local app's key settings page and affiliate links in the provider
  docs. Phase 6 builds them, and none reaches the hosted site.
- New models, the other syllabi (FRM, CAIA, CIPM, CMT, CQF) and the rest
  of the coverage matrix, the worked-example generator and study paths
  beyond the seed. Phase 7 owns them; this phase adds no model id.
- Accounts, API keys, quotas and paid plans, a merchant of record, remote
  MCP with OAuth, the AI narrative in hosted mode, the Excel add-in,
  `pyeconomics-pro` and any study product. Phase 8 owns them, behind Gate
  G3; the Pro page here sells nothing.
- Real-time streaming quotes, tick and intraday data, licensed-data
  redistribution, personalised advice, exam-prep content, native apps and
  localisation, which stay excluded in every phase (ROADMAP §6).

Additionally not in scope for this phase:

- Live data in the browser: HttpTransport and the cache under Pyodide (#114,
  #116) and proxy support (#113). The in-browser examples and the xlwings
  Lite guide use data-free models and the reader's own values; the issues
  keep a named owner in `docs/phase05-qa-findings.md`.
- #197, the MCP tool list's size: a compatible 1.x change under decision 17
  unless the maintainer pulls it into Step 17.
- TypeScript 7 (Dependabot #187) in either Node project, until `astro check`
  supports it.
- A shared Redis-backed result cache, per-PR preview deployments, a second
  alarm channel beyond decision 15's, server-side rendering and Next.js
  (ADR-0006), and a CDN for the documentation beyond Read the Docs.
- Issues #52, #62, #68 (GitHub Sponsors), #109, #110 and #184, the
  randomized property failures (#112, #137, #139, #143, #149, #152), the
  data-layer gaps (#131, #135, #136, #141, #142), #148, #150 and #194,
  #151, the Wheel-rule markers (#154, #182), the statsmodels and data
  findings (#155, #156, #158, #159), #163, #164, #174, and the gated live
  binds #195 and #196. Each keeps the owner `docs/phase04-qa-findings.md`
  gives it; this phase absorbs only #210, #211, #212, #213 and #217 (Step
  1).

Carried over during execution — the Triage rule's carry-over checklist:
each upstream gap or deferred finding, the step whose `<task>` was
patched, and the step or phase that owns it. Phase 6 and Phase 7's
roadmaps carry forward whatever is still open here.

- From Phase 4's Not-in-scope list, its QA findings and its closing line,
  absorbed by this roadmap:
  - the production API, its protected `production` environment, the
    scheduled snapshot job replacing staging's per-request fetch
    (ADR-0012 decision 11), the hosted web app, the data explorer, the
    `[app]` wheel behind `pyeconomics serve`, the production MCP endpoint
    and its remote MCP Registry entry (decision 16), Sentry,
    OpenTelemetry and uptime monitoring, the legal and trust pages, the
    permissions programme and resolvable problem-type URIs (decision 4) —
    Steps 3 to 19;
  - production caching, which Phase 4 left to this phase — decision 7;
  - the public-API freeze Phase 4's Public-API rule assigned here — Step
    17;
  - the TypeScript client, generated by the web project from the same
    `openapi.json` (publishing it waits for Phase 8's API keys) — Step 3;
  - #210 and #211, "before Phase 5 repeats the setup for production",
    #212 (actionlint) and #213 (check 16 on Windows) — Step 1;
  - #217, found by the unattended `/roadmap-refresh` of 2026-10-29 — Step
    1;
  - #113, #114 and #116, marked "Phase 5 browser scope" in Phase 4's
    pre-ship table — kept out, as the second list above says, with the
    limitation stated in Steps 11 and 12;
  - Phase 3's V6.3 needs a providers-live success within eight days of a
    Phase 3 `--post` — Step 20 dispatches one before its canonical run.

---

_This roadmap is the execution plan for Phase 5. Each step's
`**Status:**` line is flipped by that step's own PR (Status rule), so this
file on `main` is the phase's ledger — `grep -n '^\*\*Status:\*\*'`
reports progress. After all steps and verification pass, and every finding
has a destination, Phase 5 is complete — declared with the line "Phase 5 is
complete. You can now move on to Phase 6." and nothing after it — and
Phase 6 (Premium Data: Bloomberg & BYOK Providers), with Phase 7 (Catalog
Completion: CFA Program & Beyond) beside it in parallel, inherits
`pyeconomics 1.0.0` on PyPI with `pyeconomics-app`: a public API frozen
under ADR-0003; a public site at `pyeconomics.dev` whose model pages,
calculators, search, coverage matrix and explorer are generated from the
registry and the catalog, so new models and providers appear with no web
code; the same site locally through `pyeconomics serve`; a snapshot data
plane that grows with each hosted-safe source; production on Cloud Run
behind Cloudflare with a tag-driven, staged deploy, error tracking,
telemetry, uptime monitors and proven alarms; the parity suite with its web
surface; the 1.0 documentation on Read the Docs `stable`; the legal pages
and the permissions programme; and a Gate G3 window, opened by the
announcement, whose instruments record the evidence Phase 8 waits for._
