# ADR-0009: Name, domains and trademark

- Status: Accepted
- Date: 2026-10-05
- Deciders: Nathan Ramos, CFA (maintainer)
- Parent: ROADMAP §4 1.6 and 5.7; §5 "Legal & brand guardrails"; §1 note
  on similarly named projects; Gate G1 (§5 "Monetization strategy &
  validation gates")

## Context and problem

pyeconomics owns its PyPI name, but nothing else about its identity is
secured, and its current home breaks a rule it has set itself.

**The repository's address carries the CFA mark.**

- The repository lives at `github.com/nathanramoscfa/pyeconomics`, under
  the maintainer's personal handle, which contains "cfa".
- CFA Institute's guidance for charterholders answers "Can I use CFA/CIPM
  in a company name, product name, URL, email address, or social media
  handle?" with "No" [S1].
- ROADMAP §5 forbids "CFA" in any repository, domain or handle name.

**The domains are unregistered.**

- `pyeconomics.com`, `.org`, `.io` and `.dev` all returned "not found"
  from their registries' RDAP services on 2026-10-05: Verisign, Public
  Interest Registry, Identity Digital and Google Registry [S2].
- Nothing stops someone else from registering them once the project is
  announced.

**The GitHub name `pyeconomics` is taken.**

- `github.com/PyEconomics` is a user account created 2012-08-25, with no
  public repositories and no profile update since 2015-04-07 [S3].
- GitHub "do[es] not accept requests to release, transfer, or reclaim
  usernames on the basis that they appear inactive or unused". Only a
  valid trademark complaint can release one [S4].
- The roadmap's default organization name is therefore unavailable.

**The name may be hard to register as a trademark.**

- A mark is merely descriptive, and refused registration under Lanham Act
  §2(e)(1), if it "immediately conveys knowledge of a quality, feature,
  function, or characteristic" of the goods or services [S5].
- "PYECONOMICS" for economics software is at risk of that refusal.
- A merely descriptive mark may go on the Supplemental Register. An
  intent-to-use applicant cannot, until it has filed an acceptable
  allegation of use [S6].
- The PSF's trademark policy covers the word "Python", its logos, "PyCon"
  and "PyLadies". It places no restriction on a "Py" prefix [S7].

**Two similarly named projects exist.**

- `davidrpugh/pyeconomics`: "Computational economics in Python", 2013–14
  course code with no licence, last pushed 2014-01-16 [S8].
- pyecon.org: a site teaching Python for economics [S9].
- Neither is a package on PyPI.

## Decision drivers

- No "CFA" in any name the project uses.
- Secure the name's obvious domains before any announcement, at
  registry cost.
- Keep the trademark option open without spending on a filing that
  counsel has not advised (Gate G1).
- A neutral home that outlives the personal account and can take on
  maintainers.
- Every service that trusts the repository's identity (PyPI, TestPyPI,
  Read the Docs, branch protection, environments) keeps working after the
  move.

## Considered options

1. **Register the four domains now; search before any filing; move the
   repository to a neutral GitHub organization.** This is the roadmap's
   recommendation, with the organization renamed because `pyeconomics`
   is taken.
2. **Stay under the personal account.** No migration work, but the CFA
   mark stays in every repository, clone, issue and documentation URL,
   against CFA Institute's guidance [S1] and the project's own rule.
3. **File "PYECONOMICS" with the USPTO now.** Risks about $1,000 of fees
   [S10] on a likely descriptiveness refusal, before a search has said
   whether the name, or a coined brand, is the better bet.
4. **Claim the `pyeconomics` GitHub name.** Possible only through a
   trademark complaint [S4], which needs a registered or pending mark the
   project does not have. It stays available later, if a mark is
   registered.

## Decision outcome

Chosen option: **1**, because it removes the CFA mark from the project's
address, secures the domains for a few dollars a year, and defers the
trademark spend until a clearance search says it is worth it.

**Domains.**

- Register `pyeconomics.com`, `pyeconomics.org`, `pyeconomics.io` and
  `pyeconomics.dev` before any announcement.
- Use one registrar, with auto-renew on. The recommended registrar is
  Cloudflare Registrar, because:
  - it supports all four TLDs and sells at registry cost with no markup
    [S11];
  - it requires Cloudflare nameservers [S11], which ADR-0006 adopts
    anyway.
- `.dev` is HSTS-preloaded, so every `.dev` URL must serve HTTPS [S12].
- `.io` is a ccTLD whose future depends on the UK–Mauritius treaty on the
  Chagos Islands, signed 2025-05-22, whose UK implementing bill lapsed
  when Parliament was prorogued [S13]. If "IO" ever left ISO 3166-1, the
  retirement process allows about five years [S13]. So `.io` is held
  defensively and is never the canonical domain.
- Phase 5 chooses the canonical domain (ROADMAP §4 5.7–5.8).

**GitHub organization.**

- Create a free GitHub organization named **`pyeconomics-dev`**:
  - it follows the `pandas-dev/pandas` pattern;
  - it matches `pyeconomics.dev`;
  - it was free on 2026-10-05 [S3].
- The fallback is `pyeconomics-org`, also free [S3].
- The maintainer is its only owner, and the organization requires
  two-factor authentication for members, which the free plan supports
  [S14].
- Transfer `pyeconomics` into it, then verify every dependent setting by
  API: branch protection, rulesets, environments and their `pypi`
  reviewer, the secrets list, and Actions settings.
- Replace both trusted publishers. PyPI checks the repository owner's
  name and its numeric ID, and a transfer changes both [S15]. So a new
  publisher for `pyeconomics-dev/pyeconomics` (same workflow and
  environments) is added on PyPI and TestPyPI, and the old ones removed.
- Reconnect Read the Docs to the moved repository [S16].
- Never create a repository at `nathanramoscfa/pyeconomics` again. Doing
  so deletes GitHub's redirect from the old URL [S17].
- The private research archive `nathanramoscfa/pyeconomics-research-archive`
  stays on the personal account. It is not a public surface.

**Trademark.**

1. Commission a clearance search before any filing.
2. If counsel advises filing, file an intent-to-use application in Nice
   classes 9 (downloadable software) and 42 (software as a service)
   [S18].
   - Government fees: $350 per class to file, plus $150 per class for the
     Statement of Use. That is about **$1,000 for two classes**, using ID
     Manual descriptions [S10].
   - Free-form descriptions add $200 per class, and each six-month
     Statement of Use extension adds $125 per class [S10].
   - Attorney fees: TBD.
3. A coined brand for the hosted product stays an option, if the search
   finds "PYECONOMICS" weak.
4. The maintainer schedules the search before the Phase 5 launch at the
   latest (ROADMAP §4 5.7).

**Names and distinction.**

- No package, module, command, repository, domain, subdomain or social
  handle contains "CFA" [S1].
- Project metadata (`pyproject.toml` authors, `CITATION.cff`, the
  security contact) uses an email address without "cfa". CFA Institute's
  guidance covers email addresses too [S1].
- The README states that pyeconomics is not `davidrpugh/pyeconomics` or
  pyecon.org.

### Consequences

Executed:

- The four domains are registered with Cloudflare Registrar, with
  auto-renew on, and renew each October (registered 2026-10-06).
- 2026-11-12, Phase 5 Step 16: the clearance search is not yet done.
  Counsel was not yet engaged; the maintainer engages counsel, who
  orders the search, and the result is expected by 2026-12-15, before
  the launch readiness gate (Step 20). No filing has been advised, so
  none is made. A preliminary knockout check the same day is not the
  clearance search: the USPTO's own search refused automated requests,
  and third-party trademark aggregators showed no application or
  registration for PYECONOMICS, the nearest marks in their results being
  POPENOMICS (serial 99104869) and PIPONOMICS (serial 90127347), both
  live. The search's result and any filing counsel advises are recorded
  here when they arrive.

Good:

- The project's address no longer carries the CFA mark. Old URLs and git
  remotes keep working through GitHub's redirect [S17].
- The four domains cost registry list price only and close off
  squatting.
- An organization can add maintainers, teams and Sponsors later without
  another move.
- No trademark money is spent before a search says it is worthwhile.

Bad:

- `pyeconomics-dev` is not the bare name, and the bare GitHub name stays
  with a dormant account unless a registered mark later supports a
  complaint.
- The move touches every trust relationship. Until each is re-verified, a
  release could fail on the stale trusted publisher. Phase 1 Steps 10 and
  12 run after the move, so they test the new home.
- Annual domain renewals: four registrations, cost TBD, at registry list
  price.
- The roadmap and agent instructions name `nathanramoscfa/pyeconomics` in
  many places. Later steps must use the new owner, and the redirect
  covers what is missed.

### Confirmation

| Check | Built in |
|-------|----------|
| RDAP shows all four domains registered (`.io` through Identity Digital's RDAP) | This step's acceptance; Phase 1 Step 12 `verify-phase01.sh --live` (V6.2) |
| `gh repo view --json nameWithOwner` names `pyeconomics-dev/pyeconomics`; the old URL redirects | This step's acceptance; Phase 1 Step 12 `--live` (V6.3) |
| After the move, API reads confirm protection, rulesets, environments with the `pypi` reviewer, secrets and Actions settings; the operator confirms both trusted publishers are replaced; Read the Docs builds `latest` | This step's acceptance |
| Static check 21: no package or module path, entry point, project URL, author email or extra name contains "cfa", case-insensitive | Phase 1 Step 12 (added to its task by this step) |
| The README distinction note and the CFA notice | Phase 1 Step 11 |
| Clearance search done, and a filing made if counsel advises one | Phase 5 (ROADMAP §4 5.7; 5.9 launch readiness gate) |

## More information

- Related: ADR-0004 (licence), ADR-0006 (Cloudflare DNS), ROADMAP §5 "CFA
  Institute marks and content" and "pyeconomics' own licence, name and
  posture".
- Sources, all accessed 2026-10-05:
  - [S1] CFA Institute, Trademark Usage Guide for CFA Charterholders,
    https://www.cfainstitute.org/about/governance/policies/trademark-usage-guide-for-cfa-charterholders.
  - [S2] RDAP, HTTP 404 (not found) for each name:
    https://rdap.verisign.com/com/v1/domain/pyeconomics.com,
    https://rdap.publicinterestregistry.org/rdap/domain/pyeconomics.org,
    https://rdap.identitydigital.services/rdap/domain/pyeconomics.io
    (the same service returns 200 for a registered `.io` name), and
    https://pubapi.registry.google/rdap/domain/pyeconomics.dev.
  - [S3] GitHub REST API: `GET /users/pyeconomics` returns user
    `PyEconomics` (id 2219270, created 2012-08-25, 0 public repositories,
    updated 2015-04-07); `GET /users/pyeconomics-dev` and
    `GET /users/pyeconomics-org` return 404.
  - [S4] GitHub Username Policy,
    https://docs.github.com/en/site-policy/other-site-policies/github-username-policy.
  - [S5] TMEP 1209.01(b), merely descriptive marks,
    https://tmep.uspto.gov/RDMS/TMEP/print?version=current&href=TMEP-1200d1e7074.html.
  - [S6] TMEP 1209.01 (Supplemental Register) and TMEP 815 (intent-to-use
    applicants), https://tmep.uspto.gov/RDMS/TMEP/print?version=current&href=TMEP-1200d1e6993.html,
    https://tmep.uspto.gov/RDMS/TMEP/print?version=current&href=TMEP-800d1e2627.html.
  - [S7] PSF Trademark Usage Policy, https://www.python.org/psf/trademarks/;
    PSF trademarks FAQ, https://www.python.org/psf/trademarks-faq/.
  - [S8] https://github.com/davidrpugh/pyeconomics (no licence, created
    2012-12-14, last pushed 2014-01-16, not archived).
  - [S9] https://pyecon.org/.
  - [S10] USPTO trademark fee information (fees in effect since
    2025-01-18; base application $350 per class, Statement of Use $150
    per class, free-form text surcharge $200 per class, SoU extension $125
    per class), https://www.uspto.gov/trademarks/trademark-fee-information;
    current fee schedule,
    https://www.uspto.gov/sites/default/files/documents/USPTO-fee-schedule_current.pdf.
  - [S11] Cloudflare Registrar TLD policies, https://www.cloudflare.com/tld-policies/;
    FAQ (at-cost pricing; Cloudflare nameservers required),
    https://developers.cloudflare.com/registrar/faq/.
  - [S12] HSTS preload status for `dev`: preloaded,
    https://hstspreload.org/api/v2/status?domain=dev.
  - [S13] UK Parliament, Diego Garcia Military Base and British Indian
    Ocean Territory Bill, https://bills.parliament.uk/bills/4004; IANA
    `.io` record, https://www.iana.org/domains/root/db/io.html; ICANN,
    "The Chagos Archipelago and the .io Domain" (2024-11-14),
    https://www.icann.org/en/blogs/details/the-chagos-archipelago-and-the-io-domain-14-11-2024-en.
  - [S14] GitHub Docs, requiring two-factor authentication in your
    organization (available on GitHub Free),
    https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-two-factor-authentication-for-your-organization/requiring-two-factor-authentication-in-your-organization.
  - [S15] PyPI Docs, trusted publisher internals (`repository_owner_id`
    is always checked), https://docs.pypi.org/trusted-publishers/internals/;
    troubleshooting, https://docs.pypi.org/trusted-publishers/troubleshooting/.
  - [S16] Read the Docs, Git integration (GitHub App; connected
    repository), https://docs.readthedocs.com/platform/en/stable/reference/git-integration.html.
    The docs do not describe repository transfers, so the reconnect is
    verified by a successful build, not assumed.
  - [S17] GitHub Docs, transferring a repository (what moves; redirects;
    a new repository at the old path removes the redirect),
    https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository.
  - [S18] WIPO Nice Classification, 13th edition (version 2026-01-01),
    classes 9 and 42,
    https://nclpub.wipo.int/enfr/?class_number=9&explanatory_notes=show&lang=en&version=20260101.
