# Counsel review: the launch's legal pages and licensing policy

The packet the maintainer sends to counsel before pyeconomics.dev goes public
(ROADMAP §5 "Legal & brand guardrails": counsel reviews the pages and the licensing
policy before the Phase 5 launch; ADR-0013 decision 20). Prepared in Phase 5 Step
16 on 2026-11-12. Phase 5 Step 20, the launch readiness gate, records counsel's
answers in the outcome table below; a missing review is a FAIL there unless the
maintainer waives it with a recorded reason.

**Status:** counsel's review **waived**. On 2026-11-25 the maintainer decided to
engage no counsel, for cost, and the packet was never sent. In counsel's place an
AI legal review answered its thirteen questions on 2026-11-27 (Phase 5 Step 20),
from primary sources read that day. The outcome table below records each answer
and the change it asked for. It is not counsel's review and is never described as
one. The trademark clearance search is waived with it; an AI knockout search ran
the same day (ADR-0009's entry of 2026-11-27).

What an AI review cannot do, said once: be a member of the Florida Bar, keep a
communication privileged, carry malpractice cover, or appear for the operator. A
real dispute or demand letter is the point to hire counsel.

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
  own company exists; the pages name him and hello@pyeconomics.dev. The
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

## Outcome (Step 20): the AI legal review, counsel waived

Each answer reasons from the sources named, read on 2026-11-27. Risk is for the
project as it is: free, no accounts, nothing sold, a Florida operator, visitors
from anywhere. A change "made" landed in Step 20's pull request.

| Question | The AI review's answer | Change made | Date |
|----------|------------------------|-------------|------|
| 1. Limit of liability | Holds in Florida for clearly worded terms that form a contract (question 10), never for an intentional tort; US$100 is reasonable for a free service. In the UK a cap is void for death or personal injury from negligence (Consumer Rights Act 2015 s.65(1)), and the CMA's guidance (CMA37) calls "so far as the law permits" a vague saving clause; Directive 93/13's Annex 1(a)-(b) lists such caps as possibly unfair. Both reach only a trader or supplier. Risk low. | Terms §7 rewritten: the cap covers negligence, with specific exceptions (death or personal injury from negligence, fraud, harm done on purpose, any liability the visitor's law forbids limiting, EU and UK consumer rights) in place of the vague saving sentence. The page's note removed. | 2026-11-27 |
| 2. Governing law | Florida law is sound: Florida presumes a choice of law valid (*Mazzoni Farms v. E.I. DuPont*, 761 So. 2d 306 (Fla. 2000)) and enforces a forum clause unless unreasonable or unjust (*Manrique v. Fabbri*, 493 So. 2d 437 (Fla. 1986)). Fla. Stat. 685.101-685.102 do not apply (a US$250,000 floor; personal transactions excluded). An EU or UK consumer keeps the right to sue at home, and home law's mandatory protections, where activities are directed at them (Brussels I Recast arts. 17-19; Rome I art. 6(2); UK CJJA 1982 s.15B). Risk low. | Terms §9, now "Governing law and disputes": Florida's state or federal courts only, and an EU or UK consumer may also sue at home. The page's note removed. | 2026-11-27 |
| 3. Analytics without a banner | UK: no banner needed under the statistics exception (PECR Schedule A1 para 5, in force since 2026-02-05). It needs a clear purpose and a simple, free way to object, and the ICO says not to rely on browser settings alone, so Do Not Track is not enough. EU: on the text, art. 5(3) of the ePrivacy Directive reaches a script that reads screen size and language (EDPB Guidelines 2/2023 para 33), with no analytics exemption; practical risk low (no EU establishment, no profiling, no stored address). Legitimate interests is the GDPR basis, and art. 21(4) asks for the right to object to be stated. Risk low. | Not yet made: an on-page switch that turns counting off (#406), after 1.0.0, because it is new site code and 1.0.0 is the soaked candidate. The page's note stays, relabelled "An open legal question". | 2026-11-27 |
| 4. EU or UK representative, and transfers | No representative needed: GDPR art. 3(2) is probably not met (recital 23: accessibility is not targeting; EDPB 3/2018 on monitoring), and the UK GDPR reads the same. Collecting directly from a visitor is not a transfer (EDPB 05/2021, Example 1). Safeguards, from each vendor's own page: Cloudflare, Google, Upstash, Sentry, Grafana Labs and Better Stack certify under the EU-U.S. Data Privacy Framework and its UK Extension (decision 2023/1795, upheld by the General Court in T-553/23 on 2025-09-03; appeal C-703/25 P pending); Umami and Buttondown rely on SCCs and the UK addendum in their agreements. Risk low. | The privacy policy's "Where the data goes" names each processor's safeguard and says no representative is appointed. The page's note removed. The DPF list itself (a JavaScript page) was not read; each vendor's own page was. | 2026-11-27 |
| 5. FRED at inference time | Most likely within FRED's terms, and the key holder is bound ("You agree that you will be solely responsible to the Federal Reserve Bank of St. Louis for your use of the FRED® API"). The clause bars use "in connection with the development or training" of machine learning; the Bank's own FRED® MCP Connector sends FRED content to assistants at request time, and its terms carry no such clause. The Bank's reply of 2026-11-16 did not confirm. Today pyeconomics sends FRED to no model, even on opt-in. Risk low. | FRED stays `forbidden` for language models, now by policy. `docs/ai.md` and ROADMAP §5 "Data terms" record the review in place of "a question for counsel". | 2026-11-27 |
| 6. New York Fed and OECD pass-through | New York Fed: sufficient. All five quoted conditions match its Terms of Use word for word ("Last Updated: 6/9/2023"); the notice, the "Modified by pyeconomics" label and DTCC's notice comply. On a cautious reading the product-name disclaimer reaches a page titled with a rate's name; the site serves one (EFFR), whose page shows it only in the chart's note and in files. OECD: its terms ask for "OECD (year), (dataset name),(data source) DOI or URL (accessed on (date))", and five hosted series carry only "Source: OECD. Accessed <date>." Risk low (New York Fed), medium (OECD). | Terms §4.1: section 3's limits govern the service, not the content. Not yet made, each a code change after 1.0.0: a filled OECD citation (#405) and the EFFR page's static disclaimer (#406). | 2026-11-27 |
| 7. The Pro preview | FTC Act s.5 and Florida's FDUTPA (Fla. Stat. 501.204) reach the page, but nothing is offered or paid and every statement is true. The FTC's conditions for a demand test ask that the page say the product may never exist and that sign-ups be told if it is dropped. Before the first waitlist email, CAN-SPAM needs a valid postal address (15 U.S.C. 7704(a)(5)(A)(iii)); a registered mailbox qualifies (16 CFR 316.2(p)). Risk low. | `PRO_DISCLOSURE` opens "Pro does not exist yet, and it may never be built", and the waitlist promises an email if Pro opens "or if we decide not to build it". The postal address is a task before the first send (#406). | 2026-11-27 |
| 8. Hypothetical-results legend | pyeconomics is bound by neither rule: FINRA Rule 2214 binds "a member", and CFTC Rule 4.41(b)(1) reaches the performance of a CPO, a CTA or a principal. The legend fits tools that present "the likelihood of various investment outcomes", and under Rule 2214's .01 it does not belong on deterministic calculators. As worded ("uses as a template and is not bound by"), it helps. Risk low. | None needed. | 2026-11-27 |
| 9. "Not registered with any regulator" | Accurate today. Federal: no compensation, so outside the adviser definition, and impersonal tools fit the publisher's exclusion as *Lowe v. SEC*, 472 U.S. 181 (1985), reads it. Commodities: 17 CFR 4.14(a)(9). Florida: Fla. Stat. 517.021's definition has no publisher's exclusion, and its small-adviser exclusion stops at fewer than six Florida clients, so a Florida view (the Office of Financial Regulation) comes before Pro takes money. Risk low now, medium once Pro charges. | The disclaimers state facts in place of a legal conclusion: not offered through any regulated firm, the same general tools for everyone, no adviser-client or fiduciary relationship. The Florida view is a task before Pro charges (#406). | 2026-11-27 |
| 10. Acceptance by use | Under Florida law a footer link and "by using the service you accept" do not bind a visitor to the cap, the forum or the law (*Vitacost.com v. McCants*, Fla. 4th DCA 2017; *MetroPCS v. Porter*, Fla. 3d DCA 2018; *Nguyen v. Barnes & Noble*, 9th Cir. 2014, as persuasive). Without a contract the disclaimers still work as notices, the sources' conditions as published terms and the Apache License for the software. Risk medium that the terms do not bind, low consequence. | Each sign-up form says "By joining, you accept the terms of use and the privacy policy"; terms §8 says a change applies from its date and never to the past, in place of acceptance by later use. | 2026-11-27 |
| 11. The CFA® marks | CFA Institute's guidance for webpages: "CFA®, Chartered Financial Analyst®, CIPM®, and GIPS® are registered trademarks owned by CFA Institute." Keep the non-affiliation sentence (nominative use's no-endorsement element). URLs: its guidance answers "No" to marks in identifiers that suggest affiliation; keep the neutral slugs while letter 8 (#315) is open. Risk low. | The notice reads "registered trademarks owned by CFA Institute" on the site, in `docs/notices.md`, the study paths, the README and ROADMAP §5. | 2026-11-27 |
| 12. Data sources' own terms | The library-only class is correct for the Philadelphia Fed ("informational, educational, and research purposes only"), the Atlanta Fed ("personal and educational use only"; reproduction "not for commercial gain") and the Cleveland Fed (site terms "noncommercial, personal, or educational purposes only"; the CC BY-SA 4.0 on its inflation-expectations page is unconfirmed for the workbook, whose inputs are proprietary), and so is reading FRED's terms as forbidding storage. Risk low; exports low to medium, on the user's side. | No class changes. `docs/notices.md` says a file a user exports with FRED data is their own copy, kept under FRED's terms. | 2026-11-27 |
| 13. Children and deletion | Children: adequate (COPPA, 16 CFR 312.3, reaches sites directed to children under 13 or with actual knowledge; GDPR art. 8, only services offered directly to a child). A month's answer meets GDPR art. 12(3). Deletion: erasure on request answers an explicit request, but unsubscribing withdraws consent, a ground for erasure under art. 17(1)(b), and Buttondown keeps unsubscribed records. Florida's Digital Bill of Rights does not apply (over US$1 billion a year), and its breach statute (501.171) does not reach an email-only list. Risk medium for deletion, low otherwise. | The newsletter's retention text drops a reason that did not fit (pyeconomics imports no address). Not yet made: Buttondown's hard deletion (#306) and a monthly erasure of unsubscribed addresses (#406). | 2026-11-27 |

Sent to counsel: never (waived 2026-11-25).
