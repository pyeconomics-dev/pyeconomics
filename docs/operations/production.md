# Production Operations Runbook

This runbook covers production: the site, the API and the MCP endpoint on one
origin, `pyeconomics.dev`, in front of the Cloud Run service `pyeconomics-api` in
`us-central1`, with its daily snapshot job (ROADMAP §4 5.8, §5 "Release &
deployment strategy", "Security controls by layer" and "Cost projection";
ADR-0006; ADR-0012 decisions 19 and 20; ADR-0013 decisions 3 to 7).

Production repeats staging's pattern (`docs/operations/staging.md`) with its
findings applied. Where the two match, such as how the snapshot job behaves, this
page says so and points there.

Section 11 holds what watches production (Phase 5 Step 14): the error tracker,
the telemetry, the monitors, the heartbeats, the hourly check and the budget, each
alarm's proof, the incident procedure and the runbooks.

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
| `pyeconomics-production-runtime` | `roles/secretmanager.secretAccessor` | `ratelimit-url`, `edge-credential`, `sentry-dsn`, `otlp-headers` |
| | `roles/storage.objectViewer` | the bucket |
| `pyeconomics-prod-snapshots` | `roles/storage.objectUser` | the bucket |
| | `roles/secretmanager.secretAccessor` | `bea-api-key`, `bls-api-key`, `snapshot-heartbeat`, `sentry-dsn`, `otlp-headers` |
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
  `BLS_SECRET_VERSION`; Step 14 added `HEARTBEAT_SECRET_VERSION`,
  `SENTRY_SECRET_VERSION`, `OTLP_SECRET_VERSION`, `OTLP_ENDPOINT` (Grafana Cloud's
  OTLP gateway, not a secret) and `PUBLIC_SENTRY_DSN` (the browser project's DSN,
  public by design: every production page that reports an error sends it), and the
  cutover adds `PRODUCTION_PUBLIC`. A version variable left unset leaves its secret
  out of the deploy, so the service runs without that signal.

### 1.5 The `production-health` GitHub environment

The hourly check (`production-health.yml`, section 11) cannot run in `production`:
every job there waits for the maintainer. This environment admits the branch `main`
alone, has no reviewer, and holds two secrets, `CF_ACCESS_CLIENT_ID` and
`CF_ACCESS_CLIENT_SECRET`, of the Access service token
`pyeconomics-production-health`, which is in the policy `production-site-ci` and
nothing else. The cutover deletes both (section 5); the check then sends no Access
header. Phase 3 check 78 and Phase 4 check 64 admit those two names for that one
workflow, in this environment alone.

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

5. **Retire the monitors' Access tokens (Step 14).** Once step 2 is done, the
   monitors and the hourly check reach production without a token:
   - In Better Stack, open each of the five production monitors, **Configure** →
     **Advanced settings** → **Request headers**, delete both `CF-Access-Client-*`
     headers and **Save**.
   - Delete the `production-health` environment's two secrets:

     ```bash
     gh secret delete CF_ACCESS_CLIENT_ID --env production-health -R pyeconomics-dev/pyeconomics
     gh secret delete CF_ACCESS_CLIENT_SECRET --env production-health -R pyeconomics-dev/pyeconomics
     ```

   - In Zero Trust, **Access** → **Service Auth** → **Service Tokens**, delete
     `pyeconomics-production-uptime` and `pyeconomics-production-health`, and remove
     the keyring entries `UPTIME_CF_ACCESS_CLIENT_ID` and
     `UPTIME_CF_ACCESS_CLIENT_SECRET` (service `pyeconomics-production`).
   - Dispatch `production-health.yml` and check every monitor stays up.

**Rollback:** create the Access application again, as section 10 records it, and
delete `PRODUCTION_PUBLIC`. This takes minutes. The monitors then need their
headers back: create the two service tokens again and repeat Step 14's setup.

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
| Sentry DSN (`pyeconomics-api`) | Secret Manager `sentry-dsn` | never; rotate if leaked (6.6) |
| Grafana Cloud token `pyeconomics-api-production` | Secret Manager `otlp-headers` | `2027-11-10` |
| Heartbeat URLs | Secret Manager `snapshot-heartbeat`, here and in staging | never; rotate if leaked (6.6) |
| Access service token `pyeconomics-production-uptime` | Better Stack's monitors, keyring | one year from its creation; deleted at the cutover |
| Access service token `pyeconomics-production-health` | `production-health` environment | one year from its creation; deleted at the cutover |
| Better Stack API token | keyring `BETTERSTACK_API_TOKEN` | never; for setup and the alarm proofs |

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

### 6.6 The telemetry's secrets

Each is read by a pinned version, so a new one takes effect on the next deploy.

- **Sentry's DSN.** In Sentry, **Settings** → **Projects** → `pyeconomics-api` →
  **Client Keys (DSN)**, generate a new key and disable the old one. Store it with
  the helper the maintainer used at Step 14, or from a hidden prompt:

  ```bash
  read -rs DSN && printf '%s' "$DSN" | gcloud secrets versions add sentry-dsn \
    --project=pyeconomics-production --data-file=- && unset DSN
  gh variable set SENTRY_SECRET_VERSION --env production --body "<NEW_VERSION>" -R pyeconomics-dev/pyeconomics
  ```

  The browser project's DSN is public and needs no rotation; a new one is
  `gh variable set PUBLIC_SENTRY_DSN --env production`.
- **The OTLP header.** In the `rubywolf301` stack, **Administration** → **Users and
  access** → **Cloud access policies** → `pyeconomics-production-telemetry` → **Add
  token**, then store
  `Authorization=Basic%20<base64 of instance-id:token>` in `otlp-headers` the same
  way, move `OTLP_SECRET_VERSION`, redeploy, and delete the old token.
- **A heartbeat URL.** As `docs/operations/staging.md` section 7 describes, in each
  project: a new heartbeat in Better Stack, a new `snapshot-heartbeat` version
  on the host `incidents.betterstack.com` (never `uptime.betterstack.com`, which
  the job refuses), `HEARTBEAT_SECRET_VERSION` moved, a deploy, and the old
  heartbeat deleted.

Prove each with a dispatch of `deploy-production.yml` and the signal it carries
(section 11.2).

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
| Secret Manager | 6 active versions, 10,000 accesses | 7 (12 with staging's): six over, at $0.06 | $0.36 |
| Upstash Redis | none: a free account holds one database, which staging uses | a few commands per request | $0.20 per 100,000 commands |
| Workers, static assets, Access | 100,000 Worker requests a day, unlimited assets, 50 seats | 1 service token, 1 seat, 1 application | $0 |

The telemetry's vendors are on free plans (Step 14): Sentry's Developer plan
(5,000 errors and 5 million spans a month, 30 days' lookback, one user), Grafana
Cloud's free tier (10,000 active metric series, 50 GB of traces, 14 days'
retention) and Better Stack's free plan (10 monitors and heartbeats together,
3-minute checks, one status page). Production uses five monitors and two
heartbeats of the ten.

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

Added in Phase 5 Step 14 (2026-11-10 onwards):

- **Google Cloud:** the secrets `sentry-dsn`, `otlp-headers` and `snapshot-heartbeat`
  in production and `snapshot-heartbeat` in staging, with the accessor roles section
  1.3 lists (staging's job identity reads its own heartbeat).
- **Sentry** (US region, signed up with the maintainer's GitHub identity, DPA
  accepted): organization `pyeconomics`, projects `pyeconomics-api` (Python) and
  `pyeconomics-web` (browser JavaScript, no framework; allowed domain
  `pyeconomics.dev`), error monitoring only, each alerting by email on new
  high-priority issues (Sentry's project form offers no "every new issue" option any
  more, so every event pyeconomics sends is error level); IP addresses are not stored
  and the default scrubbers are required.
- **Grafana Cloud** (US region, a free account on a 14-day trial that falls back to
  the free tier): stack and organization `rubywolf301`, the name Grafana gave at
  sign-up (`rubywolf301.grafana.net`); in-stack access policy
  `pyeconomics-production-telemetry` (**Administration → Users and access → Cloud
  access policies**) with metrics, logs and traces write only and no IP range,
  because Cloud Run sends from no fixed address; token `pyeconomics-api-production`.
- **Better Stack** (free plan): team `pyeconomics`; the five monitors and two
  heartbeats section 11.2 lists; the status page at `status.pyeconomics.dev`, with
  subscriptions off, so it collects no address.
- **Cloudflare:** the Access service tokens `pyeconomics-production-uptime` and
  `pyeconomics-production-health`, in the policy `production-site-ci`; the DNS-only
  `CNAME` `status` → `statuspage.betteruptime.com`, which Better Stack's certificate
  needs.
- **GitHub:** the environment `production-health` (section 1.5), the label
  `production-health`, and the `production` variables section 1.4 lists.

---

## 11. Observability, Alarms and Incidents

Every runtime surface has a health signal, an alarm that reached the maintainer once
on a synthetic failure, and a runbook (ROADMAP §5 "Operations & observability
strategy"; ADR-0013 decision 15). Staging keeps `staging-health.yml` and its own
heartbeat; errors and telemetry are production's alone, because staging shares no
secret with production.

### 11.1 What reports where

| Signal | From | Goes to | Holds | Kept |
| --- | --- | --- | --- | --- |
| Server errors | the API (`pyeconomics.server.observability`): an exception that reached the guard, a 5xx problem from a worker or the app | Sentry `pyeconomics-api`, environment `production` | the error's type and frames (its message withheld), the problem's slug, status and error type, the route's template, the release (`pyeconomics@<version>+<sha>`) | 30 days |
| Snapshot failures | the job (`python -m pyeconomics.server.snapshot_job write`) | Sentry `pyeconomics-api` | an error per failed provider with its slug (error level, so Sentry's high-priority alert emails it); an error when no provider succeeded | 30 days |
| Browser errors | the calculator and explorer islands of a production build | Sentry `pyeconomics-web` | the error's type and frames (message withheld), the island, the page's URL without its query | 30 days |
| Request metrics and traces | the API's guard | Grafana Cloud, service `pyeconomics-api` | `http.server.request.duration` by method, route template (a model's runs as one), status class and route kind; 5% of requests as spans | 14 days |
| Task metrics | the API's worker results | Grafana Cloud | `pyeconomics.tasks` by kind, model id, cost class and outcome (slug); `pyeconomics.task.duration` | 14 days |
| Snapshot metrics | the job | Grafana Cloud, service `pyeconomics-snapshots` | `pyeconomics.snapshot.ok`, `.duration`, `.series` by provider and state, `.data_age` in days | 14 days |
| Uptime | Better Stack, every 3 minutes | Better Stack, the status page | up or down, response time | no period stated (ADR-0013) |
| Heartbeats | each snapshot job, at its end | Better Stack | a ping, or `/fail` when no provider succeeded | no period stated |
| Synthetic check | `production-health.yml`, hourly | GitHub issues and notifications | the run's log | GitHub's |
| Spend | the `$10` budget | email, Pub/Sub `production-budget-alerts` | spend against the budget | Google's |

Nothing in any of them holds a path, a query, an input, a client address or a key:
`tests/server/test_server_telemetry.py` plants all of them and finds none, and
`web/tests/unit/error-reporting.test.ts` holds the browser's options. The process's
global OpenTelemetry providers stay OpenTelemetry's no-op proxies, so spans FastAPI or
the MCP SDK make through the API go nowhere.

If Grafana stops showing data, the service logs `telemetry: an OpenTelemetry export
failed` once per failed export, without the exporter's text: look for it in the
service's log, then check the token's expiry (section 6).

To send one test event from the production image, which proves the DSN and the
release, run the job once with other arguments (the job's command is `python`; an
execution may override its arguments, never its command), which writes nothing to the
bucket:

```bash
gcloud run jobs execute pyeconomics-snapshots --project=pyeconomics-production \
  --region=us-central1 --args=-m,pyeconomics.server.observability,test-event --wait
```

### 11.2 The alarms and their proofs

Each alarm reaches the maintainer by email, and GitHub's also through its
notifications. Better Stack's free plan alerts by email and Slack only: its apps,
push, calls and SMS need a paid responder licence. Each fired once on a synthetic
failure, which was then undone.

| Alarm | Fires when | Reaches | Runbook | Proof (date, run or event, confirmation) |
| --- | --- | --- | --- | --- |
| Monitor `pyeconomics site` (`/`, keyword `pyeconomics`) | the page fails or lacks the keyword from more than one region | email | 11.4 deploy regressed | with the run monitor below |
| Monitor `pyeconomics site version` (`/version.json`, `git_sha`) | as above | email | 11.4 deploy regressed | with the run monitor below |
| Monitor `pyeconomics API version` (`/version`, `"mode":"hosted"`) | as above | email | 11.4 deploy regressed | with the run monitor below |
| Monitor `pyeconomics API health` (`/healthz`, `"status":"ok"`) | as above | email | 11.4 deploy regressed | with the run monitor below |
| Monitor `pyeconomics model run` (a `GET` run of `foundations.time_value`) | the run fails or answers another model | email | 11.4 deploy regressed, cost spike | 2026-11-11: the monitor pointed at `foundations.no_such_model` at 04:15:18Z; incident 1050499954 ("Status 404") at 04:16:30Z, emailed 04:16:32Z; path restored 04:16:50Z, resolved 04:20:36Z, emailed 04:20:37Z. The maintainer confirmed both emails. |
| Heartbeat `pyeconomics production snapshot job` (24 h, 2 h grace) | no ping for 26 hours, or a `/fail` ping | email | 11.4 snapshot job silent | 2026-11-11: first ping from snapshot run `20261111T152704Z-6e47d597` (deploy run 43047889685). The period was cut to 30 s with no grace at 16:07:15Z (a missed ping without skipping a night's snapshot); incident 1050770649 ("Missed heartbeat") at 16:07:28Z; 24 h and 2 h restored at 16:07:36Z, one ping, resolved 16:07:43Z. The maintainer confirmed both emails. |
| Heartbeat `pyeconomics staging snapshot job` (24 h, 2 h grace) | as above, for staging | email | 11.4 snapshot job silent | 2026-11-11: its first ping, from staging snapshot run `20261111T042908Z-9c848723` (`"heartbeat": "sent"`); its alert path is production's, proven above. |
| Sentry `pyeconomics-api` new high-priority issue (every event pyeconomics sends is error level) | a new server error or snapshot failure | email | 11.4 by the issue's slug | 2026-11-11: `python -m pyeconomics.server.observability test-event` run in the production job (execution `pyeconomics-snapshots-4fgmq`) sent event `540ed8195f3d4eb68c11fed38e651935` at 16:05:22Z. The maintainer confirmed the email. |
| Sentry `pyeconomics-web` new high-priority issue | a new browser error | email | 11.4 deploy regressed | 2026-11-11: production's duration calculator, driven in headless Chromium with the CI service token, was handed a run answer that does not parse; the island showed "The server's answer could not be read." and Sentry's ingest answered 200 at 16:06:20Z. The maintainer confirmed the email. |
| `production-health` issue | the hourly check fails or times out | GitHub issue and failed-run notification | 11.4 deploy regressed, upstream down | 2026-11-11: run 43057148476, dispatched with `simulate_failure`, failed and opened issue #295, closed after; runs 43056971358 and 43057821091 passed on `c8f7bc3`. |
| Budget `pyeconomics-production-monthly-budget` | spend passes 50, 90 or 100% of `$10` | email; Pub/Sub `production-budget-alerts` | section 8 | 2026-11-11: an unacknowledged pull of `production-budget-alerts-sub` returned the budget's notification of 2026-11-06T13:18:33Z (cost `$0.00` of `$10`). The threshold email cannot be triggered without real spend; Google sends it to the billing account's administrators. |

Step 14's Deployed & verified check, 2026-11-11: `deploy-production.yml` run
43047889685 on `c8f7bc3` succeeded (its site job rerun after an `apt-get` hang,
issue #294); production's `/version` and `/version.json` (CI service token) report
`c8f7bc3`; Grafana's `target_info` shows `pyeconomics-api` and
`pyeconomics-snapshots` with `vcs_ref_head_revision` `c8f7bc3`; the Sentry events
above came from that revision; the status page showed all five monitors up ("All
services are online", 16:33Z); and `production-health` run 43057821091 passed.
Two setup fixes came out of the first deploy: Sentry's 16-digit organisation ids
(#293) and the heartbeat URL's host (section 6.6).

The monitors send the Access headers of `pyeconomics-production-uptime` until the
cutover (section 5). Staging has no monitor of its own: `staging-health.yml` checks it
hourly, and giving Better Stack staging's CI token would share CI's credential with a
vendor.

### 11.3 Incident procedure

1. **Acknowledge.** In Better Stack, acknowledge the incident (the email's or the
   app's **Acknowledge**), so it stops escalating. A Sentry or GitHub alarm has no
   acknowledgement: assign the issue to yourself.
2. **Say so.** If visitors are affected, post on the status page: Better Stack →
   **Status pages** → `pyeconomics` → **Status updates** → **New update**, naming the
   affected part (site, API, data) and nothing about the cause yet. Monitors that are
   down already show there.
3. **Triage.** Which alarm, and what changed: the newest `deploy-production.yml`
   run, the newest snapshot run (`current.json`'s `completed_at`), Sentry's issue and
   its release, the service's log (route templates and problem slugs only). Pick the
   runbook below.
4. **Mitigate.** Prefer the fast reversible step: roll back the part that changed
   (section 3), disable a failing source (section 7), lower the maximum instances
   (section 8). Never fix forward under pressure what a rollback restores.
5. **Verify.** Dispatch `production-health.yml` (`gh workflow run
   production-health.yml --ref main`), and watch the monitors return to up.
6. **Close.** Resolve the Better Stack incident, post the resolution on the status
   page, and close the Sentry and GitHub issues.
7. **Post-incident note.** Within five days, open an issue labelled `incident`:
   what visitors saw and for how long, the timeline, the cause, the fix, and each
   follow-up as its own issue. A shipped wrong number is also a model error (11.4).

### 11.4 Runbooks

Each names the alarm that leads to it.

- **Deploy regressed** (any monitor, `production-health`, a Sentry issue whose
  release is the newest): roll back the part that changed (section 3: the API, the
  site or the data), then open a `fix/` issue with the failing check's output. The
  next deploy of a fixed commit restores latest traffic itself.
- **Snapshot job silent** (a heartbeat, a Sentry `snapshot run failed` error, the
  `stale_snapshot` warning): follow `docs/operations/staging.md` section 7, "A silent
  or failing job", with production's names (section 3.3). The site keeps serving the
  last good snapshot with its date; run the job by hand once fixed and check the
  heartbeat turns up.
- **Secret leaked** (gitleaks, trufflehog or a report): rotate it in Secret Manager or
  where section 6 says it lives, redeploy, prove the new one with an authenticated
  round trip (a deploy's checks, the monitors), disable the old version, and publish
  an advisory if a user's key or data was exposed.
- **Upstream source down or changed** (a Sentry `snapshot provider ... failed`
  error, `production-health`'s CSV check, a provider's live test): the service
  keeps serving the last snapshot; open an issue, and if the source changed its
  format, update its provider and contract cassettes. Disable it on the job (section
  7) if it keeps failing.
- **Data terms changed** (a terms review, a notice from the source): reclassify the
  source in its provider's `Terms` in a pull request and purge its hosted snapshots
  (`docs/operations/staging.md` section 7, "Purging a source's snapshots"), then
  record it in the changelog (ROADMAP §5 licensing rule 7).
- **Bad release on PyPI** (the release workflow's smoke, a user's report): yank the
  version on PyPI, publish a fixed patch release, and post an advisory or a changelog
  note; production deploys the fixed tag.
- **Model error reported** (an issue, a Sentry error naming a model): reproduce it as
  a failing golden case on a `fix/` branch, fix it with a new model version, and
  publish the erratum (ROADMAP §5 "Model quality & governance").
- **Cost spike** (the budget's alerts, the run monitor slowing, a burst of 429s in
  Grafana's request metrics): section 8.

## 12. Growth Signals and the Gate G3 Ledger

Phase 5 Step 15 (ROADMAP §5 Gate G2; ADR-0013 decisions 13, 14 and 19). Everything
here records counts or holds an address only at the processor; nothing passes an
address, an input or an identifier through pyeconomics' own systems.

### 12.1 What records what

| Signal | Where | Who holds it | How it reaches the ledger |
|--------|-------|--------------|---------------------------|
| Page views and the six allowlisted events (`web/src/lib/events.ts`) | Umami Cloud, US region, free Hobby plan; the tracker is `web/vendor/umami/script.js`, served from our origin in production builds only | Umami Software | Manual: Hobby has no API |
| Newsletter and waitlist sign-ups, with list, source and tier | Buttondown, by plain form posts with double opt-in | Buttondown, under its DPA | Manual: its only key that counts sign-ups also reads every address, so none is kept in CI |
| API and MCP requests by route kind | Grafana Cloud's request histogram (section 11) | Grafana Labs | `growth-metrics.yml`, with `GRAFANA_READ_TOKEN` (`metrics:read`) in the `growth` environment |
| PyPI downloads, stars, forks, Discussions activity | pypistats.org, GitHub | Public | `growth-metrics.yml` |

The production build reads the analytics site's id from the `production`
environment's variable `PUBLIC_UMAMI_WEBSITE_ID` (public: it is in every page).
The forms post to `https://buttondown.com/api/emails/embed-subscribe/<username>`,
the username in `web/src/lib/signup.ts`.

Verified live on 2026-11-12, after deploy run 43161922517 (commit `197528c`), from
the maintainer's session through Access:
- Umami recorded the page views and each of the six events (`calculator_run`,
  `search`, `download`, `waitlist_submit`, `pro_preview_click`,
  `newsletter_submit`).
- A waitlist sign-up (tier Personal) and then a newsletter sign-up reached
  Buttondown as one subscriber with `tier` = `personal`. The second sign-up
  overwrote `list`, which is why each list now has keys of its own (PR #304). The
  test subscriber was then deleted in Buttondown.
- Grafana's API and MCP counts by route kind are in the ledger's baseline comment
  on issue #298.

The views of `/models/equity/cape/` and `/data/us/unemployment/rate/` that day
came from deploy run 43154922210's browser checks, before
`web/tests/staging/support.ts` opted them out of analytics.

### 12.2 The weekly comment and its manual rows

`growth-metrics.yml` runs every Monday at 06:17 UTC and on a dispatch from `main`. It
comments on the pinned issue "Gate G3 ledger" (label `gate-g3-ledger`), which its
first run created and pinned, and whose first comment is the pre-launch baseline.
Each Monday, edit that week's comment (the `...` menu, Edit) and replace each
_manual_ with the figure:

1. **Analytics**: at https://cloud.umami.is, open the `pyeconomics` website, set the
   range to the last 7 days, and copy Views and Visitors; under Events, copy each of
   `calculator_run`, `download`, `pro_preview_click`, `newsletter_submit`,
   `waitlist_submit` and `search`.
2. **Sign-ups**: at https://buttondown.com, Subscribers, filter by type Regular
   (confirmed), and read the count for metadata `newsletter` = `yes`, then for
   `waitlist` = `yes` with `tier` = `personal`, `commercial` and `team`. One
   address can be on both lists: Buttondown keeps one subscriber per address and
   merges a second sign-up into it, so each list has keys of its own
   (`<list>` and `<list>_source`, `web/src/lib/signup.ts`).

A row reading _unavailable_ means that source failed that week (the run's log names
it); _not configured_ means the `growth` environment lacks the secret or variable;
_not on PyPI_ means pypistats.org has no such package yet (`pyeconomics-app` until
its first release). PyPI counts are sums of pypistats.org's daily series up to its
latest day, not its `/recent` summary, whose 30-day figure was wrong on 2026-11-11.

A newsletter goes only to subscribers with `newsletter` = `yes`, and a Pro email only
to those with `waitlist` = `yes`: a waitlist sign-up agreed to an email if Pro
opens, not to the newsletter. Before the first send, check in the draft that its
recipients are filtered on that metadata (not yet tried: nothing has been sent).

### 12.3 A deletion request

A subscriber who asks to be deleted is deleted in Buttondown (Subscribers, the
address, Delete), which holds the only copy; nothing else holds an address. Reply
from the maintainer's own mailbox that it is done.

### 12.4 Rotating the Grafana token

Create a new token on the access policy `pyeconomics-growth-read` (Grafana Cloud,
Access Policies), store it with `gh secret set GRAFANA_READ_TOKEN --env growth`
from its prompt, dispatch `growth-metrics.yml`, check its comment's API and MCP rows
show counts, then delete the old token.
