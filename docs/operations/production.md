# Production Operations Runbook

This runbook covers production: the site, the API and the MCP endpoint on one
origin, `pyeconomics.dev`, in front of the Cloud Run service `pyeconomics-api` in
`us-central1`, with its daily snapshot job (ROADMAP §4 5.8, §5 "Release &
deployment strategy", "Security controls by layer" and "Cost projection";
ADR-0006; ADR-0012 decisions 19 and 20; ADR-0013 decisions 3 to 7).

Production repeats staging's pattern (`docs/operations/staging.md`) with its
findings applied. Where the two match, such as how the snapshot job behaves, this
page says so and points there.

This document is operational documentation for maintainers and is excluded from
the public Sphinx documentation build (`exclude_patterns` in `docs/conf.py`).

Never print, echo or write a secret to a file or to shell history. Every command
here prompts or pipes, and every secret is recorded by name and expiry only.

---

## 1. Topology and Trust Boundary

```text
Browser / API or MCP client
  │  HTTPS to pyeconomics.dev
  ▼
Cloudflare Access (application pyeconomics-production-site), until the cutover
  │  Refuses every path without the maintainer's session or the service token
  ▼
Cloudflare Free Managed Ruleset and the zone's one rate rule (the API's paths)
  ▼
Worker pyeconomics-web (web/wrangler.jsonc, env production)
  │  run_worker_first: /v1/*, /mcp, /healthz, /version, /openapi.json
  ├── the API's paths ──► tools/node/edge/worker.mjs
  │     - answers a GET run from the Cache API when it holds one (section 1.2)
  │     - strips hop-by-hop headers, Cookie and every cf-access-* header
  │     - sets X-Pyeconomics-Edge from the Worker's EDGE_CREDENTIAL secret
  │     - adds X-Content-Type-Options: nosniff
  │     ▼
  │   Cloud Run service pyeconomics-api (us-central1, 0 to 3 instances)
  │     - refuses /v1 and /mcp without the edge credential, in constant time,
  │       before any route or rate-limit lookup
  │     - per-IP rate limits in production's own Upstash database
  │     - reads every series from the bucket, mounted read-only at /snapshots
  │
  └── every other path ─► Workers static assets (web/dist) with dist/_headers

Cloud Scheduler pyeconomics-snapshots-daily (30 23 * * *, Etc/UTC)
  ▼
Cloud Run job pyeconomics-snapshots ─► gs://pyeconomics-production-snapshots
```

Static asset requests run no Worker code and are free and unlimited. The env-less
Wrangler configuration has no origin and no secret, so no deploy without `--env`
can reach this Worker. `workers_dev` and `preview_urls` are off: version URLs on
`workers.dev` are public and would bypass Access.

### 1.1 Until the cutover, nothing is reachable without Access

The Access application covers the whole host, so the site, the API's paths and
`/mcp` all answer Access's login without the token. The origin's own gate is
independent of Access, and it stays after the cutover: a direct request to the
`*.run.app` URL without the edge credential answers `403` (`edge-required`). Only
`/version` and `/healthz` are open on the origin, for probes.

As on staging, the service grants `roles/run.invoker` to `allUsers`, because the
Worker has no Google identity and no fixed address: the edge credential is the
origin's gate. The binding is set once and survives deploys; the deploy identity's
`roles/run.developer` cannot change it. If it is ever lost, the deploy's origin
`/version` check fails and traffic rolls back. A project owner restores it:

```bash
gcloud run services add-iam-policy-binding pyeconomics-api \
  --project=pyeconomics-production --region=us-central1 \
  --member=allUsers --role=roles/run.invoker
```

### 1.2 The edge's cache of GET runs

The Worker keeps a `GET` run for as long as the origin's `Cache-Control` allows
(ADR-0013 decision 7): a day for a run that reads no data, five minutes for a run
on storable hosted-safe data. It keeps only a `200` the origin calls `public`, so
a `POST` run, a problem and a run on other data are never kept. Three facts decide
how it behaves:

- **Each deployed Worker version keeps its own entries.** A result holds the
  package's version and its URL does not, so the cache key holds the version the
  `CF_VERSION_METADATA` binding names. A deploy retires everything the last one
  kept, and so does a rollback.
- **It works behind Access, though Cloudflare does not say so.** Cloudflare's
  Cache API page says it is "not currently available" for Workers fronted by
  Access. Yet on 2026-11-10, behind Access, a fresh `GET` run answered
  `cf-cache-status: DYNAMIC` and each repeat `HIT` with an `age`, while a `POST`
  run and a problem stayed `no-store`. Because that is undocumented, a failure of
  the cache is only ever a miss, the run still reaches the origin, and no deploy
  check fails on a miss. Section 5 checks it again after the cutover.

### 1.3 Identities and their exact roles

Service accounts in `pyeconomics-production` (project number `180273591942`). None
holds a project-level role, and each lists only Google-managed keys: no service
account key exists anywhere, and none is ever made.

| Identity | Holds | On |
| --- | --- | --- |
| `pyeconomics-production-deploy` | `roles/run.developer` | service `pyeconomics-api`, job `pyeconomics-snapshots` |
| | `roles/artifactregistry.writer` | production's repository `pyeconomics` |
| | `roles/artifactregistry.reader` | staging's repository `pyeconomics`, in `pyeconomics-staging`, for promotion |
| | `roles/iam.serviceAccountUser` | `pyeconomics-production-runtime`, `pyeconomics-prod-snapshots` |
| | `roles/storage.objectViewer` | the bucket, to check `current.json` came from the deploy's run |
| | `roles/iam.workloadIdentityUser`, to the pool's principal set | itself |
| `pyeconomics-production-runtime` | `roles/secretmanager.secretAccessor` | `ratelimit-url`, `edge-credential` |
| | `roles/storage.objectViewer` | the bucket |
| `pyeconomics-prod-snapshots` | `roles/storage.objectUser` | the bucket |
| | `roles/secretmanager.secretAccessor` | `bea-api-key`, `bls-api-key` |
| `pyeconomics-prod-scheduler` | `roles/run.invoker` | job `pyeconomics-snapshots` |

Google limits a service account's name to 30 characters, which is why the last two
say `prod`.

**The federation.** Pool `github`, OIDC provider `pyeconomics`, issuer
`https://token.actions.githubusercontent.com`, with this condition, so only this
repository's `production` environment on `main` or a `v*` tag can reach the deploy
identity:

```text
assertion.repository_id == '796473097' && assertion.environment == 'production'
&& (assertion.ref == 'refs/heads/main' || assertion.ref.startsWith('refs/tags/v'))
```

### 1.4 The `production` GitHub environment

Required reviewer: the maintainer, with self-review allowed, because there is one
maintainer. It admits the branch `main` and tags matching `v*`, and nothing else.

- **Secrets:** `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`,
  `CLOUDFLARE_API_TOKEN`. No repository secret exists.
- **Variables:** `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SERVICE`,
  `GCP_ARTIFACT_REPOSITORY`, `GCP_WORKLOAD_IDENTITY_PROVIDER`,
  `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_RUNTIME_SERVICE_ACCOUNT`, `GCP_SNAPSHOT_JOB`,
  `GCP_SNAPSHOT_BUCKET`, `GCP_SNAPSHOT_SERVICE_ACCOUNT`,
  `STAGING_IMAGE_REPOSITORY`, `PRODUCTION_HOST`, `CLOUDFLARE_ACCOUNT_ID`,
  `RATELIMIT_SECRET_VERSION`, `EDGE_SECRET_VERSION`, `BEA_SECRET_VERSION`,
  `BLS_SECRET_VERSION`; Step 14 adds `HEARTBEAT_SECRET_VERSION`, and the cutover
  adds `PRODUCTION_PUBLIC`.

---

## 2. Deploying

### 2.1 By tag or by dispatch

- **A release tag:** pushing a `v*` tag that is not a `.devN` rehearsal starts
  `deploy-production.yml` beside `release.yml`.
- **A dispatch from `main`:** for a redeploy, a rollback forward or a config change:

  ```bash
  gh workflow run deploy-production.yml --ref main
  ```

  It deploys `main`'s newest commit, so that commit must already have passed staging.

Each of the four jobs waits for the maintainer in the `production` environment, so
a deploy asks for four approvals: Actions, the run, **Review deployments**,
**Approve and deploy**. Refusing any of them stops the deploy where it stands, with
everything before it live. To approve from a terminal:

```bash
env_id=$(gh api repos/pyeconomics-dev/pyeconomics/environments/production --jq .id)
gh api -X POST repos/pyeconomics-dev/pyeconomics/actions/runs/<RUN_ID>/pending_deployments \
  -F 'environment_ids[]='"$env_id" -f state=approved -f comment='<why>'
```

### 2.2 What a deploy does

1. **`check`** refuses a commit that is not on `main`, or that has no successful
   `deploy-staging.yml` run. This is the promotion gate: production only ever runs
   what staging verified, read with the run's own `GITHUB_TOKEN`.
2. **`data`** reads the digest staging tagged with the commit, copies it into
   production's registry with `docker buildx imagetools create --prefer-index=false`,
   which moves the manifest and blobs unchanged (without the flag it wraps
   staging's single manifest in a new list, with a new digest), and fails if the
   copy's digest differs. A tag also
   names the image, and the registry keeps `v*` images for ever. Then it pins the
   job to the digest with every setting in the workflow, waits for any run in
   progress, runs the job, and checks that `current.json` was completed after the
   run began.
3. **`api`** deploys the digest with secrets pinned by version, restores latest
   traffic, then checks through the edge: `/version` names the commit, a data-free
   run equals the wheel's bytes, a `GET` run answers twice through the cache path, a
   hosted-safe series answers with the retrieval time `current.json` records,
   a library-only source answers `403`, a series outside the set `404`, and a direct
   origin request without the credential `403`. `scripts/parity/check_deployed.py`
   then checks one golden case per domain.
4. **`site`** builds the production flavour from the commit, uploads it as a new
   Worker version and deploys that version, then checks `/version.json`, the exact
   policy, indexing by version, the sitemap, the API on the same host, and the
   staging browser suite (`web/tests/staging/`) against production.

A pre-release build refuses indexing (`X-Robots-Tag: noindex`, `Disallow: /`); a
final release allows it (ADR-0013 decision 4).

The workflow's concurrency group never cancels a running deploy. A newer one waits.

### 2.3 When staging's image is gone

Staging's registry keeps its two newest images and any image older than a day goes
(a `v*` tag is kept, but staging's images carry commit tags). So a commit two or
more merges behind `main` may have no image, and `data` stops with "Staging's
registry holds no image". Tag a release on `main`'s newest commit, or within a day
of it. To deploy again, merge or dispatch `deploy-staging.yml` so staging verifies
the commit you want, and rerun.

### 2.4 Routes and the custom domain

CI's token uploads and deploys versions, and never touches routes. A change to
`web/wrangler.jsonc`'s routes, `workers_dev` or `preview_urls` is the maintainer's,
from `web/`, with their own Wrangler login. In CI `wrangler deploy` would override a
DNS record for the custom domain without asking.

```bash
npm run data
SITE_FLAVOUR=production GIT_SHA=$(git rev-parse HEAD) npm run build
npx wrangler deploy --env production
```

---

## 3. Rolling Back

Each part rolls back by itself. The workflow does this on a failed check; these are
the same steps by hand.

### 3.1 The API

```bash
gcloud run revisions list --service=pyeconomics-api \
  --project=pyeconomics-production --region=us-central1
gcloud run services update-traffic pyeconomics-api \
  --project=pyeconomics-production --region=us-central1 \
  --to-revisions="<REVISION_NAME>=100"
```

This pins traffic to that revision. The next deploy restores latest traffic itself.
To restore it sooner, once the fault is fixed:

```bash
gcloud run services update-traffic pyeconomics-api \
  --project=pyeconomics-production --region=us-central1 --to-latest
gcloud run services describe pyeconomics-api \
  --project=pyeconomics-production --region=us-central1 --format='yaml(spec.traffic)'
```

The last command must show `latestRevision: true` and `percent: 100`.

### 3.2 The site

Workers keep the last 100 versions. From `web/`, with the maintainer's login:

```bash
npx wrangler deployments status --env production
npx wrangler versions list --env production
npx wrangler rollback <VERSION_ID> --env production --message "reason"
```

The next deploy replaces it; nothing stays pinned. A rollback also moves the edge
cache to that version's entries.

### 3.3 The data

Runs are never overwritten, so rolling back means pointing `current.json` at an
earlier run (decision 6). Each provider's entry names its `previous` object.

```bash
gcloud scheduler jobs pause pyeconomics-snapshots-daily \
  --project=pyeconomics-production --location=us-central1
gcloud storage cat gs://pyeconomics-production-snapshots/current.json > current.json
# For each provider to roll back, replace "object" with its "previous" entry:
# copy "name" and "sha256" together, because the service checks the hash.
gcloud storage cp current.json gs://pyeconomics-production-snapshots/current.json
```

The service reads it again within a minute. The next run writes a new `current.json`
from the latest data, so resume the schedule only when newer data may be served:

```bash
gcloud scheduler jobs resume pyeconomics-snapshots-daily \
  --project=pyeconomics-production --location=us-central1
```

Running the job, a silent or failing job, purging a source's snapshots and the job's
log all work as `docs/operations/staging.md` section 7 describes, with these names:
job `pyeconomics-snapshots`, bucket `pyeconomics-production-snapshots`, schedule
`pyeconomics-snapshots-daily`, project `pyeconomics-production`.

---

## 4. Lifting a Tripped Spend Cap

The `$20` spend-cap budget `pyeconomics-production-cloud-run-cap` pauses all Cloud Run
workloads in the project when estimated spend passes the target. Services answer
`5xx`; the job's new tasks fail to start and running ones fail to complete. Pages,
the documentation and PyPI stay up. Enforcement is not instant, and overages are
billed. Email goes to billing administrators and project owners.

1. Find out what caused it first (section 8). Lifting it returns the API to the
   traffic that tripped it, and a lifted cap does not trip again this month unless
   the target is raised.
2. In the Google Cloud console, open **Billing → Budgets & alerts**, click the spend
   caps banner (**View spend cap details**), open the budget, choose **Lift spend
   cap**, then **Confirm**.
3. Allow up to an hour for Cloud Run to recover, then check `/version` through the
   edge and run the job by hand if a scheduled run was missed.

Left alone, the cap lifts by itself on the first of the next month.

---

## 5. The Cutover (Phase 5 Step 19)

Opening the site removes Access and nothing else. The origin still refuses requests
without the edge credential, and the rate rule and the managed WAF stay on.

1. Set the variable that ends the deploy's check that Access refuses a request
   without the token, or the next deploy fails that check and rolls back:

   ```bash
   gh variable set PRODUCTION_PUBLIC --env production --body true -R pyeconomics-dev/pyeconomics
   ```

2. Delete the Access application `pyeconomics-production-site` (Zero Trust →
   **Access** → **Applications**). Keep staging's two.
3. Enable the redirect rules, in each of the four zones: **Rules** → **Redirect
   Rules**, then switch on the rule named `Canonical redirect, enabled at the
   cutover`. Their proxied `AAAA 100::` records exist already; until a rule is on,
   those hosts answer a Cloudflare error.
4. **Check the edge's cache again without Access (section 1.2).** Send the same
   `GET` run twice, within a minute, from one machine. `?inputs=` is the inputs'
   JSON in base64url without padding:

   ```bash
   url='https://pyeconomics.dev/v1/models/foundations.time_value/run?inputs=eyJjYWxjdWxhdGlvbiI6ImZ1dHVyZV92YWx1ZSIsInByZXNlbnRfdmFsdWUiOjEwMDAuMCwicmF0ZSI6MC4wNSwicGVyaW9kcyI6MTB9'
   curl -sS -o /dev/null -D - "$url" | grep -iE '^(cf-cache-status|age|cache-control):'
   curl -sS -o /dev/null -D - "$url" | grep -iE '^(cf-cache-status|age|cache-control):'
   ```

   The second must show `cf-cache-status: HIT`, or an `age`. Then check `POST` runs
   and a problem never show one.

**Rollback:** create the Access application again, as section 10 records it, and
delete `PRODUCTION_PUBLIC`. This takes minutes.

---

## 6. Rotating Secrets and Tokens

Each row is production's alone: nothing here is shared with staging. Rotate at least
14 days before an expiry. `Expires` is the date recorded when it was created.

| Secret | Where it lives | Expires |
| --- | --- | --- |
| Edge credential | Secret Manager `edge-credential`, Worker secret `EDGE_CREDENTIAL` | never; rotate yearly |
| Upstash URL | Secret Manager `ratelimit-url` | never; rotate yearly |
| BEA and BLS keys | Secret Manager `bea-api-key`, `bls-api-key` | never |
| Access service token `pyeconomics-production-ci` | `production` environment, keyring | `2027-11-10` |
| Cloudflare API token `pyeconomics-web-deploy` | `production` environment | `2027-11-11` |

### 6.1 The edge credential

Secret Manager, the Worker and Cloud Run must change together. Do this outside a
deploy: between steps 1 and 3 the edge answers `403` (`edge-required`) for a minute.

1. Generate it without displaying it, from the repository root:

   ```bash
   python3 -c '
   import secrets, subprocess
   cred = secrets.token_urlsafe(48)
   subprocess.run(
       ["gcloud", "secrets", "versions", "add", "edge-credential",
        "--project=pyeconomics-production", "--data-file=-"],
       input=cred.encode("ascii"), check=True,
   )
   subprocess.run(
       ["npx", "--prefix", "web", "wrangler", "secret", "put", "EDGE_CREDENTIAL",
        "--config", "web/wrangler.jsonc", "--env", "production"],
       input=cred.encode("ascii"), check=True,
   )
   '
   ```

2. Read the new version's number (metadata only):

   ```bash
   gcloud secrets versions list edge-credential \
     --project=pyeconomics-production --limit=1 --format='value(name)'
   ```

3. Pin it on the service and in the environment:

   ```bash
   gh variable set EDGE_SECRET_VERSION --env production --body "<NEW_VERSION>" -R pyeconomics-dev/pyeconomics
   gcloud run services update pyeconomics-api \
     --project=pyeconomics-production --region=us-central1 \
     --update-secrets="PYECONOMICS_EDGE_CREDENTIAL=edge-credential:<NEW_VERSION>"
   ```

4. Once traffic is on the new revision, disable the old version:

   ```bash
   gcloud secrets versions disable "<OLD_VERSION>" \
     --secret=edge-credential --project=pyeconomics-production
   ```

### 6.2 The Upstash URL

Rotate the password in the Upstash console for `pyeconomics-production`, then add the
new URL from a hidden prompt, read its version, and pin it as in 6.1 with
`ratelimit-url`, `RATELIMIT_SECRET_VERSION` and `PYECONOMICS_RATELIMIT_URL`:

```bash
python3 -c '
import getpass, subprocess
url = getpass.getpass("New rediss:// URL: ").strip()
assert url.startswith("rediss://"), "Must be a rediss:// URL"
subprocess.run(
    ["gcloud", "secrets", "versions", "add", "ratelimit-url",
     "--project=pyeconomics-production", "--data-file=-"],
    input=url.encode("ascii"), check=True,
)
'
```

### 6.3 The job's provider keys

As in `docs/operations/staging.md` section 7, with `--project=pyeconomics-production`
and `--env production`. The keys are production's own registrations, not staging's.
A new version takes effect on the next deploy, which pins it.

### 6.4 The Access service token

1. In Zero Trust, **Access** → **Service Auth** → **Service Tokens**, refresh
   `pyeconomics-production-ci`, which keeps the token and its policy, and copy both
   values.
2. Store them from the prompt:

   ```bash
   gh secret set CF_ACCESS_CLIENT_ID --env production -R pyeconomics-dev/pyeconomics
   gh secret set CF_ACCESS_CLIENT_SECRET --env production -R pyeconomics-dev/pyeconomics
   uv run --no-sync python -c "import getpass, keyring; keyring.set_password('pyeconomics-production', 'CF_ACCESS_CLIENT_ID', getpass.getpass('ID:').strip()); keyring.set_password('pyeconomics-production', 'CF_ACCESS_CLIENT_SECRET', getpass.getpass('Secret:').strip())"
   ```

3. Prove it with a dispatch of `deploy-production.yml`, and update the date above.

### 6.5 The Cloudflare API token

- **Token name:** `pyeconomics-web-deploy` (account-owned)
- **Scope:** *Specified Workers* = `pyeconomics-web` · *Individual Workers* ·
  *Editor*; no other permission, no IP filter (GitHub-hosted runners have no fixed
  addresses). On 2026-11-10 it read, uploaded, deployed and rolled back
  `pyeconomics-web`, and both staging Workers refused it (issue #231). It cannot
  change the custom domain or routes, which stay the maintainer's (section 2.4).
- **Created:** `2026-11-10`. **Expires:** `2027-11-11`.

To rotate it:

1. In the Cloudflare dashboard, **Manage Account** → **Account API Tokens**, roll
   `pyeconomics-web-deploy`, which keeps its policy, and copy the new value.
2. Store it from the prompt:

   ```bash
   gh secret set CLOUDFLARE_API_TOKEN --env production -R pyeconomics-dev/pyeconomics
   ```

3. Prove it with a dispatch of `deploy-production.yml` from `main`, and update the
   dates above.

---

## 7. Disabling a Data Provider

A provider is disabled through `PYECONOMICS_DISABLED_PROVIDERS`, which
`DataProvider._gate` enforces before any cache or snapshot read (issue #162):

```bash
gcloud run services update pyeconomics-api \
  --project=pyeconomics-production --region=us-central1 \
  --update-env-vars=PYECONOMICS_DISABLED_PROVIDERS=treasury
```

Clear it with `--remove-env-vars=PYECONOMICS_DISABLED_PROVIDERS`. To stop the job
asking a source as well, set it with `gcloud run jobs update pyeconomics-snapshots`,
which keeps the source's last good object. A deploy's `--set-env-vars` replaces the
list, so a provider that must stay off needs the same variable in the workflow.

---

## 8. A Cost Spike

The `$10` budget `pyeconomics-production-monthly-budget` alerts at 50, 90 and 100% of
actual spend, by email and to the Pub/Sub topic `production-budget-alerts`. In order:

1. **Look.** Billing → Reports, filtered to the project and grouped by SKU.
2. **Lower the maximum:**

   ```bash
   gcloud run services update pyeconomics-api \
     --project=pyeconomics-production --region=us-central1 --max-instances=1
   ```

   A deploy puts `--max-instances=3` back, so change the workflow if this must stay.
3. **Tighten the rule.** Lower the zone's rate rule (section 8.1).
4. **If it comes from a leaked service token,** revoke it (section 6.4) and rotate the
   edge credential (section 6.1).
5. **Stop the origin** if nothing else holds. Every API path then answers Google's
   `403`, and pages keep serving:

   ```bash
   gcloud run services remove-iam-policy-binding pyeconomics-api \
     --project=pyeconomics-production --region=us-central1 \
     --member=allUsers --role=roles/run.invoker
   ```

The spend cap is the last line. The maximum instance count alone does not bound cost,
because Cloud Run may exceed it briefly (ADR-0013 decision 5).

### 8.1 The rate rule

The zone's one Free-plan rule, under **Security** → **WAF** → **Rate limiting rules**,
keeps the name `staging-api-rate-limit` from Phase 4 and covers production too,
because it matches paths, never the host: 50 requests in 10 seconds per IP, then
`429` for 10 seconds. Its expression is in `docs/operations/staging.md` section 5.

---

## 9. Free-Tier and Budget Arithmetic

Prices were read on 2026-11-05, for `us-central1`. Every free allowance below but the
Worker's belongs to the billing account, so staging and any other project on
it share them.

### What production costs while nobody uses it

| Resource | Free allowance | Production's use | Monthly cost |
| --- | --- | --- | --- |
| Cloud Run service | 180,000 vCPU-s, 360,000 GiB-s, 2M requests | a few hundred seconds of checks | $0 |
| Cloud Run job | 240,000 vCPU-s, 450,000 GiB-s | 31 runs × 240 to 624 s = 7,440 to 19,344 vCPU-s, twice that in GiB-s | $0 |
| Cloud Storage | 5 GB-months | about 280 MB: 31 runs × 7.3 MB, and 7 days of soft delete | $0 |
| Cloud Scheduler | 3 jobs | 1 (2 with staging's) | $0 |
| Artifact Registry | 0.5 GiB, shared with staging | about 251 MiB an image: the three newest and every `v*`, shared layers stored once, beside staging's two | about $0.10 per GiB over |
| Secret Manager | 6 active versions, 10,000 accesses | 4 (8 with staging's): two over, at $0.06 | $0.12 |
| Upstash Redis | none: a free account holds one database, which staging uses | a few commands per request | $0.20 per 100,000 commands |
| Workers, static assets, Access | 100,000 Worker requests a day, unlimited assets, 50 seats | 1 service token, 1 seat, 1 application | $0 |

So production costs under $1 a month before launch, and the alert budget of `$10`
stays quiet.

### What the budget buys

Beyond the free tier a busy instance costs `$0.000024` a vCPU-second and `$0.0000025`
a GiB-second, so `$0.0000265` a second at 1 vCPU and 1 GiB, plus `$0.40` per million
requests:

- **One instance busy all month** (2.68 million seconds): about `$71` before the free
  tier, about `$66` after it.
- **Three instances busy all month:** about `$213`, the case the maximum alone would
  not stop. They spend `$20` in about three days, which is what the cap is for.
- **What `$10` buys past the free tier:** about 377,000 busy instance-seconds, or
  about 4.4 days of one instance, on top of the 180,000 seconds free.
- **The Worker's own limit** comes first: past 100,000 requests a day on the Free plan
  the API's paths answer `429` while pages keep serving (ADR-0013 decision 3). At
  10 requests a second, a flood spends that allowance in 2.8 hours, then fails closed.

---

## 10. What Exists

Created from 2026-11-05 to 2026-11-10, in Phase 5 Step 13. Names only.

- **Google Cloud:** project `pyeconomics-production` (`180273591942`), in the
  organization staging's project is in, on billing account `010548-2423B0-E0B624`.
  Docker repository `pyeconomics`, whose cleanup keeps `v*` tags and the three newest
  and deletes the rest after a day; staging's policy gained the same `v*` rule.
  Bucket `pyeconomics-production-snapshots`: uniform access, public access prevention
  enforced, Google's default soft delete, no Object Versioning, seeded from staging's
  newest run. Log exclusion `cloud-run-request-logs` on the `_Default` sink.
  Service `pyeconomics-api`, job `pyeconomics-snapshots` and Cloud Scheduler job
  `pyeconomics-snapshots-daily`; the identities `pyeconomics-production-deploy`,
  `pyeconomics-production-runtime`, `pyeconomics-prod-snapshots` and
  `pyeconomics-prod-scheduler`, with Google-managed keys only; Workload Identity
  pool `github` and provider `pyeconomics`; the secrets `edge-credential`,
  `ratelimit-url`, `bea-api-key` and `bls-api-key`, each at version 1; the alert
  budget `pyeconomics-production-monthly-budget` (`$10`) and the spend cap
  `pyeconomics-production-cloud-run-cap` (`$20`, Cloud Run only).
- **Upstash:** database `pyeconomics-production`, GCP `us-central1`, TLS, pay as you
  go, on the maintainer's personal account beside staging's free one.
- **GitHub:** environment `production`, the maintainer the one required reviewer,
  deployments from `main` and `v*` tags only, three secrets and seventeen variables.
- **Cloudflare:** Worker `pyeconomics-web`, custom domain `pyeconomics.dev`; Access
  application `pyeconomics-production-site` on the whole host, 24-hour session, with
  the policies `production-site-ci` (Service Auth, `pyeconomics-production-ci`) and
  `production-site-maintainer` (Allow, the maintainer's email); HSTS at
  `max-age=63072000; includeSubDomains; preload`, the same value `web/csp.config.ts`
  sends; a disabled redirect rule in each of the four zones, with proxied `AAAA 100::`
  records on `www.pyeconomics.dev` and on the apex and `www` of `.com`, `.org`, `.io`;
  the API token `pyeconomics-web-deploy` (section 6.5). The Free Managed Ruleset runs
  as Cloudflare deploys it by default on a Free plan ("deployed by default on Free
  plans", its WAF guide), so the zone shows no managed entry point of its own; the
  rate rule `staging-api-rate-limit` matches the API's paths on every host.
- **Read the Docs:** `docs.pyeconomics.dev`, canonical, by a `CNAME` to `readthedocs.io`
  with the proxy off, which Read the Docs requires, so Access cannot cover that host;
  it serves only what was already public. `pyeconomics.readthedocs.io` redirects there.
- **Cloudflare Web Analytics' Real User Measurements** stay disabled for the zone, as
  `docs/operations/staging.md` section 1 records. The setting is zone-wide, and their
  beacon's CSP violations would fail the site job's browser check.
