# Counsel review: the launch's legal pages and licensing policy

The packet the maintainer sends to counsel before pyeconomics.dev goes public
(ROADMAP §5 "Legal & brand guardrails": counsel reviews the pages and the licensing
policy before the Phase 5 launch; ADR-0013 decision 20). Prepared in Phase 5 Step
16 on 2026-11-12. Phase 5 Step 20, the launch readiness gate, records counsel's
answers in the outcome table below; a missing review is a FAIL there unless the
maintainer waives it with a recorded reason.

**Status:** ready to send. Counsel was not yet engaged on 2026-11-12; the maintainer
engages counsel and sends this packet, and records the date sent here. The
trademark clearance search (ADR-0009) is expected by 2026-12-15, ordered through
counsel.

## What pyeconomics is

- A free, open-source Python library of economics and finance models (formula
  calculators, pricing models, regressions, simulations of user-defined rules), with
  cited formulas and tested values, under the Apache License 2.0
  (https://github.com/pyeconomics-dev/pyeconomics).
- The same models through a command line, a REST API, an MCP server for AI
  assistants, a local web app, and a hosted website, pyeconomics.dev, which is
  non-commercial at launch: free, no advertising, no accounts, nothing sold. A paid
  "Pro" tier is only previewed (/pro/), and nothing can be bought.
- Data comes from public agencies and research sources, each under its own terms,
  classified by those terms into where its data may go (ADR-0005).
- Operated by Nathan Ramos, the maintainer, as an individual, until the project's
  own company exists; the pages name him and nathan.ramos.github@gmail.com. The
  maintainer briefs counsel directly on the entity, its timing and his own
  professional obligations; none of that is recorded in this public repository.

## What to review

Production is behind Cloudflare Access until the cutover (Step 21): the maintainer
sends counsel each page as a PDF printed from production, and the source of each
is public at the repository paths given.

| Document | Page | Source |
|----------|------|--------|
| Terms of use | https://pyeconomics.dev/legal/terms/ | `web/src/pages/legal/terms/index.astro` |
| Privacy policy | https://pyeconomics.dev/legal/privacy/ | generated from `web/src/content/legal/data-flows.json` by `web/src/pages/legal/privacy/index.astro` |
| Disclaimers | https://pyeconomics.dev/legal/disclaimers/ | `web/src/pages/legal/disclaimers/index.astro` |
| Data sources and licences | https://pyeconomics.dev/sources/ | generated from provider metadata by `web/src/pages/sources/index.astro` |
| Licence | https://pyeconomics.dev/legal/licence/ | `LICENSE`, `NOTICE` and `web/src/lib/licences.ts` |
| security.txt | https://pyeconomics.dev/.well-known/security.txt | `web/src/lib/security-txt.ts` |
| The Pro preview | https://pyeconomics.dev/pro/ | `web/src/pages/pro/index.astro`, `web/src/lib/pro.ts` |
| The data flows | | `web/src/content/legal/data-flows.json` (every processor, what it holds, where, for how long, and its agreement) |
| The data licensing policy | | `docs/roadmap/ROADMAP.md` §5 "Data licensing policy" and ADR-0005 |
| The legal and brand guardrails | | `docs/roadmap/ROADMAP.md` §5 "Legal & brand guardrails" |
| The permission letters | | `docs/operations/permissions.md` |
| Name, domains and trademark | | ADR-0009 |

## The questions

Each question names where the pages stand today. The pages mark questions 1 to 4
where they arise, in these words, until counsel answers.

1. **The limit of liability.** The terms cap liability at US$100 and exclude
   indirect damages. The page's note: the amount of the cap, and whether the limits
   hold for readers in the EU and the UK.
2. **The governing law.** The terms name the State of Florida, United States, where
   the maintainer lives. The page's note: the governing law, and where a dispute is
   heard.
3. **Analytics without a banner.** The site counts visits with Umami Cloud: no
   cookie, no stored IP address, a visitor hash from a monthly salt, Do Not Track
   honoured (ADR-0013 decision 13). The page's note: Whether cookie-less analytics
   needs a consent banner in the EU and the UK: Umami's pricing page says none is
   needed, while its documentation says that depends on the site's setup.
4. **An EU or UK representative, and transfers.** Most processors are in the United
   States. The page's note: whether pyeconomics needs a representative in the EU or
   the UK, and the safeguards each transfer relies on.
5. **FRED content at inference time.** The hosted site never serves FRED. Locally, a
   user's own AI assistant can call pyeconomics' MCP server, which reads FRED with
   the user's own key and passes values to the assistant at the time of the request,
   never for training; FRED's terms bar using its content "in connection with the
   development or training" of machine learning. Is passing values at inference time
   within the FRED terms, and is the user or pyeconomics the party bound? Today the
   MCP server passes data from a source whose AI terms are unclear only when the
   user opts in, and FRED's are classed as forbidding it (ROADMAP §5 "Data terms").
   The St. Louis Fed is asked the same question (`permissions.md` letter 1).
6. **The New York Fed's and the OECD's pass-through.** The terms of use quote and
   pass on the New York Fed's conditions (same permissions, no more restrictive
   terms, notices kept, no implied endorsement, modifications labelled) and the
   OECD's (citation, and the same acknowledgement required of sub-licensees). Each
   New York Fed reference rate carries the Terms of Use's notice, the disclaimer the
   Terms ask of a service that names a rate, the label "Modified by pyeconomics: the
   published percentages are shown as decimals", and, on SOFR and BGCR, DTCC
   Solutions' notice. Is this sufficient, and does the product-name disclaimer reach
   pages titled with a rate's name (for example the SOFR data page)?
7. **The Pro preview's wording.** /pro/ leads with the statement that Pro does not
   exist and nothing is sold, shows indicative prices "not an offer", and takes only
   a waitlist sign-up. Is that wording safe as a pre-launch demand test?
8. **The hypothetical-results legend.** Models whose outputs are simulated or
   hypothetical (Monte Carlo, historical simulation, backtests; chosen by registry
   tags) carry FINRA Rule 2214(c)(4)'s legend, adapted, beside their results, and a
   model that simulates futures would add CFTC Rule 4.41(b)(1)'s statement.
   pyeconomics is not a FINRA member or a CTA; are these the right templates, and is
   the scope right (FINRA's .01 excludes illustrations of mathematical principles)?
9. **"Not registered with any regulator".** The disclaimers say pyeconomics is not
   registered with any regulator and offers no service that would require it,
   relying on the publisher's exclusion for impersonal, general tools (ROADMAP §5,
   the adviser posture). Is the statement accurate and sufficient?
10. **Acceptance of the terms.** The terms bind by use ("By using the service you
    accept these terms"), linked from every page's footer, with no click-through.
    Is that enough for a free service with no accounts?
11. **The CFA® marks.** The site uses the notice ROADMAP §5 fixes ("CFA® and
    Chartered Financial Analyst® are trademarks owned by CFA Institute. pyeconomics
    is not affiliated with, endorsed by, or a Prep Provider of CFA Institute."); CFA
    Institute's own footer says "registered trademarks". Syllabus mappings use
    neutral slugs; CFA Institute is asked about URL paths (`permissions.md` letter
    8).
12. **Data sources' own terms.** ADR-0005's classification of every source, the
    hosted-safe list above all (`/sources/`), and the reading of terms that prohibit
    storage (FRED) or allow only noncommercial use (the Philadelphia, Atlanta and
    Cleveland Feds; the Cleveland Fed's page now shows CC BY-SA 4.0).
13. **Children and deletion.** The privacy policy says the site is not directed at
    children under 16, and promises an answer to a data-rights request within a
    month; the email processor soft-deletes an unsubscribed address and erases it on
    request. Is that adequate?

## Outcome (Step 20)

| Question | Counsel's answer | Change made | Date |
|----------|------------------|-------------|------|
| | | | |

Sent to counsel: not yet.
