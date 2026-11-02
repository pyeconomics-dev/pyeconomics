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
npm run data     # export the registry, OpenAPI, errors, sources, concepts and surfaces; generate the client
npm run build    # astro build, then scripts/headers.ts (dist/_headers) and scripts/indexing.ts
```

The build generates a page for every model (`/models/<domain>/<name>/`, from
the `models` content collection over `registry.json`), every domain, and
every problem type (`/problems/<slug>/`), each with a canonical link, Open
Graph tags, schema.org JSON-LD and a social image drawn at build time under
`/og/`, plus `sitemap-index.xml`. `scripts/indexing.ts` then writes
`robots.txt` and `_redirects` (each model alias's page to its model's) and
fails on a page the sitemap misses or a path in `released-pages.json`, the
ledger of every page a release has served, that neither builds nor
redirects.

`npm run data` writes `src/data/generated/` and `src/client/`, both
git-ignored: every build regenerates them from the registry and the catalog,
so a new model or source reaches the site with no web code.

## Check

```sh
npm run check       # astro check (TypeScript 6, strict)
npm run lint        # ESLint: security, TypeScript and accessibility rules, no warnings
npm test            # Vitest (tests/unit), including the model page rendered through Astro's container
npm run test:dist   # Vitest over the built dist/ (tests/site): pages, sections, links, JSON-LD, images
npx playwright install chromium
npm run e2e         # Playwright with axe and the CSP-violation listener (tests/e2e)
npm run lighthouse  # Lighthouse on ADR-0013 decision 19's sample pages
npm run licences    # what ships to browsers passes the permissive allowlist
```

Playwright and Lighthouse serve `dist/` with `wrangler dev` as Workers static
assets, so `dist/_headers` applies exactly as on Cloudflare. Astro's Content
Security Policy does not run in `astro dev`; test it on a build.

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
