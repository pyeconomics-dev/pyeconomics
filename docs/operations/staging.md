# Staging Operations Runbook

This runbook covers the Phase 4 staging deployment of the hosted `pyeconomics`
API (`staging-api.pyeconomics.dev` in front of Cloud Run `pyeconomics-api-staging`
in `us-central1`), its trust boundary, deployment and rollback procedures,
secret rotation, provider disablement, cost-spike mitigation, and free-tier
arithmetic (ROADMAP §4 4.7, §5; ADR-0006; ADR-0012 decisions 11, 12, 19, 20).

 This document is operational documentation for maintainers and is excluded from
the public Sphinx documentation build (`exclude_patterns` in `docs/conf.py`).

---

## 1. Topology and Trust Boundary

```text
Caller (CI probe / maintainer CLI)
  │  HTTPS to staging-api.pyeconomics.dev
  │  Headers: CF-Access-Client-Id, CF-Access-Client-Secret (or Access session)
  ▼
Cloudflare Zero Trust Access (self-hosted application)
  │  Blocks unauthenticated callers before the Worker executes
  ▼
Cloudflare Free-Plan Rate Rule
  │  Outer volumetric guard on staging-api.pyeconomics.dev
  ▼
Cloudflare Worker (tools/node/edge/worker.mjs; workers_dev = false)
  │  - Strips hop-by-hop headers, Connection-listed headers, Host, and Access headers
  │  - Preserves CF-Connecting-IP and MCP headers (MCP-Protocol-Version, Mcp-Method, Mcp-Name)
  │  - Never adds an Origin header
  │  - Sets X-Pyeconomics-Edge from the Worker's EDGE_CREDENTIAL secret
  │  - Forwards method, path, query, and body to ORIGIN_URL (*.a.run.app)
  ▼
Google Cloud Run (pyeconomics-api-staging, us-central1)
  │  - Verifies X-Pyeconomics-Edge in constant time (SHA-256 + hmac.compare_digest)
  │    before any /v1 or /mcp route or rate-limit lookup runs
  │  - Keys per-IP rate limits by CF-Connecting-IP only after the edge check succeeds,
  │    backed by Upstash Redis over TLS (rediss://)
  │  - Executes model runs and hosted-safe series fetches in a 2-worker process pool
```

### Why Cloud Run IAM allows unauthenticated invocations

Cloud Run's IAM policy grants `roles/run.invoker` to `allUsers` and accepts
`--ingress=all` because the Cloudflare Worker executes on Cloudflare's global
edge without a static source IP range or a Google Cloud OIDC identity. Instead,
the origin enforces its own cryptographic gate
(`src/pyeconomics/server/edge.py`):

- Every request to `/v1/*` or `/mcp` must carry `X-Pyeconomics-Edge` matching
  `PYECONOMICS_EDGE_CREDENTIAL` (32 to 512 printable ASCII characters, no
  spaces, compared in constant time via SHA-256 digests).
- Any direct request to the `*.a.run.app` origin URL without the matching header
  is rejected immediately with `403 Forbidden`
  (`https://pyeconomics.dev/problems/edge-required`) before touching Redis or
  any route handler, and without trusting `CF-Connecting-IP`.
- Only `/healthz` and `/version` are open on the origin for container health
  probes. Because Google Frontend (GFE) reserves paths ending in `z` such as
  `/healthz` on `*.run.app` external URLs and returns a static 404 before
  reaching the container, Cloud Run's own HTTP startup probe is configured on
  container `/healthz:8080` directly, while the Cloudflare Worker (`worker.mjs`)
  probes the origin's open `/version` endpoint for incoming `GET /healthz` and
  `HEAD /healthz` requests and translates a `200` response into
  `{"status":"ok"}`.

The `allUsers` binding is set once on the service and persists across deploys:
since issue #211 the deploy no longer passes `--allow-unauthenticated`, so it
never rewrites the service's IAM policy. If the binding is ever lost, the
deploy's origin `/version` check fails (Google answers `403`) and traffic rolls
back; a project owner restores it with:

```bash
gcloud run services add-iam-policy-binding pyeconomics-api-staging \
  --project=pyeconomics-staging --region=us-central1 \
  --member=allUsers --role=roles/run.invoker
```

### Least-privilege identities and secrets

- **No service-account keys:** GitHub Actions authenticates to Google Cloud
  exclusively through Workload Identity Federation (`google-github-actions/auth`
  v3 pinned by commit SHA). The OIDC provider's `attribute-condition` restricts
  federation to this repository's numeric ID (`796473097`) and branch
  `refs/heads/main`. Each service account lists only `SYSTEM_MANAGED` keys.
- **Deploy service account (`pyeconomics-staging-deploy`):** granted only
  `roles/artifactregistry.writer` on the `pyeconomics` Artifact Registry
  repository, `roles/run.developer` on the `pyeconomics-api-staging` service,
  and `roles/iam.serviceAccountUser` on `pyeconomics-staging-runtime`. It holds
  no project-level role (as of 2026-10-29, issue #211). Phase 4 had bound
  `roles/run.admin` on the project, because Cloud Run refuses a service-level
  binding before the service exists; once the service existed, the role moved
  to the service, narrowed to `roles/run.developer`, which deploys and routes
  traffic but cannot set IAM policy. A new service (production) gets the same
  pattern: create it once by hand, then bind the deploy identity on it.
- **Runtime service account (`pyeconomics-staging-runtime`):** granted only
  `roles/secretmanager.secretAccessor` on the `ratelimit-url` and
  `edge-credential` secrets in Secret Manager. It holds no project-wide role.
- **GitHub `staging` environment:** restricted to deployments from `main` only.
  Holds `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` as environment
  secrets (no repository secrets exist) and non-secret configuration (`GCP_PROJECT_ID`,
  `GCP_REGION`, `GCP_SERVICE`, `GCP_ARTIFACT_REPOSITORY`,
  `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`,
  `GCP_RUNTIME_SERVICE_ACCOUNT`, `STAGING_HOST`, `ORIGIN_URL`,
  `RATELIMIT_SECRET_VERSION`, `EDGE_SECRET_VERSION`) as environment variables.

---

## 2. Deployment and Rollback

### Automated deployment on merge to `main`

Every push to `main` triggers `.github/workflows/deploy-staging.yml` (which can
also be triggered manually with `gh workflow run deploy-staging.yml --ref main`):

1. Builds the wheel in a clean virtual environment and records the canonical
   bytes of `pyeconomics.run("foundations.time_value", ...)`.
2. Builds the production container image with `--build-arg GIT_SHA=$GITHUB_SHA`.
3. Scans the image with Trivy (`ghcr.io/aquasecurity/trivy:0.69.3` pinned by
   digest), failing the build on any fixable `CRITICAL` or `HIGH` vulnerability.
4. Records the currently serving Cloud Run revision (`PREVIOUS_REVISION`),
   pushes the image to Artifact Registry by SHA tag, resolves its immutable
   `@sha256:...` digest, and deploys that digest to `pyeconomics-api-staging`
   with secrets pinned by version (`ratelimit-url:$RATELIMIT_SECRET_VERSION`,
   `edge-credential:$EDGE_SECRET_VERSION`).
5. Verifies the deployment:
   - Cloud Run's `startupProbe.httpGet.path` is `/healthz` (`:8080`) and origin
     `/version` returns `200` with `git_sha == $GITHUB_SHA` and
     `mode == "hosted"`.
   - Direct origin `/v1/models` and `POST /mcp` without `X-Pyeconomics-Edge`
     return `403` (`edge-required`).
   - Unauthenticated `https://staging-api.pyeconomics.dev/version` without the
     Cloudflare Access service token is refused.
   - Authenticated `https://staging-api.pyeconomics.dev/healthz` returns `200`
     (`{"status": "ok"}`) and `/version` returns `200` with
     `git_sha == $GITHUB_SHA` and `mode == "hosted"`.
   - Authenticated `POST /v1/models/foundations.time_value/run` returns bytes
     identical to the wheel's `Result.to_json()`.
   - Authenticated `GET /v1/series/treasury:debt?start=2025-01-01&end=2025-01-31`
     returns `200` with `provider == "treasury"`, `licence == "hosted-safe"`,
     and Treasury attribution.
   - Authenticated `GET /v1/series/fred:UNRATE` returns `403`
     (`licence-refused`) with the source's `terms` URL.
6. If any deployment or verification step fails, the workflow automatically
   executes `gcloud run services update-traffic` to route `100%` of traffic back
   to `PREVIOUS_REVISION` and fails the run. That pins traffic to the named
   revision. The next deploy returns it to the latest revision itself: right
   after `gcloud run deploy` it runs `gcloud run services update-traffic
   --to-latest`, before verifying (issue #210), so its new revision is never
   left at `0%`.

### Deploying the Cloudflare Worker edge

The Cloudflare Worker source lives in `tools/node/edge/worker.mjs` with its
unit test suite in `tools/node/edge/worker.test.mjs` and its configuration in
`tools/node/edge/wrangler.toml` (`workers_dev = false`, `preview_urls = false`).

Run the local unit tests before deploying:

```bash
npm --prefix tools/node run test:edge
```

Deploy the Worker from the repository root:

```bash
npx --prefix tools/node wrangler deploy --config tools/node/edge/wrangler.toml
```

### Manual Cloud Run rollback

Cloud Run retains earlier revisions of `pyeconomics-api-staging`. To inspect the
available revisions and shift `100%` of traffic back to a previous revision
immediately without rebuilding:

```bash
# 1. List revisions and their active traffic split
gcloud run revisions list \
  --service=pyeconomics-api-staging \
  --project="$GCP_PROJECT_ID" \
  --region=us-central1

# 2. Route 100% of traffic to the target revision
gcloud run services update-traffic pyeconomics-api-staging \
  --project="$GCP_PROJECT_ID" \
  --region=us-central1 \
  --to-revisions="<REVISION_NAME>=100"
```

A manual rollback pins traffic to that revision (`latestRevision: true`
disappears from the service's traffic). The next deploy returns traffic to its
own new revision; to return to the latest revision before then, once the fault
is fixed:

```bash
# 3. Send 100% of traffic to the latest ready revision again
gcloud run services update-traffic pyeconomics-api-staging \
  --project="$GCP_PROJECT_ID" \
  --region=us-central1 \
  --to-latest

# 4. Confirm: the traffic entry reads latestRevision: true, percent: 100
gcloud run services describe pyeconomics-api-staging \
  --project="$GCP_PROJECT_ID" \
  --region=us-central1 \
  --format='yaml(spec.traffic)'
```

---

## 3. Secret Rotation

Never print, echo, or write a secret value to a file or shell history. Always
generate or read secrets in memory and pipe them directly into Secret Manager,
Wrangler, `gh secret set`, or the OS keyring.

### 3.1 Rotating the edge credential (`edge-credential` / `EDGE_CREDENTIAL`)

The edge credential is shared between Secret Manager (`edge-credential`, read by
Cloud Run as `PYECONOMICS_EDGE_CREDENTIAL`) and the Cloudflare Worker secret
(`EDGE_CREDENTIAL`).

1. Generate a fresh 64-character URL-safe credential in Python and pipe it into
   a new Secret Manager version and the Cloudflare Worker secret without
   displaying it:

   ```bash
   python3 -c '
   import secrets, subprocess
   cred = secrets.token_urlsafe(48)
   subprocess.run(
       ["gcloud", "secrets", "versions", "add", "edge-credential",
        "--project=pyeconomics-staging", "--data-file=-"],
       input=cred.encode("ascii"),
       check=True,
   )
   subprocess.run(
       ["npx", "--prefix", "tools/node", "wrangler", "secret", "put",
        "EDGE_CREDENTIAL", "--config", "tools/node/edge/wrangler.toml"],
       input=cred.encode("ascii"),
       check=True,
   )
   '
   ```

2. Check the new Secret Manager version number (metadata only):

   ```bash
   gcloud secrets versions list edge-credential \
     --project=pyeconomics-staging \
     --limit=1 \
     --format='value(name)'
   ```

3. Update the `EDGE_SECRET_VERSION` variable in the `staging` GitHub environment
   and update the Cloud Run service to pin the new version:

   ```bash
   gh variable set EDGE_SECRET_VERSION --env staging --body "<NEW_VERSION>"
   gcloud run services update pyeconomics-api-staging \
     --project=pyeconomics-staging \
     --region=us-central1 \
     --update-secrets="PYECONOMICS_EDGE_CREDENTIAL=edge-credential:<NEW_VERSION>"
   ```

4. Disable the old Secret Manager version once traffic is serving on the new
   revision:

   ```bash
   gcloud secrets versions disable "<OLD_VERSION>" \
     --secret=edge-credential \
     --project=pyeconomics-staging
   ```

### 3.2 Rotating the Upstash Redis rate-limit URL (`ratelimit-url`)

1. Rotate the database password in the Upstash console (or create a replacement
   TLS-enabled database) and copy the `rediss://` URL to the clipboard.
2. Pipe the URL into a new version of `ratelimit-url` in Secret Manager without
   echoing it:

   ```bash
   python3 -c '
   import getpass, subprocess
   url = getpass.getpass("New rediss:// URL: ").strip()
   assert url.startswith("rediss://"), "Must be a rediss:// URL"
   subprocess.run(
       ["gcloud", "secrets", "versions", "add", "ratelimit-url",
        "--project=pyeconomics-staging", "--data-file=-"],
       input=url.encode("ascii"),
       check=True,
   )
   '
   ```

3. Read the new version number, update `RATELIMIT_SECRET_VERSION` in the
   `staging` environment, and update Cloud Run:

   ```bash
   gcloud secrets versions list ratelimit-url \
     --project=pyeconomics-staging \
     --limit=1 \
     --format='value(name)'
   gh variable set RATELIMIT_SECRET_VERSION --env staging --body "<NEW_VERSION>"
   gcloud run services update pyeconomics-api-staging \
     --project=pyeconomics-staging \
     --region=us-central1 \
     --update-secrets="PYECONOMICS_RATELIMIT_URL=ratelimit-url:<NEW_VERSION>"
   ```

### 3.3 Rotating the Cloudflare Access service token

- **Service token name:** `pyeconomics-staging-ci`
- **Issued:** `2026-10-27`
- **Expires:** `2027-10-27` (1-year validity; rotate at least 14 days before
  expiry)

To rotate the service token:

1. In Cloudflare Zero Trust (`Access` -> `Service Auth` -> `Service Tokens`),
   create or refresh the token for `pyeconomics-staging-ci`.
2. Store the new Client ID and Client Secret in the `staging` GitHub environment
   (each command prompts interactively):

   ```bash
   gh secret set CF_ACCESS_CLIENT_ID --env staging
   gh secret set CF_ACCESS_CLIENT_SECRET --env staging
   ```

3. Update the maintainer's OS keyring used by local verification recipes
   (`verify-phase04.sh --live`):

   ```bash
   uv run --no-sync python -c "import getpass, keyring; keyring.set_password('pyeconomics', 'CF_ACCESS_CLIENT_ID', getpass.getpass('CF_ACCESS_CLIENT_ID:').strip()); keyring.set_password('pyeconomics', 'CF_ACCESS_CLIENT_SECRET', getpass.getpass('CF_ACCESS_CLIENT_SECRET:').strip())"
   ```

4. Dispatch `staging-health.yml` on `main` to verify the new token works end to
   end, then delete the old service token in Cloudflare Zero Trust:

   ```bash
   gh workflow run staging-health.yml --ref main
   ```

---

## 4. Disabling a Data Provider (`PYECONOMICS_DISABLED_PROVIDERS`)

If an upstream hosted-safe provider experiences an outage, rate-limit change, or
terms update, disable it on staging immediately through
`PYECONOMICS_DISABLED_PROVIDERS` (issue #162; `DataProvider._gate` enforces the
list before `check_configuration` and before any cache read, returning `503`
`source-disabled` when every candidate is disabled):

```bash
# Disable one or more providers (comma-separated provider IDs, e.g. treasury,ecb)
gcloud run services update pyeconomics-api-staging \
  --project=pyeconomics-staging \
  --region=us-central1 \
  --update-env-vars="^:^PYECONOMICS_MODE=hosted:PYECONOMICS_WORKERS=2:PYECONOMICS_DISABLED_PROVIDERS=treasury"
```

To re-enable all providers, clear `PYECONOMICS_DISABLED_PROVIDERS`:

```bash
gcloud run services update pyeconomics-api-staging \
  --project=pyeconomics-staging \
  --region=us-central1 \
  --remove-env-vars=PYECONOMICS_DISABLED_PROVIDERS
```

---

## 5. Handling a Cost Spike or Traffic Surge

The Google Cloud project carries a monthly billing budget with alerts at `50%`,
`90%`, and `100%` of the threshold and programmatic notifications delivered to
the Pub/Sub topic `staging-budget-alerts` (subscription
`staging-budget-alerts-sub`).

If a budget alert fires or abnormal traffic is observed:

1. **Cap or pause Cloud Run instances immediately:**

   ```bash
   # Lower max instances to 1
   gcloud run services update pyeconomics-api-staging \
     --project=pyeconomics-staging \
     --region=us-central1 \
     --max-instances=1

   # Or remove public invoker access to stop all origin invocations at the Google edge
   gcloud run services remove-iam-policy-binding pyeconomics-api-staging \
     --project=pyeconomics-staging \
     --region=us-central1 \
     --member="allUsers" \
     --role="roles/run.invoker"
   ```

2. **Tighten the Cloudflare rate rule or Access policy:**
   - Lower the threshold on the Cloudflare zone's free-plan rate-limiting rule
     (`staging-api-rate-limit`, matching `URI Path starts with "/"` per `IP`,
     `50 requests / 10 seconds`, `Block` for `10 seconds`).
   - If the surge comes from a compromised service token, revoke the token in
     Cloudflare Zero Trust (`Access` -> `Service Auth` -> `Service Tokens`) and
     rotate `EDGE_CREDENTIAL` using Section 3.1.

---

## 6. Free-Tier Arithmetic

Staging is sized from measured container footprints so that continuous hourly
probing (`staging-health.yml`) and normal `main` deployments (`deploy-staging.yml`)
stay inside every service's permanent free tier at `$0.00/month`:

### Container memory measurement (2 workers)

Measured on the multi-stage `python:3.14-slim-bookworm` image with
`PYECONOMICS_WORKERS=2`:

- Cold start (`uvicorn` main process + resource tracker + 2 spawned worker
  processes): `350 MiB` container cgroup memory (`194 MiB` main RSS, `151 MiB`
  per worker RSS).
- After executing models (`foundations.time_value`, `econometrics.garch`,
  `econometrics.time_series`, `fixed_income.curve_fitting`) and exporting
  `parquet` (`pyarrow`) and `xlsx` (`openpyxl`) across both workers: `505 MiB`
  peak container cgroup memory (`269 MiB` per worker RSS).
- **Cloud Run sizing:** `1 vCPU`, `1 GiB` memory (`--cpu=1 --memory=1Gi`),
  `--min-instances=0`, `--max-instances=2`, request-based billing
  (`--cpu-throttling`), `--timeout=60s`.

### Monthly usage vs. free-tier limits (31-day month)

| Service | Free-tier allowance | Hourly probes (744/mo) | Expected deploys (30/mo) | Monthly total | Share of free tier |
| --- | --- | --- | --- | --- | --- |
| **Cloud Run requests** (`us-central1`) | 2,000,000 requests | 744 × 3 = 2,232 | 30 × 7 = 210 | 2,442 requests | 0.12% |
| **Cloud Run vCPU-seconds** (`1 vCPU`, request-based) | 180,000 vCPU-s | 744 × 3.0 s = 2,232 vCPU-s | 30 × 5.0 s = 150 vCPU-s | 2,382 vCPU-s | 1.32% |
| **Cloud Run GiB-seconds** (`1 GiB`, request-based) | 360,000 GiB-s | 744 × 3.0 s = 2,232 GiB-s | 30 × 5.0 s = 150 GiB-s | 2,382 GiB-s | 0.66% |
| **Artifact Registry storage** (`us-central1`) | 500 MiB (0.5 GiB) | — | ~185 MiB/image × 2 kept | ~370 MiB | 74.0% |
| **Secret Manager** | 6 active versions; 10,000 accesses | ~1,488 cold-start accesses | ~60 accesses | 2 versions; ~1,548 accesses | 33.3% / 15.5% |
| **Upstash Redis** (`rediss://`) | 500,000 commands | 744 × 3 = 2,232 cmds | 30 × 9 = 270 cmds | ~2,502 commands | 0.50% |
| **Cloudflare Worker** (`staging-api.pyeconomics.dev`) | 100,000 requests/day | 72 requests/day | ~7 requests/day | ~79 requests/day | 0.08% |
| **Cloudflare Access** | 50 seats + service tokens | 1 service token | 1 maintainer seat | 1 seat, 1 token | 2.0% |
