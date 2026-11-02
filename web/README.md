# web/

The pyeconomics web app: a static Astro site with React islands, written in
TypeScript, shared by the hosted site and the local app (`pyeconomics serve`).
The stack is decided in [ADR-0006](../docs/adr/0006-web-stack-and-hosting.md)
and its hosting, headers and launch in
[ADR-0013](../docs/adr/0013-web-app-and-launch.md). Nothing here ships in the
`pyeconomics` wheel; under ADR-0002 the built site ships in its own
`pyeconomics-app` wheel.

## Build

Node comes from `.nvmrc` (24); Python from the repository's `uv` environment.

```sh
npm ci --ignore-scripts
npm run data     # export the site data and golden cases; precompile the validators; generate the client
npm run build    # astro build, then scripts/headers.ts (dist/_headers), scripts/indexing.ts and scripts/search-index.ts
```

The build generates a page for every model (`/models/<domain>/<name>/`, from
the `models` content collection over `registry.json`), every domain, and
every problem type (`/problems/<slug>/`), each with a canonical link, Open
Graph tags, schema.org JSON-LD and a social image drawn at build time under
`/og/`, plus `sitemap-index.xml`. `scripts/indexing.ts` then writes
`robots.txt` and `_redirects` (each model alias's page to its model's) and
fails on a page the sitemap misses or a path in `released-pages.json`, the
ledger of every page a release has served, that neither builds nor
redirects. `scripts/search-index.ts` last runs Pagefind over the pages marked
searchable (model, domain and problem pages) and writes the index into
`dist/pagefind/`, which `/search/` and the header's search box query in the
browser.

## Navigation, filters and coverage

The header lists the fifteen domain sections (`src/lib/paths.ts` `DOMAINS`);
`/models/` filters every model by domain, syllabus level and topic, evidence,
cost class, data needs and tag, keeping the filters in the query string; each
model page lists its syllabus tags and related models; and `/coverage/` is the
coverage matrix. All of it is computed at build time from the registry and
`syllabi/` (`src/lib/catalog.ts`), whose one loader is
`../scripts/web/syllabi.py`.

`npm run data` writes `src/data/generated/` and `src/client/`, both
git-ignored: every build regenerates them from the registry and the catalog,
so a new model or source reaches the site with no web code. It runs
`../scripts/web/compile_validators.mjs` after the export, which precompiles
each model's input-schema validator into `src/data/generated/validators/`;
the build stops on a validator that is missing or stale.

## Calculators

Every model page carries a calculator (`src/components/calculator/`), a React
island hydrated when it scrolls into view. It loads its model's module (the
precompiled validators, the input schema and the examples), renders the
schema with RJSF and its shadcn/ui theme, and posts the inputs' JSON to
`POST /v1/models/<id>/run` on the site's own origin through the generated
client (`src/lib/run-request.ts`). The answer's bytes are kept as received:
the outputs table, the chart (`src/lib/figure.ts`, a port of `figure_of`,
drawn by Plotly.js's basic bundle, loaded only with the first chart), the
sources panel, the downloads (`?format=`) and the snippets for Python, the
command line, curl and MCP sit beside them. A bound model offers live data
(`?profile=`) where hosted mode can serve every field it binds.

## Check

```sh
npm run check       # astro check (TypeScript 6, strict)
npm run lint        # ESLint: security, TypeScript and accessibility rules, no warnings
npm test            # Vitest (tests/unit): the model page, every model's form, the figures, the snippets
npm run test:dist   # Vitest over the built dist/ (tests/site): pages, sections, links, JSON-LD, images
npm run test:parity # every golden case through the calculators' request builder, and each snippet kind,
                    # against a local `pyeconomics serve` the suite starts (tests/parity)
npx playwright install chromium
npm run e2e         # Playwright with axe and the CSP-violation listener (tests/e2e)
npm run lighthouse  # Lighthouse on ADR-0013 decision 19's sample pages
npm run licences    # what ships to browsers passes the permissive allowlist
```

Playwright and Lighthouse serve `dist/` with `wrangler dev` as Workers static
assets, so `dist/_headers` applies exactly as on Cloudflare. Astro's Content
Security Policy does not run in `astro dev`; test it on a build. The
calculator tests forward the page's `/v1/` requests to
`../tests/web/e2e_api.py`, the REST app in hosted mode over the catalog
world's stand-in providers, which Playwright starts on port 8799: live data,
its sources and a CSV's attribution block need no network or key.
`npx playwright test --config playwright.staging.config.ts` runs the duration
calculator on staging through Access (`CF_ACCESS_CLIENT_ID` and
`CF_ACCESS_CLIENT_SECRET`).

## Deploy

`wrangler.jsonc` puts the site and the API on one host (ADR-0013 decision 3):
static assets serve every page, and the shared edge Worker
(`../tools/node/edge/worker.mjs`) runs first only on `/v1/*`, `/mcp`,
`/healthz`, `/version` and `/openapi.json`, forwarding them to Cloud Run. Its
env-less configuration has no origin, so locally those paths answer `503`.
`SITE_FLAVOUR=staging npm run build` adds `X-Robots-Tag: noindex` to every
path and writes `Disallow: /` into `robots.txt`; `SITE_FLAVOUR=production`
does the same unless the site data's version is a final release; an unset
`SITE_FLAVOUR` is a local build, which stays indexable.

Every merge to `main` deploys env `staging` (`staging.pyeconomics.dev`,
behind Cloudflare Access) from `deploy-staging.yml`'s `site` job; nothing here
deploys by hand except a change of route or custom domain. Deploy, rollback,
the Access application and the token are in
[docs/operations/staging.md](../docs/operations/staging.md).

## Rules

The web rules in [AGENTS.md](../AGENTS.md) govern this directory: one policy
from `csp.config.ts`, never loosened by a page; no third-party script; no
secret in the bundle; formulas as MathML; `dependencies` only for what ships to
browsers.
