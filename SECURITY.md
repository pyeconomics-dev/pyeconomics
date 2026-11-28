# Security policy

## Supported versions

| Version                     | Supported                                                   |
|-----------------------------|-------------------------------------------------------------|
| 1.0.x (latest: 1.0.0)       | Yes. Fixes ship in the next 1.0.x release.                  |
| 1.0 pre-releases            | No. Upgrade to 1.0.0.                                       |
| 0.2.x (last: 0.2.6)         | No. End of life since 2026-11-28, the day 1.0.0 was released; upgrade to 1.0 (see the migration guide). |
| 0.1.x                       | No.                                                         |

From 1.0.0, the latest 1.x minor release is supported (ADR-0003).

## Reporting a vulnerability

Report a vulnerability privately through GitHub's private vulnerability
reporting: open the repository's
[Security tab and choose "Report a vulnerability"](https://github.com/pyeconomics-dev/pyeconomics/security/advisories/new).
Never open a public issue, discussion or pull request for a vulnerability.

Please include the affected version, a description of the issue and its impact,
and steps to reproduce it. Never include a real API key or other secret in the
report; describe where it leaks instead.

## What happens next

pyeconomics has one maintainer, so these are targets, not guarantees:

| Stage                     | Target                                                        |
|---------------------------|---------------------------------------------------------------|
| Acknowledge the report    | Within 3 business days                                        |
| Assess and rate severity  | Within 7 days, using CVSS                                     |
| Fix Critical or High      | Within 30 days, before any new feature work (ROADMAP §5 "Vulnerability handling") |
| Fix Medium or Low         | Tracked as an issue with an owner; fixed in a following release |

You are kept informed in the private advisory thread, and credited in the
advisory unless you prefer not to be.

## Advisories, yanks and key rotation

- **Advisory.** A vulnerability in a released version gets a GitHub security
  advisory naming the affected and fixed versions, a CVE where one is
  assigned, and a patched release. Example:
  [GHSA-j6rp-vwwv-jrr8](https://github.com/pyeconomics-dev/pyeconomics/security/advisories/GHSA-j6rp-vwwv-jrr8),
  the FRED API key logged by 0.2.0 to 0.2.5 and fixed in 0.2.6.
- **Yank.** A compromised or dangerously broken release is yanked from PyPI, so
  resolvers skip it unless it is pinned exactly. A published version number is
  never reused.
- **Key rotation.** When a version could have exposed a credential, such as a
  data provider's API key, the advisory tells users which keys to revoke and
  reissue at the provider. pyeconomics never needs to see a key to rotate it.
- **Releases.** Packages are published from GitHub Actions through PyPI
  Trusted Publishing with attestations; no PyPI API token exists. Verify a
  release's provenance on its PyPI page.
