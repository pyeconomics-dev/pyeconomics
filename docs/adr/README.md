# Architecture Decision Records

These records hold the decisions every phase of the pyeconomics 1.0 rebuild
builds on: what the project is, how it is packaged, versioned and licensed,
how data licences are enforced, which web and documentation stacks it uses,
what it is called, which Python versions it supports, how its data platform
works, and how its programmatic surfaces serve it. Each one starts from the
recommended default in
[ROADMAP §4 1.6](../roadmap/ROADMAP.md#16-architecture-decision-records) or the
phase section it implements, and from the §5 section behind it.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-product-boundaries.md) | Product boundaries | Accepted | 2026-10-05 |
| [0002](0002-distributions-and-extras.md) | Distributions and extras | Accepted | 2026-10-05 |
| [0003](0003-versioning-and-deprecation.md) | Versioning and deprecation | Accepted | 2026-10-05 |
| [0004](0004-licence-and-contributions.md) | Licence and contributions | Accepted | 2026-10-05 |
| [0005](0005-data-licence-model.md) | Data-licence model | Accepted | 2026-10-05 |
| [0006](0006-web-stack-and-hosting.md) | Web stack and hosting | Accepted | 2026-10-05 |
| [0007](0007-documentation-tooling.md) | Documentation tooling | Accepted | 2026-10-05 |
| [0008](0008-numerical-conventions.md) | Numerical conventions | Accepted | 2026-10-09 |
| [0009](0009-name-domains-and-trademark.md) | Name, domains and trademark | Accepted | 2026-10-05 |
| [0010](0010-python-support-policy.md) | Python support policy | Accepted | 2026-10-05 |
| [0011](0011-data-platform.md) | Data platform | Accepted | 2026-10-14 |
| [0012](0012-programmatic-surfaces.md) | Programmatic surfaces | Accepted | 2026-10-23 |

ADR-0008, the numerical conventions (decimal rates, units, bounds,
compounding and day counts, tolerances, seeds, canonical JSON numbers and the
error taxonomy), was reserved in Phase 1 and written in Phase 2 Step 1, when
the model engine first needed it (ROADMAP §4 2.1). ADR-0011, the data platform
(the value types, vintages, licence terms, the HTTP stack, credentials, the
cache, the catalog, bindings and manifest schema 2), was written in Phase 3
Step 2, before any provider code (ROADMAP §4 3.1). ADR-0012, the programmatic
surfaces (the invocation path, canonical bytes, the error table, the CLI, the
export formats, the REST and MCP shapes, hosted mode and the staging edge), was
written in Phase 4 Step 2, before any framework code (ROADMAP §4 4.1–4.7).

## Lifecycle

1. **Proposed.** A new ADR is copied from [template.md](template.md), takes
   the next free number, and opens in a pull request reading
   `Status: Proposed`.
2. **Amended in place.** Until it is accepted, the maintainer's changes are
   made directly in the file, and each one is noted under "More
   information".
3. **Accepted.** The maintainer accepts each ADR explicitly in its pull
   request. Only then does its status line read `Status: Accepted`, with
   the acceptance date on its `Date:` line and in this index.
4. **Superseded, never edited.** Once accepted, an ADR's decision does not
   change. A new ADR supersedes it: the new one says `Supersedes
   ADR-NNNN`, and the old one's status becomes `Superseded by ADR-MMMM`.
   That status change, broken links and typos are the only edits an
   accepted ADR takes, plus one exception: a dated record of an action
   the ADR itself asks to be recorded. ADR-0009's domain registrar and
   renewal month are an example.

Each ADR's "Confirmation" section names the check that enforces it and the
roadmap step that builds that check. Facts that move, such as release
dates, version floors, licences, prices and name availability, carry a
source and an access date, or read TBD.
