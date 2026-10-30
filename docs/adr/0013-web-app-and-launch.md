# ADR-0013: Web app, hosting, data plane and launch

- Status: Accepted
- Date: 2026-10-29
- Deciders: Nathan Ramos, CFA (maintainer)
- Parent: ROADMAP §4 5.1–5.10; §5 "Release & deployment strategy",
  "Security & privacy strategy", "Operations & observability strategy",
  "Data licensing policy", "Legal & brand guardrails" and "Monetization
  strategy & validation gates"

## Context and problem

Phase 5 opens pyeconomics to the public. It builds a static site with a
page and a calculator for every model, navigation, search, a coverage
matrix, a data explorer and in-browser handling of users' files; serves the
same site locally through `pyeconomics serve`; replaces staging's
per-request fetches with a scheduled snapshot data plane; stands up
production on Cloud Run behind Cloudflare with error tracking, telemetry,
uptime checks and a status page; adds a newsletter, a waitlist, analytics
and a priced "Pro" page that sells nothing; publishes the legal and trust
pages; and releases 1.0.0 after a production soak. Phases 6 and 7 build on
what it fixes, and Gate G3 counts from its announcement.

Seven earlier decisions constrain the answer:

- **ADR-0006** chose Astro static output with React islands, Tailwind and
  shadcn/ui, the site on Cloudflare (Workers static assets unless a reason
  to stay on Pages), FastAPI on Cloud Run, and no Worker code in the page
  path "unless a later ADR adds it".
- **ADR-0012** fixed the surfaces the site calls: one invocation path, the
  canonical bytes, the error table whose problem `type` URIs name
  `https://pyeconomics.dev/problems/<slug>`, the `GET` form, the weak
  `ETag` and `Cache-Control` of a run, hosted mode, and the staging Worker
  (decision 20). Its decision 11 left hosted series to Phase 5's snapshot
  reader, and decision 16 left the MCP Registry's remote entry to Phase 5's
  production endpoint.
- **ADR-0003** makes 1.0.0 the first stable public API, ends 0.2.x at
  1.0.0, and lists what is public. This record adds the site's page URLs to
  that list.
- **ADR-0002** puts the built site in a `pyeconomics-app` wheel behind
  `[app]`, versioned in lockstep and outside `[all]`.
- **ADR-0005** lets the hosted service serve only `hosted-safe` and
  `user-supplied` data, from snapshots of originators, never an aggregator,
  and never as a clone of a provider's product.
- **ADR-0007** keeps the documentation on Sphinx and Read the Docs, with
  marimo's WebAssembly export for in-browser examples, and moves `stable`
  to 1.0 at the cutover.
- **ADR-0009** registered the four domains, left the canonical one to Phase
  5, keeps `.io` defensive, and asks for a clearance search before launch.

Several of this phase's choices become public API or public promises at
1.0.0 and cannot be taken back after the launch: the domain, the page URLs,
the problem URIs and what the privacy policy says. Twenty build steps would
otherwise each pick their own host, headers, vendors and data flows, and
the privacy policy (Step 16) would have nothing fixed to be checked
against.

The facts the decisions rest on, re-read on 2026-10-29:

- **Cloudflare.** Requests to Workers static assets are free and unlimited
  [S1]. A Free-plan Worker serves 100,000 requests a day; past that, the
  paths it runs first on answer 429 [S1][S2]. `run_worker_first` takes up
  to 100 path patterns [S3]. `_headers` and `_redirects` apply to asset
  responses only; `_headers` holds at most 100 rules of 2,000 characters a
  line [S4]. The Free plan has one rate-limiting rule (path and verified-bot
  fields, counted by IP, a 10-second period and timeout) [S5], ten Single
  Redirect, Cache and Transform rules, and the Free Managed Ruleset on by
  default [S6]. A Worker's `fetch()` to an outside origin reads through its
  zone's cache, and a Cache Rule applies when it matches the subrequest's
  URL; the Workers Cache API works on a custom domain [S7]. Cloudflare
  starts new projects on Workers, not Pages [S8]. Web Analytics records no
  custom events [S9]. Zero Trust's free plan has 50 seats, keeps Access
  logs up to 24 hours, and service tokens take no seat [S10]. Version
  URLs on `workers.dev` are public when enabled [S11].
- **Google Cloud.** Cloud Storage volume mounts are generally available for
  Cloud Run services and jobs, read-only or read-write per volume; FUSE
  has no file locking and the last write wins [S12]. Always Free covers 5
  GB-months of Standard storage across `us-west1`, `us-central1` and
  `us-east1`, and Google now recommends soft delete over Object Versioning
  [S13]. Cloud Scheduler gives three free jobs per billing account [S14].
  Cloud Run's request-based free tier is 180,000 vCPU-seconds, 360,000
  GiB-seconds and 2 million requests a month, and jobs have their own
  [S15]. An alerts-only budget never caps spending, but a spend-cap budget,
  generally available for Cloud Run since 2026-10-12, pauses Cloud Run in
  one project, with a delay and overages billed [S16]. Cloud Run's request
  logs record the full URL with its query, the client address and the user
  agent; the `_Default` bucket keeps them 30 days in the `global`
  location, and an exclusion filter drops them [S17].
- **Astro and the browser libraries.** Astro's `security.csp` is stable
  since Astro 6 and writes each page's script and style hashes into a
  `<meta>` element; only an adapter with `staticHeaders` sends a header,
  and the Cloudflare adapter has none; it supports neither the
  ClientRouter nor Shiki, and does not run in `astro dev` [S18]. A meta
  policy cannot carry `frame-ancestors` [S19]. Pagefind needs
  `'wasm-unsafe-eval'` and, with its worker, `worker-src 'self' blob:`
  [S23]. KaTeX can render MathML alone [S24]. Plotly.js runs without
  inline styles when `plotly.css` is loaded with its `no-inline-styles`
  marker, and only the `plotly.js` package ships that stylesheet [S25].
  RJSF 6 has a shadcn/ui theme and build-time precompiled validators that
  avoid `'unsafe-eval'` [S26]. `@astrojs/check` does not accept TypeScript
  7, and Node 24 has been in maintenance since 2026-10-20, to 2028-04-30
  [S20][S22]. Versions and licences: [S20][S21].
- **The vendors.** Umami Cloud's Hobby plan, Plausible, GoatCounter,
  Buttondown, Kit, Sentry's Developer plan, Grafana Cloud's free tier and
  Better Stack's free plan, as decisions 13–15 state them [S27]–[S37].
- **In the repository.** 50 models in 13 domains, each id
  `<domain>.<name>` in snake case with no hyphen; problem `type` URIs on
  `pyeconomics.dev` that nothing answers yet; `registry.json` and
  `openapi.json` exported deterministically; the staging Worker
  (`workers_dev` and `preview_urls` off), its Access application and its
  rate rule on `staging-api.pyeconomics.dev`; hosted mode's limits keyed
  by client address in Upstash Redis, in one-minute windows; the server's
  own logs holding route templates and problem records only; and
  `server.json` with one stdio package and no remote.

## Decision drivers

- **Licence first.** No library-only, `byok` or `premium-local` data
  reaches the hosted site, its snapshots or its downloads (ADR-0005).
- **No secret in the browser.** No key, token, internal hostname or origin
  address in the bundle, and one strict Content Security Policy that no
  vendor loosens.
- **Privacy by construction.** The least personal data, one processor per
  class, and every flow stated (what, who, where, how long) so the privacy
  policy can be checked against it line by line.
- **Generated, not written.** The site gains a model or a source only
  through the registry and the catalog, so Phases 6 and 7 need no web code.
- **Parity.** The canonical bytes stay the contract on the web.
- **Bounded cost.** About $0 a month at hobby scale beyond the email
  processor, a production budget of $10, and limits that fail closed
  rather than bill.
- **Stable names, chosen once.** What 1.0.0 freezes is decided here, before
  any step builds it (ADR-0003).
- **One operator.** The fewest vendors and moving parts, managed services,
  and every alarm with a runbook.

## Considered options

The overall choice:

1. **One origin, static first.** Workers static assets serve the
   prerendered site on `pyeconomics.dev`; one Worker runs only on the
   API's paths and forwards them to Cloud Run; a daily Cloud Run job writes
   snapshots to Cloud Storage; a few vendors' free or entry plans cover
   analytics, email, errors, telemetry and uptime.
2. **Two origins.** The site on `pyeconomics.dev`, the API on
   `api.pyeconomics.dev`. Rejected: every calculator run becomes a
   cross-origin request with CORS, the policy names a second origin, and
   two edges must be kept in step.
3. **A server-rendered site** (Astro on demand in a Worker or on Cloud
   Run). Rejected: it breaks ADR-0006's static rule, puts code in the page
   path, costs per page view, and cannot be the local app's offline site.

The alternatives behind each numbered decision:

| # | Chosen | Alternatives and why they lost |
|---|--------|--------------------------------|
| 1 | `pyeconomics.dev` canonical | `.com` canonical: the problem URIs already name `.dev` and would redirect for ever, and `.com` is not HSTS-preloaded. `.io`: never canonical (ADR-0009) |
| 2 | `/models/<domain>/<name>/`, hyphens, trailing slashes | Snake-case paths mirroring the ids: harder to read in a URL. Id-only paths (`/m/<id>/`): no domain sections |
| 3 | Workers static assets, one Worker on the API's paths | An `api.` subdomain: CORS. Cloudflare Pages: Cloudflare starts new projects on Workers [S8]. A Worker in the page path: ADR-0006 forbids it without need |
| 4 | Pull requests build only; staging is the preview; tags deploy production | Per-pull-request version URLs: public on `workers.dev` unless protected [S11], with no API behind them |
| 5 | Separate `pyeconomics-production` project | Production in the staging project: one blast radius, one budget, shared identities |
| 6 | Cloud Storage volume mount, canonical-JSON frames, runs named by id | Cloudflare R2 (the parent's plan): a long-lived access key and request-signing code. Parquet: a second parser on the hosted read path, and pyarrow stays optional (ADR-0008 decision 8). Object Versioning: Google recommends soft delete instead [S13], and run-named objects are never overwritten |
| 7 | Workers Cache API in the Worker | Zone Cache Rules matching the origin's URL [S7]: the caching logic would live in dashboard rules instead of the Worker's tested code. A shared result cache (Redis): cost and a new store for no measured need |
| 8 | RJSF 6 with the shadcn/ui theme, precompiled validators | Hand-written forms per field type: drift from the schemas. Validators compiled in the browser: need `'unsafe-eval'` [S26] |
| 9 | One header policy holding every page's hashes | A meta policy alone: cannot carry `frame-ancestors` [S19]. `'unsafe-inline'`: defeats the policy |
| 10 | Pagefind | Algolia DocSearch: a third-party origin and script. Lunr or Fuse: a whole index in every page's JavaScript |
| 11 | Catalog transforms through `data.get`; files parsed in a worker | Server-side upload: a stored user file. The npm `xlsx` package: frozen at 0.18.5 since 2022 [S45] |
| 12 | `syllabi/` seed now, the rest in Phase 7 | No filters until Phase 7: §4 5.3 asks for them now. Tags inside model metadata: curricula change yearly, so the mapping must be data |
| 13 | Umami Cloud Hobby | Umami Pro ($20 a month): adds the API the ledger could read. Plausible Starter ($9 a month): custom properties need Business ($19) [S29]. GoatCounter: free, but events carry no properties [S30]. Cloudflare Web Analytics: no custom events [S9], which Gate G2 needs |
| 14 | Buttondown Basic | Buttondown Free: no metadata or tags for new accounts, so no list or tier [S32]. Kit Free: free to 10,000, but open and click tracking show as on with no documented switch [S34] |
| 15 | Sentry, Grafana Cloud, Better Stack free plans | Google Cloud's Error Reporting and Monitoring only: no browser errors and no public status page. Self-hosting: one operator |
| 16 | `packages/pyeconomics-app/` workspace member | Site files inside the `pyeconomics` wheel: the wheel admits only `.py` files (Phase 1's allowlist), and every user would download the site |
| 17 | Inventory plus a test derived from the code | A hand-kept list: it drifts. No inventory: the freeze has nothing to compare against |
| 18 | One Trusted Publishing job for both distributions; a seven-day soak | Two release workflows: the versions can drift. No soak: the first real traffic meets an unproven production |
| 19 | Thirteen fixed pages; G3 over the 90 days after the announcement | Every page: slow and noisy in CI. A rolling window: the gate would never close |
| 20 | Every legal page live before launch; outside answers recorded, never awaited | Launch first, pages later: the data notices and disclaimers are conditions of use, not polish |

## Decision outcome

Chosen option: **1, one origin, static first**, because it keeps every page
a file a CDN serves for nothing, keeps the API on the origin the policy
already allows, keeps hosted data inside the licence boundary by reading
snapshots, and lets one person run the whole of it on free or entry plans.
The twenty decisions below are rules a later step follows as written; a
later step that needs a different rule writes a superseding ADR.

### 1. Canonical domain

- `pyeconomics.dev` serves the site, the API and the MCP endpoint on one
  origin.
- `www.pyeconomics.dev`, `pyeconomics.com`, `pyeconomics.org` and
  `pyeconomics.io` (with their `www.` names) answer 301 to the same path
  and query on `https://pyeconomics.dev`, through each zone's Single
  Redirects [S6], enabled at the cutover (Step 19). `.io` is never
  canonical (ADR-0009).
- The problem `type` URIs (`https://pyeconomics.dev/problems/<slug>`)
  become public API at 1.0.0 and resolve to the generated problem pages
  (decision 2).
- Rationale: the URIs already name `.dev`; the `.dev` TLD is
  HSTS-preloaded, so every request is HTTPS from the first [S44]; the name
  matches the `pyeconomics-dev` organization.

### 2. Site layout and URLs

- `web/` is an Astro project with its own Node project and lockfile beside
  `tools/node/`, the development-tooling workspace. Its build data comes
  only from `scripts/web/export_site_data.py`, which reads the registry
  export, the catalog and `syllabi/`.
- Pages, each with a trailing slash:
  - `/models/<domain>/<name>/`, from the model id `<domain>.<name>` with
    every underscore a hyphen. Ids hold no hyphen, so the mapping is a
    bijection: `fixed_income.bond_pricing` is
    `/models/fixed-income/bond-pricing/`.
  - `/models/` and `/models/<domain>/`, `/data/`, `/search/`,
    `/coverage/`, `/sources/`, `/problems/<slug>/`, `/legal/<page>/`,
    `/pro/`, `/newsletter/`, and `/version.json` (the build's version and
    SHA).
- No path segment or query value names a trademark (§5 "CFA Institute
  marks and content").
- A shipped page never disappears: `web/released-pages.json` lists every
  path a release served, a build fails when one goes missing, and a
  retired path redirects to its successor.
- Open Graph images are drawn at build time by `astro-og-canvas` (MIT)
  [S20].
- Rationale: readable, hyphenated paths grouped by domain and derived from
  the permanent ids (ADR-0003), so a page's URL is as permanent as its
  model.

### 3. One host, one Worker

- Workers static assets serve the built site.
- One Worker — ADR-0012 decision 20's, extended — runs first only on
  `/v1/*`, `/mcp`, `/healthz`, `/version` and `/openapi.json`
  (`run_worker_first` [S3]) and forwards those requests to Cloud Run with
  the edge credential. No Worker code runs for a page or an asset, so
  ADR-0006's rule holds.
- Same origin, so the API needs no CORS and the policy's `connect-src`
  names `'self'` for it.
- Asset requests are free and unlimited [S1]. The Worker's 100,000 free
  requests a day [S2] bound API traffic before the origin's limits do:
  past them the API's paths answer 429 while pages keep serving [S1].
- The Free plan's one rate-limiting rule matches the API's paths on every
  host, counted by IP over 10 seconds [S5]; the Free Managed Ruleset stays
  on [S6].
- Rationale: the cheapest and simplest edge that keeps pages static, the
  API same-origin and the free limits failing closed.

### 4. Environments

- Every pull request builds and tests the site; none deploys.
- Every merge to `main` deploys staging through `deploy-staging.yml`: the
  API first, then the site on `staging.pyeconomics.dev`, behind Cloudflare
  Access. Staging is ROADMAP §5's "preview".
  `staging-api.pyeconomics.dev` stays as staging's API-only edge.
- A release tag, approved in the protected `production` environment,
  deploys `pyeconomics.dev`. Production stays behind Access until Step 19
  removes it.
- Every Worker sets `workers_dev = false` and `preview_urls = false`,
  because version URLs on `workers.dev` are public [S11]. A site or Worker
  rollback is `wrangler rollback` to one of the last 100 versions [S11].
- Rationale: one preview that has the real API behind it and is never
  public.

### 5. Production on Google Cloud

- A separate project, `pyeconomics-production`, in `us-central1`.
- The service `pyeconomics-api`: 1 vCPU and 1 GiB, minimum 0 and maximum 3
  instances, request-based billing (CPU only during requests), concurrency
  8, which needs at least one vCPU [S15].
- Images are promoted from staging by digest, never rebuilt.
- Workload Identity Federation bound to the repository id, the
  `production` environment and the `main` or `v*` refs; the deploy
  identity holds `roles/run.developer` on the service alone (#211), and a
  deploy restores latest traffic (#210).
- Production shares no secret with staging: its own Upstash database, edge
  credential, Access service token and Cloudflare API token.
- **Budget.** A $10 monthly alerts-only budget with alerts at 50, 90 and
  100% of actual spend to email and Pub/Sub, and a spend-cap budget at $20
  a month that pauses Cloud Run (the service and the snapshot job) in the
  project until the maintainer lifts it [S16]. The maximum instance count
  alone does not bound cost, because Cloud Run may exceed it briefly
  [S15]; at three busy instances a month would cost far more than the
  budget. When the cap pauses Cloud Run, the pages, the documentation and
  PyPI stay up; only the API and the snapshot job stop.
- **Logs.** The service's own logs hold route templates, status,
  durations and problem records, never a path, query, body or key
  (ADR-0012). An exclusion filter on the `_Default` sink drops Cloud Run's
  automatic request logs, which would record each URL with its query
  (including a `GET` run's `?inputs=`), the user agent and the client
  address [S17]. What remains is kept 30 days in the `_Default` bucket's
  `global` location [S17].
- Rationale: one blast radius per environment, the staging pattern Phase 5
  Step 1 corrected, a hard ceiling on the cost of a flood, and no request
  URL in a log.

### 6. Snapshot data plane

- A Cloud Run job — the same image, in hosted mode — runs daily at 23:30
  UTC, after the US end-of-day series publish, from Cloud Scheduler [S14].
  It runs one task at a time and never overlaps itself, so the bucket has
  one writer: Cloud Storage FUSE has no file locking and the last write
  wins [S12].
- Each run writes one gzip-compressed canonical-JSON object per provider,
  in the cache's frame codec (ADR-0011 decision 14), under its own run id,
  and never overwrites an object; then it writes `current.json` last,
  naming the run each provider is served from. A provider whose fetch
  fails keeps its last good run in `current.json`.
- The bucket is private, in `us-central1`, with soft delete at Google's
  default and no Object Versioning, which Google no longer recommends and
  which run-named objects do not need [S13]. The job deletes a run older
  than 30 days that `current.json` no longer names. Rolling back is
  pointing `current.json` at an earlier run.
- The bucket is mounted read-write into the job and read-only into the
  service [S12], so no key, no request signing and no network code exists
  outside `data/transport/`. The reader is a data-layer module that reads
  files (it joins `IO_MODULES`) and validates every frame it reads.
- The set is computed from the catalog: every candidate of a
  `hosted-safe` originator whose terms allow storage. Never FRED or ALFRED,
  an aggregator, a library-only source or a storage-forbidden series.
- A series outside the set is refused with `not-in-snapshot` (404, a new
  error-table row), pointing to local mode. A snapshot older than two days
  is served with a `stale_snapshot` warning; the service never falls back
  to a live fetch.
- Rationale: the job keeps the hosted service inside every provider's
  rate limits and licence (ADR-0005 rule 3), a mount needs no credential,
  and Always Free covers the storage [S13].

### 7. Caching

- The Worker caches `GET` run responses with the Workers Cache API, for as
  long as the origin's `Cache-Control` allows (ADR-0012 decision 12: long
  for runs that read no data, short for bound runs on storable hosted-safe
  data).
- `POST` runs and every problem stay `no-store` and are never cached.
- `/_astro/*` assets are immutable (`max-age=31536000, immutable`); HTML
  revalidates.
- No shared result cache: the in-process cache and the edge suffice at this
  scale.
- Rationale: a zone Cache Rule could also cache the Worker's subrequest,
  when it matches the origin's URL [S7], but the Cache API keeps the rule
  in the Worker's own tested code, the same on staging and production,
  instead of in dashboard settings.

### 8. Calculators

- RJSF 6 with its shadcn/ui theme renders each model's own input schema
  [S26]. Validators are precompiled at build time, so nothing is compiled
  in the browser and the policy needs no `'unsafe-eval'`.
- The island posts the inputs' JSON to the run route and renders the
  canonical bytes it receives; a table and a chart go beside them.
- Charts come from a TypeScript port of `figure_of`, held equal to each
  model's `example_figure`, on Plotly.js's basic bundle at the version the
  `[plot]` extra bundles (4.1.1) [S21]. Both the bundle and `plotly.css`
  come from the `plotly.js` package's `dist/`, because the
  `plotly.js-basic-dist-min` package ships no stylesheet [S25].
- Downloads use the API's `?format=`. Snippets for Python, the CLI, curl
  and MCP are generated and run in CI.
- The web joins the parity evidence: every golden case through the
  island's request builder, and `scripts/parity/check_deployed.py` through
  a deployed API.

### 9. Security headers

- One policy for every page, sent from `_headers` and by the local server:

  ```text
  default-src 'self';
  script-src 'self' 'wasm-unsafe-eval' <every page's script hashes>;
  style-src 'self' <every page's style hashes>;
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self' https://gateway.umami.is <Sentry's ingest origin>;
  worker-src 'self' blob:;
  form-action 'self' https://buttondown.com;
  frame-ancestors 'none';
  base-uri 'none';
  object-src 'none';
  upgrade-insecure-requests
  ```

- Astro's `security.csp` writes each page's script and style hashes into
  a `<meta>` policy, and only an adapter with `staticHeaders` can send them
  as a header; the Cloudflare adapter has none [S18]. A post-build step
  therefore reads every page's hashes and writes their union into the one
  header policy in `_headers`, which alone can carry `frame-ancestors`
  [S19]. Each page keeps its meta policy as well; a browser enforces both,
  so a page runs only its own hashed code. A `_headers` line holds at most
  2,000 characters [S4], so the build keeps inlined code to Astro's island
  runtime and fails when the policy line would exceed the limit.
- Beside it: `Strict-Transport-Security: max-age=63072000;
  includeSubDomains; preload`, above the preload list's one-year minimum
  [S44], `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  strict-origin-when-cross-origin`, a `Permissions-Policy` denying every
  feature the site does not use, and `Cross-Origin-Opener-Policy:
  same-origin`.
- No `'unsafe-inline'` and no `'unsafe-eval'`. KaTeX renders MathML only,
  at build time [S24], and the post-build check fails on any inline
  `style` attribute. Plotly.js loads `plotly.css`, with its
  `no-inline-styles` marker element in the page before the library loads,
  instead of injecting styles [S25]. RJSF's validators are precompiled
  (decision 8) [S26]. The site uses neither the ClientRouter nor Shiki,
  which Astro's policy does not support [S18]; code samples use Astro's
  `<Prism />`. `'wasm-unsafe-eval'` is the one concession, for Pagefind,
  whose worker also needs `worker-src 'self' blob:` [S23].
- Every script is built from `web/` or is the analytics tracker (decision
  13), served from our origin.
- Verified by a post-build check, a Playwright listener that fails on any
  CSP violation, and, once the site is public, the MDN HTTP Observatory at
  grade A or better, which rewards a policy with no unsafe source and a
  preloaded HSTS [S39].

### 10. Search and navigation

- Pagefind (MIT) indexes the built site and searches in the browser [S23].
- Fifteen domain sections in ROADMAP §4 7.2's order; `micro` and
  `alternatives` are planned sections that link the coverage matrix.
- Filters by domain, syllabus level and topic, evidence status, cost
  class, data needs and tag. Related models are computed at build time.

### 11. Data explorer and user data

- `/data/` lists the catalog's concepts with each source's licence class
  and hosted availability, reads series through `/v1/series/`, draws the
  attribution and as-of date on every chart, and downloads through
  `?format=`.
- Transforms are the catalog's own single-series transforms, through a new
  `transform` option on `data.get` passed through the CLI, the REST route
  and MCP's `get_series`, so a transformed file carries the same
  attribution.
- Hosted mode offers only the snapshot set. The explorer feeds models and
  never replicates a provider's product (ADR-0005 rule 5).
- Users' files: CSV through Papa Parse and XLSX through a maintained,
  permissively licensed reader chosen at Step 9's kickoff (on 2026-10-29,
  `read-excel-file` 9.3.14, MIT, was current [S20]), never the npm `xlsx`
  package, frozen at 0.18.5 [S45]; parsed in a Web Worker; capped at 5 MB
  and at each field's `max_length`; and sent only as run values, in a
  run's body.

### 12. Syllabus seed and coverage matrix

- ROADMAP §4 5.3 asks for syllabus filters, and §4 7.1 creates the
  crosswalks. This phase creates `syllabi/` in 7.1's format: a JSON Schema
  and one TOML file per syllabus version.
- One seed: the 2027 CFA® Program topic areas for Levels I to III, mapped
  to the launch catalog's entries, holding factual names and links to
  cfainstitute.org only — no learning-outcome wording — and reviewed by the
  maintainer.
- Slugs and query values stay neutral (no mark) until CFA Institute
  answers the URL question (decision 20).
- The coverage matrix is generated from the registry and `syllabi/`.
  Phase 7 adds the other syllabi and the remaining coverage.

### 13. Analytics

- Umami Cloud's free Hobby plan: 100,000 events a month, one website,
  custom events and event properties, and six months' retention; no API
  access on Hobby [S27].
- Its EU region, chosen at sign-up and fixed thereafter [S27]. Umami's
  DPA applies without a signature [S28].
- No cookies [S28]. The vendor's pricing page says no cookie banner is
  needed, while its documentation says that depends on the site's setup
  [S27][S28]; counsel confirms the site needs none (decision 20).
- The tracker is downloaded at a pinned version and served from our
  origin, posting to `https://gateway.umami.is` through `data-host-url`
  [S28]. Production builds only; staging and local mode load no tracker.
- Custom events come from a fixed allowlist; a property never holds an
  input, a value, a query or an address. The tracker excludes query
  strings and fragments.
- Without an API on Hobby, the weekly ledger's analytics rows read
  "manual" and the maintainer adds them (Step 15). Umami Pro ($20 a
  month) adds the API if the manual rows become a burden.
- Personal data: see "Personal data" below.

### 14. Email processor

- One processor for the newsletter and the waitlist: Buttondown, on its
  Basic plan ($9 a month to 1,000 subscribers; $29 to 5,000) [S31],
  because subscriber metadata, which records the list and tier interest,
  needs Basic for accounts opened since April 2026 [S32].
- Plain HTML forms post straight to Buttondown's embed endpoint
  (`https://buttondown.com/api/emails/embed-subscribe/<username>`) by
  form navigation, never by `fetch`, because the response can hold a
  CAPTCHA; with no key; with `metadata__list`, `metadata__source` and, on
  the waitlist, `metadata__tier` [S32].
- Double opt-in, which Buttondown requires for signup forms [S32]. Open
  and click tracking, both opt-in, stay off [S32].
- No list, address or export passes through pyeconomics' own systems,
  logs or analytics. The maintainer holds the only account, with
  two-factor authentication, and accepts Buttondown's DPA when opening it
  [S33].
- Personal data: see "Personal data" below.

### 15. Errors, telemetry and uptime

- **Errors**: Sentry's free Developer plan (5,000 errors a month, one
  user, 30 days' lookback) in its US region, fixed at sign-up; the
  maintainer accepts Sentry's DPA, which needs a click [S35].
  `sentry-sdk` on the backend and `@sentry/browser` in the islands only.
  The browser SDK 11 collects user details, the IP address, cookies,
  headers and bodies unless told not to [S35], so it is initialised with
  every `dataCollection` category off; the Python SDK leaves
  `send_default_pii` unset and passes no `data_collection` mapping, which
  would opt into broader defaults [S35]. A test asserts both
  initialisations. No session replay and no browser tracing.
- **Telemetry**: OpenTelemetry metrics and sampled traces to Grafana
  Cloud's free tier (10,000 active series, 14 days' retention) in a US
  region, fixed at sign-up [S36], through the project's own middleware
  (not the beta FastAPI instrumentation), flushed on shutdown. Attributes
  are route templates, outcomes and durations only. Step 14 confirms at
  its kickoff that the free tier takes OTLP.
- Both libraries come from a `hosted` dependency group the image installs,
  never an extra.
- **Uptime**: Better Stack's free plan (10 monitors and heartbeats,
  3-minute checks, one status page, email alerts) [S37] for the uptime
  monitors, the snapshot jobs' heartbeats (pinged through the data layer's
  transport, its host declared like a provider's) and the status page at
  `status.pyeconomics.dev`, a custom subdomain the free page allows [S37].
  Step 14 confirms at its kickoff whether a free monitor can send the
  Access service token's headers, and keeps its fallback otherwise.
- An hourly `production-health.yml` and the budget alerts complete the
  alarms, reaching the maintainer by email and by GitHub's notifications.
  Each alarm names its runbook in `docs/operations/production.md`.
- Personal data: see "Personal data" below.

### 16. Local app

- `packages/pyeconomics-app/` is a uv workspace member whose wheel carries
  only the built site.
- `[app]` pins it to the same version and stays out of `[all]`
  (ADR-0002).
- `pyeconomics serve` mounts the site at `/` behind the API's routes, with
  the same headers and the loopback guard unchanged.
- Locally, the site offers live library-only data on the user's own keys
  and the whole catalog; the local site loads no analytics and no error
  tracking.

### 17. Public-API freeze

- Step 17 inventories the public surface in `docs/public-api.md` — every
  item ADR-0003 lists, plus the site's page URLs and the problem URIs —
  and pins it with a test derived from the code.
- After 1.0.0, every change follows ADR-0003.
- #197, the MCP tool list's size, stays a compatible 1.x change (slimmer
  schemas that keep every tool name and its validation), unless the
  maintainer pulls it in before the freeze.

### 18. Release, soak and end of life

- `release.yml` publishes `pyeconomics` and `pyeconomics-app` through one
  Trusted Publishing exchange.
- The exact candidate is rehearsed on TestPyPI (`v1.0.0rc1.dev1`); then
  `1.0.0rc1` goes to PyPI and to production behind Access.
- The soak lasts seven days from production's deploy of the candidate.
  Only security fixes merge during it. It passes when there was no
  unexplained 5xx, the status page shows at least 99.5% uptime, every
  scheduled snapshot run was green, every Sentry issue was triaged,
  `production-health` stayed green, spend stayed inside the budget, and no
  Critical or High security finding is open.
- 1.0.0 follows the gate's GO; its archives differ from the candidate's
  only in version metadata, and its classifier is `Development Status :: 5
  - Production/Stable`. A NO-GO makes the next candidate `1.0.0rc2`.
- 0.2.x reaches end of life at 1.0.0: `legacy/0.2.x` is locked and
  `SECURITY.md` updated (ADR-0003).
- The MCP Registry gains a `streamable-http` remote entry beside the
  package once the endpoint is public, which `server.json` schema
  2025-12-11 supports [S38]. Read the Docs' default branch moves to `main`
  and its default version to `stable`, which serves 1.0.

### 19. Launch measures and growth gates

- **Web quality** on thirteen pages: `/`, `/models/`,
  `/models/fixed-income/`, `/models/fixed-income/bond-pricing/`,
  `/models/foundations/time-value/`, `/models/macro/policy-rule/`,
  `/models/econometrics/garch/`, `/data/`, `/search/`, `/coverage/`,
  `/sources/`, `/legal/privacy/` and `/problems/invalid-input/`.
  Lighthouse, the median of three mobile runs, scores at least 90 in all
  four categories; axe finds no WCAG 2.2 AA violation.
- **Security and load**: the OWASP ZAP baseline with no High finding
  [S40]; the MDN HTTP Observatory at A or better [S39]; a Locust load test
  against staging whose month at 10,000 runs a day fits the production
  budget.
- **Gate G2's signals**, written weekly as counts to a pinned "Gate G3
  ledger" issue: page views and the allowlisted events, sign-ups by list
  and tier, API and MCP requests by route kind, PyPI downloads and GitHub
  stars. Counts only; no address, identifier or input.
- **Gate G3's window**: the 90 days after the 1.0.0 announcement. Its
  thresholds are ROADMAP §5's: at least 1,000 waitlist or newsletter
  sign-ups, or 1,000 activated users (a visitor who completes a run or a
  download); and at least 30 upgrade-intent clicks or pre-orders; and at
  least 10 interviews in which users confirm they would pay. The
  maintainer confirms or adjusts them again at Step 18.

### 20. Legal readiness

- Live before launch: the terms of use (passing through the New York
  Fed's and the OECD's conditions); the privacy policy, generated from one
  data-flows file that a test holds equal to the processors and logs the
  service uses; the disclaimers, with FINRA Rule 2214's statement as the
  template for projections and CFTC Rule 4.41(b)(1)'s for simulated
  trading results [S41][S42]; the data-sources and licence pages;
  `security.txt` at `/.well-known/` with `Contact` and an `Expires` under
  a year away (RFC 9116) [S43]; and every chart's and file's attributions.
- The permissions letters go out — the St. Louis Fed, Ken French, Robert
  Shiller, the IMF, the Philadelphia, Atlanta and Cleveland Feds, and CFA
  Institute on URL paths — and no launch item waits for an answer. A grant
  is a reclassification in its own pull request (ADR-0005 rule 7).
- Counsel reviews the pages and the licensing policy before launch
  (ROADMAP §5), and the trademark clearance search is recorded in
  ADR-0009's executed record. At the readiness gate a missing outside item
  is a FAIL unless the maintainer waives it with a recorded reason.

### Personal data

Every flow the site and the service create, for Step 16's privacy policy
and its data-flows file to match line by line. Nothing here is sold,
shared for advertising or used to profile a visitor.

| Flow | What is collected | Who processes it | Where it is kept | How long | Decision |
|------|-------------------|------------------|------------------|----------|----------|
| Every request through the edge | The visitor's IP address, user agent and request, as the CDN, WAF and rate rule see them. pyeconomics sets no cookie and turns on no Logpush or Workers Logs | Cloudflare, under the DPA its self-serve agreement incorporates [S47] | Cloudflare's global network | Not stated for Free zones; its DPA keeps customer logs only while processing needs them [S47] | 3 |
| Staging and production behind Access | The maintainer's identity and the CI service token's use | Cloudflare Zero Trust [S47] | Cloudflare | Access logs up to 24 hours [S10] | 4 |
| API requests | The service's records: route template, status, duration, problem slug; never a path, query, body or key. Cloud Run's request log is excluded | Google Cloud (Cloud Run, Cloud Logging), under its Cloud Data Processing Addendum [S46] | Cloud Logging's `global` location | 30 days [S17] | 5 |
| Rate limits | A counter keyed by the client's address (IPv6 by /64) | Upstash (Redis) | A US region beside the service, chosen at Step 13 | The window, one minute | 5 |
| Run inputs, including values from a user's file | The values in a run's body, in memory for one run; never stored, cached or logged | Google Cloud (Cloud Run) | `us-central1`, in memory | The request | 8, 11 |
| Analytics | Page views and allowlisted events, the referrer, browser, operating system, device type, language, screen size and approximate location; no cookie, no input; the IP address used in passing for a visitor hash and location, not stored with the analytics, though it may reach the vendor's operational logs [S28] | Umami Software (Umami Cloud), under its DPA [S28] | Umami Cloud's EU region [S27] | Six months [S27] | 13 |
| Newsletter and waitlist | Email address, IP address, referrer, subscription and confirmation times, list, source and tier interest [S33] | Buttondown, under its DPA [S33] | The United States (AWS `us-west-2`) [S33] | Until the subscriber leaves or asks for deletion | 14 |
| Errors | Error type, stack trace, release and route; no IP address, user detail, cookie, header, body or input | Functional Software (Sentry), under its DPA [S35] | Sentry's US region; some account data always in the US [S35] | 30 days [S35] | 15 |
| Telemetry | Metrics and sampled traces of route templates, outcomes and durations; no personal data | Grafana Labs (Grafana Cloud) | A US region [S36] | 14 days [S36] | 15 |
| Uptime | The vendor's own synthetic requests and the jobs' heartbeats; no visitor data | Better Stack | The EU by default; its DPA allows transfer to the US [S37] | Recorded at Step 14 | 15 |
| Gate G3 ledger | Weekly counts only | GitHub (a pinned issue) | GitHub | Kept as a public record | 19 |

User files never leave the browser except as run values (decision 11).
The data-flows file Step 16 writes holds these rows; a vendor's figure
that changes is a change to that file and to the privacy policy in the
same pull request.

### Consequences

Good:

- Pages cost nothing to serve and need no server; the local app serves the
  same files.
- The API is same-origin: no CORS, one origin in the policy, one edge.
- Hosted data cannot leave the licence boundary: the reader serves only
  the computed snapshot set, and no credential exists to reach the bucket.
- One strict policy contains cross-site scripting through model text, user
  files or a vendor script; no vendor can loosen it.
- A flood cannot run up an unbounded bill: the Worker's daily limit, the
  rate rule, hosted mode's limits and the spend cap each stop it.
- Every personal-data flow is named before it exists, so the privacy policy
  is a check, not a guess.
- New models and sources reach the site with no web code.

Bad:

- Every page URL and problem URI becomes public API at 1.0.0; a retired
  page must redirect for ever.
- Free tiers bound the launch: the Worker's 100,000 requests a day and
  Umami's 100,000 events a month. Crossing one is a cost decision, not a
  code change, and each is watched through the ledger (decision 19).
- The email processor costs $9 a month from Step 15, and $29 once the list
  passes 1,000.
- The ledger's analytics rows are manual on Umami's Hobby plan.
- A spend cap that trips pauses the API until the maintainer lifts it.
- Five vendors beyond Google and Cloudflare (Umami, Buttondown, Sentry,
  Grafana Labs, Better Stack), each with an account, a DPA and terms to
  re-read; each region is fixed once chosen.
- Snapshots are at most a day old, and a source's outage shows as a stale
  warning, not fresh data.
- The policy rules out Astro features (the ClientRouter, Shiki) and inline
  styles in every dependency the site adopts, and Astro's policy does not
  run in `astro dev`, so it is tested on a built site.

### Confirmation

| Decision | Check | Built in |
|----------|-------|----------|
| 1 Canonical domain | The redirects and the problem pages answer through the edge; the Observatory and the preload status | Steps 5 and 19 |
| 2 Site layout and URLs | A build check that every model id maps to its page and back; the `web/released-pages.json` ledger | Steps 3 and 5 |
| 3 One host, one Worker | The Worker's tests (only the API's paths reach it); a request through the edge per path | Step 4 |
| 4 Environments | `deploy-staging.yml`'s site job; a pull request deploys nothing; `workers_dev` and `preview_urls` off; production behind Access | Steps 4 and 13 |
| 5 Production | Cloud Run settings, IAM, both budgets and the log exclusion read through the API; the budget alert fired once | Steps 13 and 14 |
| 6 Snapshot data plane | The licence test over the computed set; `not-in-snapshot` and `stale_snapshot` tests; one task, no overlap; the heartbeat | Steps 8 and 14 |
| 7 Caching | Worker cache tests; `Cache-Control` and `no-store` read back through the edge | Steps 4 and 13 |
| 8 Calculators | Web parity over every golden case; `check_deployed.py`; chart equality with `example_figure` | Step 6 |
| 9 Security headers | The post-build CSP check (no unsafe source, no inline style, the line limit); the Playwright violation listener; the Observatory | Steps 3, 4 and 19 |
| 10 Search and navigation | Fifteen sections and the filters render from the export; search returns every model | Step 7 |
| 11 Data explorer and user data | The network-log test (a file's bytes never leave the browser); the hosted set only; attribution per chart | Step 9 |
| 12 Syllabus seed | `syllabi/` validates against its schema; no mark in a slug | Step 7 |
| 13 Analytics | The tracker is self-hosted, production-only and allowlisted; a recorded event | Step 15 |
| 14 Email processor | A double-opt-in sign-up with its list and tier recorded at the processor, then deleted; no address in a log | Step 15 |
| 15 Errors, telemetry and uptime | Every alarm fired once; the SDK initialisation tests; no personal data in a sample event | Step 14 |
| 16 Local app | `pyeconomics[app]` serves the site with the same headers | Step 10 |
| 17 Public-API freeze | `tests/repo/test_public_api.py` | Step 17 |
| 18 Release and soak | Both distributions published together; the soak record | Steps 10, 17 and 19 |
| 19 Launch measures | Lighthouse and axe on the sample; ZAP; the load test; the ledger | Steps 3, 15 and 18 |
| 20 Legal readiness | The data-flows test; `security.txt` valid; the readiness gate's legal sections | Steps 16 and 18 |

## More information

- Related: ADR-0002 (the app wheel), ADR-0003 (public API at 1.0.0),
  ADR-0005 (licence classes and attribution), ADR-0006 (the web stack and
  the Worker clause), ADR-0007 (documentation), ADR-0008 (decision 8's
  optional pyarrow), ADR-0009 (domains and the clearance search),
  ADR-0011 (the cache codec, the layering), ADR-0012 (the surfaces, the
  error table, caching and the staging edge); the Phase 5 roadmap's Web,
  Licence, Privacy and Credential rules.
- The parent roadmap is amended in the same pull request, each edit naming
  this record: §4 5.3 and 7.1 (the syllabus seed, decision 12); §4 5.8, §5
  "Cost projection", "Deployable surfaces", "Data and schema migrations"
  and "Rollback" (the snapshot store, decision 6, and the staging preview,
  decision 4); §4 5.9 and the phase's acceptance criteria (the soak and the
  Lighthouse sample, decisions 18 and 19); and §5's Gate G3 row (its
  window, decision 19).
- The maintainer accepted the twenty decisions, with the values in this
  record, on 2026-10-29 in Phase 5 Step 2 (pull request #221), answering
  one batched question with every recommendation:
  - all twenty decisions, with the re-read's changes listed below,
    including the two additions to decision 5 (the $20 spend cap and the
    request-log exclusion);
  - Buttondown on its Basic plan as the email processor (decision 14),
    over Buttondown Free and Kit Free;
  - Umami Cloud's free Hobby plan as the analytics provider (decision 13),
    over Umami Pro, Plausible Business and GoatCounter;
  - Gate G3's window, the 90 days after the 1.0.0 announcement, and ROADMAP
    §5's thresholds as drafted (decision 19), to be confirmed again at
    Step 18.
- No decision was amended in place while the record read Proposed.
- The re-read of 2026-10-29 changed these drafted defaults of the Phase 5
  roadmap, each accepted by the maintainer:
  - decision 5: the spend-cap budget (new on 2026-10-12) and the request-log
    exclusion are additions;
  - decision 6: run-named objects with soft delete replace Object
    Versioning;
  - decision 7: the Cache API stays, but zone Cache Rules can cache a
    Worker's subrequest, so the reason is now where the logic lives;
  - decision 8: Plotly.js and `plotly.css` come from the `plotly.js`
    package;
  - decision 9: the union of every page's hashes in one header, under the
    2,000-character line limit;
  - decision 14: Buttondown's Basic plan, because metadata left its free
    plan;
  - decision 15: Sentry's browser SDK 11 collects personal data unless
    configured not to.
- Sources, all accessed 2026-10-29:
  - [S1] Cloudflare Workers static assets, billing and limitations ("free
    and unlimited"; requests matching `run_worker_first` answer 429 past
    the free tier),
    https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/.
  - [S2] Cloudflare Workers limits (100,000 requests a day on Free, Error
    1027; 20,000 files of up to 25 MiB),
    https://developers.cloudflare.com/workers/platform/limits/.
  - [S3] Workers static assets binding, `run_worker_first` (route
    patterns, `!` negation, up to 100 entries),
    https://developers.cloudflare.com/workers/static-assets/binding/.
  - [S4] Workers static assets headers (100 rules, 2,000 characters a
    line, not applied to Worker responses) and redirects,
    https://developers.cloudflare.com/workers/static-assets/headers/,
    https://developers.cloudflare.com/workers/static-assets/redirects/.
  - [S5] Cloudflare rate limiting rules, availability (Free: one rule;
    path and verified-bot fields; IP; 10-second period and timeout),
    https://developers.cloudflare.com/waf/rate-limiting-rules/.
  - [S6] Single Redirects, https://developers.cloudflare.com/rules/url-forwarding/;
    Cache Rules, https://developers.cloudflare.com/cache/how-to/cache-rules/;
    Transform Rules, https://developers.cloudflare.com/rules/transform/;
    the Free Managed Ruleset, https://developers.cloudflare.com/waf/get-started/.
  - [S7] Workers Cache API (functional on custom domains),
    https://developers.cloudflare.com/workers/runtime-apis/cache/; how the
    cache works ("reads through its own zone's cache, even if the URL is for
    a non-Cloudflare site"),
    https://developers.cloudflare.com/workers/reference/how-the-cache-works/;
    Cache Rules with Workers,
    https://developers.cloudflare.com/cache/interaction-cloudflare-products/workers/,
    https://developers.cloudflare.com/cache/interaction-cloudflare-products/workers-cache-rules/.
  - [S8] Cloudflare Pages ("Start new projects with Workers"),
    https://developers.cloudflare.com/pages/.
  - [S9] Cloudflare Web Analytics FAQ (custom events: "Not yet"),
    https://developers.cloudflare.com/web-analytics/faq/.
  - [S10] Cloudflare Zero Trust plans (Free: 50 users; logs up to 24
    hours), https://www.cloudflare.com/plans/sase-zero-trust.md; seat
    management (service tokens take no seat),
    https://developers.cloudflare.com/cloudflare-one/identity/users/seat-management/.
  - [S11] Workers rollbacks (the last 100 versions),
    https://developers.cloudflare.com/workers/configuration/versions-and-deployments/rollbacks/;
    previews ("Version URLs are publicly available"),
    https://developers.cloudflare.com/workers/configuration/previews/.
  - [S12] Cloud Run release notes (Cloud Storage volumes GA for services and
    jobs, 2024-08-27; spend caps GA 2026-10-12),
    https://docs.cloud.google.com/run/docs/release-notes; Cloud Storage
    volume mounts for services and for jobs,
    https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts,
    https://docs.cloud.google.com/run/docs/configuring/jobs/cloud-storage-volume-mounts;
    Cloud Storage FUSE overview,
    https://docs.cloud.google.com/storage/docs/cloud-storage-fuse/overview.
  - [S13] Cloud Storage pricing and Always Free,
    https://cloud.google.com/storage/pricing,
    https://docs.cloud.google.com/free/docs/free-cloud-features; Object
    Versioning ("We recommend that you use soft delete instead"),
    https://docs.cloud.google.com/storage/docs/object-versioning; lifecycle,
    https://docs.cloud.google.com/storage/docs/lifecycle.
  - [S14] Cloud Scheduler pricing (three free jobs per billing account,
    then $0.10 a job), https://cloud.google.com/scheduler/pricing.
  - [S15] Cloud Run pricing (request-based and jobs free tiers),
    https://cloud.google.com/run/pricing; billing settings,
    https://docs.cloud.google.com/run/docs/configuring/billing-settings;
    maximum instances (may be exceeded briefly),
    https://docs.cloud.google.com/run/docs/configuring/max-instances;
    CPU (concurrency above 1 needs at least one vCPU),
    https://docs.cloud.google.com/run/docs/configuring/services/cpu.
  - [S16] Cloud Billing budgets,
    https://docs.cloud.google.com/billing/docs/how-to/budgets; spend caps
    (single project, monthly, Cloud Run eligible, enforcement not instant,
    overages billed),
    https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps.
  - [S17] Cloud Run logging (request logs created automatically; exclusion
    filters), https://docs.cloud.google.com/run/docs/logging; LogEntry
    `httpRequest` (`requestUrl` with the query, `remoteIp`, `userAgent`),
    https://docs.cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry;
    log buckets (30 days by default),
    https://docs.cloud.google.com/logging/docs/buckets; default settings
    (`global` location),
    https://docs.cloud.google.com/logging/docs/default-settings; exclusions,
    https://docs.cloud.google.com/logging/docs/exclusions.
  - [S18] Astro configuration reference, `security.csp`,
    https://docs.astro.build/en/reference/configuration-reference/; Astro 6
    ("now stable"), https://astro.build/blog/astro-6/; adapter
    `staticHeaders`,
    https://docs.astro.build/en/reference/adapter-reference/; the
    Cloudflare adapter,
    https://docs.astro.build/en/guides/integrations-guide/cloudflare/.
  - [S19] MDN, `frame-ancestors` ("not supported in the `<meta>`
    element"),
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors.
  - [S20] npm registry, https://registry.npmjs.org/<name>/latest: astro
    7.4.4 (MIT; Node 22.23.4 or later), @astrojs/check 0.9.12 (TypeScript
    `^5.0.0 || ^6.0.0`), typescript 7.0.2, astro-og-canvas 0.13.2 (MIT),
    @astrojs/sitemap 3.7.4, plotly.js 4.2.0 (MIT), katex 0.19.1 (MIT),
    pagefind 1.5.2 (MIT), @rjsf/core and @rjsf/validator-ajv8 6.11.0
    (Apache-2.0), @rjsf/shadcn 6.11.0 (MIT), @sentry/browser 11.10.0
    (MIT), @lhci/cli 0.15.1 (Lighthouse 12.6.1; lighthouse itself 13.6.0),
    @mdn/mdn-http-observatory 1.7.2 (MPL-2.0), wrangler 4.156.0, xlsx
    0.18.5 (2022-03-24) and read-excel-file 9.3.14 (MIT, 2026-10-29).
  - [S21] PyPI, https://pypi.org/pypi/<name>/json: sentry-sdk 2.73.0,
    opentelemetry-sdk 1.45.2, locust 2.47.0 and plotly 7.1.0, which bundles
    Plotly.js 4.1.1 (its changelog,
    https://raw.githubusercontent.com/plotly/plotly.py/main/CHANGELOG.md).
  - [S22] Node.js release schedule (24: maintenance from 2026-10-20, end of
    life 2028-04-30; 26: LTS from 2026-10-28),
    https://raw.githubusercontent.com/nodejs/Release/main/schedule.json.
  - [S23] Pagefind hosting (`'wasm-unsafe-eval'`; `worker-src 'self'
    blob:`), https://pagefind.app/docs/hosting/.
  - [S24] KaTeX options (`output: "mathml"`), https://katex.org/docs/options.
  - [S25] Plotly.js: strict-CSP support through `dist/plotly.css` and the
    `no-inline-styles` marker, https://github.com/plotly/plotly.js/pull/7109;
    the stylesheet missing from the `*-dist-min` packages,
    https://github.com/plotly/plotly.js/issues/7332.
  - [S26] RJSF validation, precompiled validators ("to overcome issues with
    `unsafe-eval`"),
    https://rjsf-team.github.io/react-jsonschema-form/docs/usage/validation.
  - [S27] Umami pricing (Hobby: $0, 100K events a month, one website,
    six-month retention, custom events and properties, no API),
    https://umami.is/pricing; Umami Cloud FAQ (retention; US or EU region,
    read-only after setup), https://docs.umami.is/docs/cloud/faq.
  - [S28] Umami FAQ (no cookies; what is collected),
    https://docs.umami.is/docs/faq; privacy (IP processed transiently),
    https://umami.is/privacy; DPA, https://umami.is/dpa; subprocessors,
    https://umami.is/subprocessors; tracker configuration
    (`data-host-url`), https://docs.umami.is/docs/tracker-configuration;
    self-hosting the script,
    https://docs.umami.is/docs/bypass-ad-blockers; the collector
    (`gateway.umami.is`), https://docs.umami.is/docs/api/sending-stats.
  - [S29] Plausible pricing (Starter $9; custom properties on Business),
    https://plausible.io/; subscription plans,
    https://plausible.io/docs/subscription-plans; data policy,
    https://plausible.io/data-policy.
  - [S30] GoatCounter terms ("reasonable public usage"),
    https://www.goatcounter.com/help/terms; events,
    https://www.goatcounter.com/help/events; privacy,
    https://www.goatcounter.com/help/privacy.
  - [S31] Buttondown pricing (Free to 100; Basic $9 to 1,000; Standard $29
    to 5,000), https://buttondown.com/pricing.
  - [S32] Buttondown: embed forms (by navigation, not `fetch`),
    https://docs.buttondown.com/building-your-subscriber-base; metadata
    ("Available on the Basic plan"), https://docs.buttondown.com/metadata;
    the April 2026 plan changes,
    https://buttondown.com/blog/paywall-changes; double opt-in,
    https://docs.buttondown.com/double-opt-in; open and click tracking
    (opt-in), https://docs.buttondown.com/open-tracking,
    https://docs.buttondown.com/click-tracking.
  - [S33] Buttondown DPA (data processed; transfer to the United States),
    https://buttondown.com/legal/data-processing-agreement; subprocessors
    (AWS `us-west-2`), https://buttondown.com/legal/subprocessors.
  - [S34] Kit pricing (free to 10,000), https://kit.com/pricing; account
    email stats (`open_tracking_enabled`, `click_tracking_enabled`),
    https://developers.kit.com/api-reference/accounts/get-email-stats; DPA,
    https://kit.com/dpa.
  - [S35] Sentry pricing (Developer: one user, 5k errors, 30-day lookback),
    https://sentry.io/pricing/; data storage location (US or EU, fixed),
    https://docs.sentry.io/organization/data-storage-location/; JavaScript
    SDK 10 to 11 migration (`dataCollection`),
    https://docs.sentry.io/platforms/javascript/migration/v10-to-v11/;
    Python data collected,
    https://docs.sentry.io/platforms/python/data-management/data-collected/;
    DPA (accepted electronically), https://sentry.io/legal/dpa/.
  - [S36] Grafana Cloud pricing (Free: 10k active series, 50 GB logs and
    traces, 14-day retention, three users), https://grafana.com/pricing/;
    regional availability (fixed per stack),
    https://grafana.com/docs/grafana-cloud/security-and-account-management/regional-availability/;
    OTLP, https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/.
  - [S37] Better Stack uptime (10 monitors and heartbeats, 3-minute checks,
    a status page, free), https://betterstack.com/uptime; pricing (email
    and Slack alerts on free), https://betterstack.com/pricing; status
    pages ("Your logo and sub-domain … Completely free"),
    https://betterstack.com/status-page; monitor headers,
    https://betterstack.com/docs/uptime/api/create-a-new-monitor/; DPA,
    https://betterstack.com/dpa.
  - [S38] `server.json` schema 2025-12-11 (`remotes` beside `packages`),
    https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json.
  - [S39] MDN HTTP Observatory, tests and scoring,
    https://developer.mozilla.org/en-US/observatory/docs/tests_and_scoring;
    the grader's modifiers,
    https://github.com/mdn/mdn-http-observatory/blob/main/src/grader/charts.js.
  - [S40] ZAP baseline scan, https://www.zaproxy.org/docs/docker/baseline-scan/;
    the GitHub Action (v0.15.0), https://github.com/zaproxy/action-baseline.
  - [S41] FINRA Rule 2214, paragraph (c)(4),
    https://www.finra.org/rules-guidance/rulebooks/finra-rules/2214.
  - [S42] 17 CFR 4.41(b)(1) ("These results are based on simulated or
    hypothetical performance results that have certain inherent
    limitations"), https://www.law.cornell.edu/cfr/text/17/4.41. The
    capitalised "HYPOTHETICAL PERFORMANCE RESULTS HAVE MANY INHERENT
    LIMITATIONS" is NFA Rule 2-29(c)(1)'s, not the CFTC's.
  - [S43] RFC 9116, https://www.rfc-editor.org/rfc/rfc9116.html.
  - [S44] HSTS preload requirements (one year minimum, `includeSubDomains`,
    `preload`), https://hstspreload.org/; the `.dev` TLD preloaded,
    https://www.registry.google/domains/dev/.
  - [S45] SheetJS installation ("the registry is out of date"),
    https://docs.sheetjs.com/docs/getting-started/installation/nodejs.
  - [S46] Google Cloud terms (the Cloud Data Processing Addendum
    incorporated), https://cloud.google.com/terms,
    https://cloud.google.com/terms/data-processing-addendum.
  - [S47] Cloudflare Self-Serve Subscription Agreement (its DPA incorporated;
    Free services included), https://www.cloudflare.com/terms/; Customer
    DPA 6.4, https://www.cloudflare.com/cloudflare-customer-dpa/; privacy
    policy, https://www.cloudflare.com/privacypolicy/.
