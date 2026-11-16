# ADR-0004: Licence and contributions

- Status: Accepted
- Date: 2026-10-05
- Deciders: Nathan Ramos, CFA (maintainer)
- Parent: ROADMAP §4 1.6; §5 "Dependency licences" and "pyeconomics' own
  licence, name and posture"

## Context and problem

pyeconomics 0.1.0 to 0.2.6 are MIT-licensed. The 1.0 rebuild will be:

- used by companies;
- wrapped by other projects (OpenBB, Excel add-ins, AI assistants);
- run as a hosted service by the project itself from Phase 5.

From Phase 8 it may also carry paid, hosted-only features. Its licence
must let all of that happen, protect users from patent claims by
contributors, and keep the project free to change its business model
later without asking every contributor.

The relevant facts:

- **Apache-2.0 has a patent grant; MIT does not.** Under Apache-2.0 §3,
  each contributor grants users a perpetual, royalty-free patent licence
  for their contributions. That licence ends for anyone who sues claiming
  the work infringes a patent [S1]. MIT has no patent clause.
- **Relicensing applies forward only.** A project can relicense future
  versions, while releases already published under MIT stay available
  under MIT [S2]. A sole author may relicense their own work [S3].
- **The author record allows it.** Every commit in the history is by the
  maintainer, except one Dependabot commit that bumps an action in a 0.2.x
  workflow file. Phase 1 Step 7 deletes that file.
- **AGPL reaches hosted services.** AGPL-3.0 §13 requires a modified
  program to offer its source to every user who interacts with it over a
  network [S4]. An AGPL dependency in the hosted service would reach the
  service itself.
- **OpenBB tried AGPL and left it.** OpenBB moved from AGPL-3.0-only (May
  2024) to Apache-2.0 in its v5.0.0 (2026-09-30) [S5].
- **Some neighbours' licences are incompatible.** FinancePy is
  GPL-3.0-or-later [S6]. rateslib is source-available and non-commercial
  [S7]. The DBnomics client is AGPL-3.0 [S8]. getfactormodels is AGPL-3.0
  on GitHub, with no licence in its PyPI metadata [S8]. `full_fred`'s
  repository says Apache-2.0 while its PyPI classifier says GPLv3 [S8].
  Several OpenBB provider extensions are still AGPL-3.0-only [S5].
- **DCO is a lightweight contribution certification.** The Developer
  Certificate of Origin 1.1 is a short statement that a contributor
  certifies with a `Signed-off-by:` line [S9]. The DCO GitHub App checks
  pull requests for it [S10]. GitHub's "require sign-off on web-based
  commits" setting covers web-interface commits only [S11].

## Decision drivers

- Maximum adoption, including commercial use and embedding in other
  projects.
- An explicit patent grant for users.
- The hosted service must never be forced to publish its source by a
  dependency's licence.
- Low friction for contributors. No paperwork unless a future relicence
  makes it necessary.
- A dependency's licence is checked by a machine, not remembered by a
  reviewer.

## Considered options

1. **Apache-2.0 from 1.0, DCO sign-off, permissive-only runtime
   dependencies, and paid hosted features in a separate private
   repository.**
2. **Stay MIT.** Equally permissive, but no patent grant, so users rely on
   an implied licence.
3. **AGPL-3.0, or AGPL plus a commercial licence (dual licensing).** It
   protects against hosted free-riding, but deters the companies and
   projects the open core is meant to reach. Dual licensing needs a CLA
   from every contributor. OpenBB's move away from AGPL [S5] shows the
   cost in this niche.
4. **A CLA for every contribution.** It enables any future relicence, but
   adds friction to every first contribution. That buys an option that
   option 1 keeps open in a cheaper way.

## Decision outcome

Chosen option: **1**, because it maximizes adoption, adds a patent grant,
keeps the hosted service's source private by construction, and asks
contributors for one line per commit.

**Licence.**

- The public repository is licensed **Apache-2.0 from 1.0**:
  - `LICENSE` holds the Apache License 2.0 text;
  - `pyproject.toml` declares `license = "Apache-2.0"` and
    `license-files = ["LICENSE", "NOTICE"]` (PEP 639);
  - `NOTICE` carries the project's copyright line and the attributions
    its runtime dependencies require.
- **0.2.x stays MIT.** `legacy/0.2.x` keeps its MIT `LICENSE`, and every
  0.2.x release remains MIT.
- **Hosted-only paid features** (Phase 8) live in a separate private
  repository that depends on the public package. Nothing free today
  becomes paid later.
- **No AGPL, and no dual licensing.**

**Contributions.**

- Every commit carries a `Signed-off-by:` trailer certifying DCO 1.1
  [S9], added with `git commit -s`. CI checks every commit in a pull
  request (Phase 1 Step 10), and CONTRIBUTING explains it (Phase 1 Step
  11).
- No CLA. A CLA is introduced, by a superseding ADR and before the
  contribution is merged, only if an outside contribution might ever need
  to be relicensed. Paid features live in a private repository rather
  than in relicensed public code, so that need is not expected.

**Runtime dependency allowlist.**

- Runtime dependencies, meaning everything a user installs with the
  package or any extra, must carry one of these licences:
  - `MIT`
  - `BSD-2-Clause`, `BSD-3-Clause`
  - `Apache-2.0`
  - `ISC`
  - `NCSA`
  - `PSF-2.0`
- All seven are SPDX identifiers [S12]. PSF-2.0 is permissive but not
  OSI-approved [S12]. It stays on the list because parts of Python's own
  ecosystem use it.
- A dependency with any other licence, or with no licence metadata, fails
  the check, unless an exception is recorded:
  - an amendment to this ADR before acceptance; or
  - a superseding ADR afterwards; or
  - a reviewed entry in the check's exceptions list. That entry names the
    package, its licence and why it is acceptable. One case: a
    mislabelled licence verified against the package's own `LICENSE`.
- Development and test tools (dependency groups) are outside the
  allowlist, because they are not distributed. They still pass the
  vulnerability audit.
- Excluded by name: FinancePy, rateslib, getfactormodels, the DBnomics
  client, AGPL OpenBB extensions and AGPL MCP servers, and `full_fred`
  (conflicting licence metadata).
- `blpapi` is proprietary and is never a dependency (ADR-0002).

**Note of 2026-11-16 (fonts, Phase 5 Step 17).** The web app's licence
check, `scripts/checks/web_licences.py`, which applies this decision's
permissive posture to what the site ships to browsers, admits the SIL Open
Font License 1.1 (`OFL-1.1`) for font files only, by a named rule: the two
font packages ADR-0013's amendment of the same date lists, and no other
package. The fonts are served as files, never linked into code. The OFL lets
fonts be bundled and redistributed with software, provided each copy keeps its
copyright notice and licence, and forbids selling a font by itself and a
Modified Version using a Reserved Font Name (neither chosen font declares one).
The Python runtime allowlist above is unchanged.

### Consequences

Good:

- Companies and other projects can adopt and embed pyeconomics freely,
  with an explicit patent licence.
- The hosted service's code stays private without any licence
  gymnastics.
- Contributors sign off with one flag. There are no forms.
- The licence check runs on every commit and in CI, so an excluded
  licence cannot slip in.

Bad:

- Anyone, including a competitor, may host pyeconomics. The project's
  edge must come from quality, surfaces and the hosted product, not the
  licence.
- Apache-2.0 asks redistributors to keep `NOTICE` attributions and mark
  modified files. That is slightly more than MIT asks.
- A useful library with an excluded licence must be reimplemented or left
  out.
- Without a CLA, a future move to a more restrictive licence would need
  every outside contributor's consent. That is accepted, because no such
  move is planned.

### Confirmation

| Check | Built in |
|-------|----------|
| `LICENSE` is the Apache-2.0 text; `pyproject.toml` declares `license = "Apache-2.0"` and `license-files`; `NOTICE` exists; no `®` in either | Phase 1 Step 7 |
| Licence allowlist: `scripts/checks/licences.py` over the locked runtime closure, in the pre-commit gate and as a required CI check; fails on any licence outside this list, with no metadata, or on a package excluded by name; its reviewed exceptions file starts empty | Phase 1 Step 8 (exclusions and exceptions file added to its task by this step) |
| `dco` CI job: every commit in a pull request carries a `Signed-off-by:` trailer matching its author; required on `main` | Phase 1 Step 10 |
| CONTRIBUTING explains DCO and `git commit -s`; the README and CITATION.cff state Apache-2.0 | Phase 1 Step 11 |
| Phase 8's private repository holds the paid features; the gate review records it | Phase 8 (ROADMAP §4 8.1) |

## More information

- Related: ADR-0001 (neighbours and their licences), ADR-0002
  (`blpapi`), ADR-0009 (name and trademark).
- Sources, all accessed 2026-10-05:
  - [S1] Apache License 2.0, §3 "Grant of Patent License",
    https://www.apache.org/licenses/LICENSE-2.0.
  - [S2] Kyle E. Mitchell, "Two Kinds of Relicensing" (prior MIT or Apache
    versions remain available under those terms),
    https://writing.kemitchell.com/2023/09/23/Two-Kinds-Relicensing.
  - [S3] Open Source Guides, "The Legal Side of Open Source" (a sole
    contributor may change the licence), https://opensource.guide/legal/.
  - [S4] GNU Affero General Public License v3.0, §13,
    https://www.gnu.org/licenses/agpl-3.0.html (text verified through the
    SPDX copy, https://spdx.org/licenses/AGPL-3.0-only.html).
  - [S5] OpenBB: AGPL-3.0-only from 2024-05-14 (PR #6415) to Apache-2.0
    (PR #7677, release `openbb-v5.0.0`, 2026-09-30),
    https://github.com/OpenBB-finance/OpenBB/pull/7677. Provider
    extensions dropped from v5 (for example `openbb-fmp`,
    `openbb-polygon`) and `openbb-yfinance` 2.0.0 still declare
    AGPL-3.0-only on PyPI, https://pypi.org/pypi/openbb-fmp/json; the MCP
    server `openbb-mcp-server` 2.0.1 is Apache-2.0.
  - [S6] FinancePy, https://github.com/domokane/FinancePy (PyPI 1.1.2,
    `GPL-3.0-or-later`).
  - [S7] rateslib LICENCE ("This software is not open source"),
    https://github.com/attack68/rateslib/blob/main/LICENCE.
  - [S8] DBnomics client (AGPL-3.0),
    https://git.nomics.world/dbnomics/dbnomics-python-client;
    getfactormodels (AGPL-3.0 on GitHub, no PyPI licence metadata),
    https://github.com/x512/getfactormodels; `full_fred` (Apache-2.0
    LICENSE, GPLv3 PyPI classifier), https://github.com/7astro7/full_fred.
  - [S9] Developer Certificate of Origin, Version 1.1,
    https://developercertificate.org/.
  - [S10] DCO GitHub App (`dcoapp/app`, formerly `probot/dco`),
    https://github.com/dcoapp/app.
  - [S11] GitHub Docs, managing the commit sign-off policy (web-based
    commits only),
    https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-the-commit-signoff-policy-for-your-repository.
  - [S12] SPDX License List 3.29.0 (2026-09-16),
    https://spdx.org/licenses/ (PSF-2.0 is listed as not OSI-approved).
