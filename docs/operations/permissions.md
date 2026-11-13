# The permissions programme

pyeconomics' hosted site (pyeconomics.dev) serves a source's data only when the
source's terms allow a third-party service to display it (ADR-0005; ROADMAP §5
"Data licensing policy"). Eight sources the models read are `library-only` today:
users read them on their own computers, under their own acceptance of the terms,
and the hosted site does not serve them. These letters ask each owner whether the
hosted site may, and one asks CFA Institute about its mark in URL paths (ROADMAP
§4 5.7; ADR-0013 decision 20).

The rules:

- **A grant becomes a reclassification pull request**, with the answer quoted in
  the provider's metadata, the provider's tests, the catalog's and the snapshot
  set's tests, and a changelog entry (ADR-0005 rule 7). The hosted snapshot
  follows only once that merges. Nothing in this file changes a licence class.
- **A partial or conditional grant** is applied as written, and nothing more.
- **Silence leaves the source library-only.** One follow-up goes out 30 days after
  the letter; after that, no further chasing. No launch item waits for an answer.
- Each letter has a tracking issue labelled `permissions`. The table below records
  the date each was sent and the answer; the issue holds the correspondence's
  summary (never an address beyond the institution's published contact).
- The letters name only the maintainer's published name and the project's
  published address, nathan.ramos.github@gmail.com. The contacts are those each
  institution publishes, with the page that publishes it.

Written in Phase 5 Step 16 (2026-11-12), from each institution's terms and contact
pages read that day.

## Tracking

| Recipient | Published contact | Sent | Issue | Answer | Outcome |
|-----------|-------------------|------|-------|--------|---------|
| Federal Reserve Bank of St. Louis (FRED, ALFRED) | stlsFRED@stls.frb.org ([FRED legal page](https://fred.stlouisfed.org/legal/): "For comments or questions about the data in the FRED® database, we prefer you send an email to stlsFRED@stls.frb.org"; the [contact form](https://fred.stlouisfed.org/contactus/) is the other route) | 2026-11-12, by email | #308 | | |
| Kenneth R. French (Data Library) | kfrench@dartmouth.edu ([contact page](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/contact_Information.html)) | 2026-11-12, by email | #309 | 2026-11-13, by email from Professor French: we may not include the data in software we distribute. Told the same day that the library downloads his files at a user's request, he wrote that this is fine, and that he may rescind the permission | Declined: `ken_french` stays library-only; nothing we distribute holds the data; the run-time download continues with his consent, which he may rescind (section 2) |
| Robert J. Shiller (US stock market data and CAPE) | laurence.black@theindexstandard.com ([Professor Shiller's data page](http://www.econ.yale.edu/~shiller/data.htm), "For questions or more information") | 2026-11-12, by email | #310 | 2026-11-13, by email: they cannot permit showing S&P data, which belongs to S&P; they named S&P's licensing contact. The file's new layout is expected within two months (#324) | Declined: `shiller` stays library-only; no S&P licence sought (section 3) |
| International Monetary Fund | copyright@imf.org ([copyright and usage](https://www.imf.org/en/about/copyright-and-terms)) | 2026-11-12, by email | #311 | 2026-11-13: an automatic reply only, pointing to the Copyright Clearance Center; no answer from a person yet | |
| Federal Reserve Bank of Philadelphia (RTDSM, SPF) | PHIL.SPF@phil.frb.org, copy Casey.Ross@phil.frb.org ([SPF documentation](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters); [RTDSM page](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists)) | 2026-11-12, by email | #312 | | |
| Federal Reserve Bank of Atlanta (GDPNow) | [GDPNow inquiry form](https://www.atlantafed.org/en/research-and-data/data/gdpnow/gdpnow-inquiry) | 2026-11-12, by web form | #313 | | |
| Federal Reserve Bank of Cleveland (inflation expectations) | public.information@clev.frb.org ([inflation expectations](https://www.clevelandfed.org/indicators-and-data/inflation-expectations), "For further information") | 2026-11-12, by email | #314 | | |
| CFA Institute (the mark in URL paths) | trademark@cfainstitute.org ([trademark guidance](https://www.cfainstitute.org/programs/candidate-resources/share-achievement)) | 2026-11-12, by email | #315 | | |

All eight letters went out on 2026-11-12: seven by email from
nathan.ramos.github@gmail.com, sent at the maintainer's request through the Gmail API
with a send-only grant revoked after sending, and the Atlanta Fed's through its web
form. Follow-ups are due on 2026-12-12.

## What each letter asks

Every letter describes pyeconomics the same way and asks about the same four uses,
leaving out a use that does not apply:

1. **Display** on pyeconomics.dev: the series in charts and in model results.
2. **Snapshots:** a daily copy, kept privately on the site's server, of only the
   series the models use, refreshed from the owner's published files, so the site
   never calls the owner's servers per visit.
3. **Downloads:** the same series and model results as CSV, Excel, Parquet, Arrow
   and JSON files, each carrying the attribution and the owner's notices.
4. **AI assistants:** passing the values, at the time of a request (never for
   training), to an AI assistant a visitor connects to the site through the Model
   Context Protocol.

Each offers the attribution the owner prescribes, says the site is non-commercial
at launch (free, no advertising, nothing sold), says values are never modified but
for percentages shown as decimals (labelled), and promises removal on request.

## The letters

### 1. Federal Reserve Bank of St. Louis: FRED® and ALFRED®

Email stlsFRED@stls.frb.org, the address FRED's legal page prefers for questions
about its data (its [contact form](https://fred.stlouisfed.org/contactus/), topic
"Permissions to use the Data", is the other route). FRED's terms forbid
storing or caching FRED content, and the Bank cannot grant permission for series
owned by third parties, so the letter asks only about what the Bank owns.

> **Subject:** Permission request: FRED and ALFRED data on a non-commercial, open-source model site
>
> Dear FRED team,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its users can read FRED and ALFRED series on their own computers through the FRED API, with their own API keys and under the FRED API Terms of Use; pyeconomics never stores or caches FRED content, and shows your required notice.
>
> We are preparing a website, pyeconomics.dev, that runs the same models in a browser and charts the data they use. It is non-commercial at launch: free, with no advertising and nothing for sale. The site serves only data whose owner allows a third-party service to display it, so it reads public series from the agencies that publish them and does not use FRED at all.
>
> We understand the Bank cannot grant permission for series owned by third parties. For data the Bank itself owns or compiles, above all the ALFRED vintages of series whose originators keep no history of revisions, may pyeconomics.dev:
>
> 1. display those series in charts and model results, with the citation you prescribe and a link to FRED;
> 2. keep a daily copy of only the series its models use on its own server, refreshed through the API, so it never calls FRED per visit;
> 3. offer those series and model results as downloadable files, each carrying the citation and your notice; and
> 4. pass those values, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> Separately, a user who runs pyeconomics on their own computer with their own FRED API key can connect their own AI assistant to it. May FRED content reach that assistant at the time of the user's request? It would never be used for training.
>
> We would never imply the Bank's endorsement, would use no FRED mark in a hostname, and would remove the data at once on request. If you can grant only some of these, or under conditions, we will follow them exactly; if we do not hear back, FRED stays available only on users' own computers.
>
> Thank you for FRED, and for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

### 2. Kenneth R. French: the Data Library

Email kfrench@dartmouth.edu. The files are copyright Eugene F. Fama and Kenneth R.
French, and they draw on CRSP and, for the one-month bill, Ibbotson Associates and
ICE BofA, so the letter asks about the authors' rights and acknowledges the inputs.

> **Subject:** Permission request: Fama/French factor data on a non-commercial, open-source model site
>
> Dear Professor French,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its factor regression, asset pricing test and portfolio models can read files from your Data Library (the Fama/French 3 and 5 factors, the momentum factor, the 12 and 49 industry portfolios and the 25 size and book-to-market portfolios) on a user's own computer, fetched at run time with the attribution "Source: Eugene F. Fama and Kenneth R. French, Data Library" and your copyright line, and never bundled with the software.
>
> We are preparing a website, pyeconomics.dev, that runs the same models in a browser. It is non-commercial at launch: free, with no advertising and nothing for sale. The site serves only data whose owner allows it, so today those models there ask visitors for their own data instead.
>
> May pyeconomics.dev, with that attribution and a link to the Data Library:
>
> 1. display those returns in charts and model results;
> 2. keep a daily copy of only the files its models use on its own server, refreshed from your published files;
> 3. offer the returns its models use, and the models' results, as downloadable files, each carrying the attribution; and
> 4. pass those values, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> We know the files draw on CRSP and other sources; if your permission cannot cover those inputs, we would be grateful to know whom to ask. We would ask Professor Fama too if you prefer, would never imply endorsement, and would remove the data at once on request. If we do not hear back, the Data Library stays available only on users' own computers.
>
> Thank you for the Data Library, and for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

**Answer (2026-11-13).** Professor French replied himself: "I'm sorry, but you
may not include the data in software you distribute."

**Follow-up (2026-11-13).** Our thanks told him that the site will not use his data,
that nothing we distribute contains it, and that the library's code downloads his
files from his site to a user's own computer when the user asks. It offered to remove
that download if he preferred. He answered: "That's all fine. Thanks. Please be
forewarned, this permission may be rescinded in the future."

**Outcome.** Declined. `ken_french` stays library-only and the hosted site never
serves it, so the live data of `asset_pricing.factor_regression`,
`asset_pricing.factor_model_tests`, `econometrics.garch`,
`portfolio.black_litterman` and `portfolio.risk_based_allocation` runs on a user's
own computer only. An audit the same day found the data in nothing we distribute:

- the wheels hold the provider's code, which downloads the files from his site at
  run time, on the user's machine;
- the provider's cassettes (in the sdist) are synthetic, as every library-only
  source's must be;
- the five models' golden cases cite papers, NIST StRD and identities; and
- their worked examples (on the site and in the app wheel) are invented or
  seeded-simulated values.

Keep it so: no file of his, or values copied from one, is ever committed,
packaged, cached on our servers or shown on the site. Issue #309 is closed as
declined.

The library's run-time download continues with his consent. If he rescinds it, open
an issue that day to retire the provider in the next release. Until that release
ships, users can switch the provider off with the `disabled_providers` setting
(`PYECONOMICS_DISABLED_PROVIDERS`).

### 3. Robert J. Shiller: US stock market data and the CAPE ratio

Email laurence.black@theindexstandard.com, the address Professor Shiller's Yale data
page gives "for questions or more information" (shillerdata.com publishes none). The
file's earnings and dividends are derived from S&P data, so the letter asks about
what the authors can grant.

> **Subject:** Permission request: the U.S. stock market and CAPE data on a non-commercial, open-source model site
>
> Dear Mr Black,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its CAPE and equity models can read Professor Shiller's "US Stock Price, Earnings and Dividends as well as Interest Rates and Cyclically Adjusted Price Earnings Ratio (CAPE) since 1871" (ie_data.xls) on a user's own computer, with the attribution "Source: Robert J. Shiller" and the notice the file carries. Professor Shiller's Yale data page names you for questions.
>
> We are preparing a website, pyeconomics.dev, that runs the same models in a browser. It is non-commercial at launch: free, with no advertising and nothing for sale. The site serves only data whose owner allows it, so today the CAPE model there asks visitors for their own data instead.
>
> May pyeconomics.dev, with that attribution, the file's notice and a link to shillerdata.com:
>
> 1. display the series in charts and model results;
> 2. keep a daily copy of only the columns its models use on its own server, refreshed from the published file;
> 3. offer those columns and the models' results as downloadable files, each carrying the attribution and notice; and
> 4. pass those values, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> We understand the earnings and dividends draw on S&P data; if a permission cannot cover them, we would be grateful to know whom to ask. We would never imply endorsement and would remove the data at once on request. If we do not hear back, the data stays available only on users' own computers.
>
> Thank you for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

**Answer (2026-11-13).** Laurence Black, Index Advisor to Robert Shiller, replied
that they cannot give permission to show S&P data, because it belongs to S&P. He
named a licensing contact at S&P Dow Jones Indices, which answers the letter's
question of whom to ask. He added that the data file's structure will change
shortly (#324). A permission to publish covers its holder, not those who copy the
file, so the hosted site needs S&P's licence, not the authors'.

**Follow-up (2026-11-13).** We asked when the new file will be published, so that the
library's reader can follow it. He answered: "I would expect it to be in the next 2
months". That means by mid-January 2027. #324 makes the provider read its columns by
header and refuse a layout it does not know. It must land before the release
candidate (Step 19), so that no frozen release reads a changed file without noticing.

**Outcome.** Declined. `shiller` stays library-only with no change: the library
still reads the file on a user's own computer, under that user's acceptance of the
terms, and the hosted site never serves it, so `equity.cape`'s live data runs
locally only. No S&P licence is sought. Redistributing licensed data is out of
scope in every phase (ROADMAP §6), and an index-data licence would cost money a
free site does not earn. Issue #310 is closed as declined.

### 4. International Monetary Fund

Email copyright@imf.org. The IMF's terms let users distribute its statistical data
with attribution, but ask for permission for commercial reuse and for automated bulk
download, and bar training language models without permission; a daily snapshot is
an automated download, so the letter asks for exactly that.

> **Subject:** Permission request: IMF statistical data on a non-commercial, open-source model site
>
> Dear IMF Permissions Manager,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its users can read IMF statistical data (for example the consumer price indices) through the IMF's SDMX API on their own computers, with the attribution "Source: International Monetary Fund, <database name>, <link to the dataset>".
>
> We are preparing a website, pyeconomics.dev, that runs the same models in a browser and charts the data they use. It is non-commercial at launch: free, with no advertising and nothing for sale. The site serves only data whose owner allows it, and your terms ask for permission for automated downloads, so it does not serve IMF data today.
>
> May pyeconomics.dev, with that attribution:
>
> 1. display IMF series in charts and model results;
> 2. download once a day, through the SDMX API, only the series its models use, and keep that copy privately on its own server, so it never calls the IMF per visit;
> 3. offer those series and the models' results as downloadable files, each carrying the attribution and the statement that the data is available free of charge from the IMF; and
> 4. pass those values, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> We would never alter the data except to show percentages as decimals, which we label, would never imply the IMF's endorsement, and would remove the data at once on request. If we do not hear back, IMF data stays available only on users' own computers.
>
> Thank you for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

**Automatic reply (2026-11-13).** The copyright mailbox answered at once that
permission to reuse IMF content is cleared through the Copyright Clearance Center
(www.copyright.com). No person has answered. The source stays library-only, and the
follow-up on 2026-12-12 stands.

### 5. Federal Reserve Bank of Philadelphia: the RTDSM and the SPF

Email PHIL.SPF@phil.frb.org, with a copy to Casey.Ross@phil.frb.org, whom the SPF
documentation and the RTDSM page both name, for the Real-Time Data Research Center.
The Bank's terms allow informational, educational and research use only.

> **Subject:** Permission request: the Real-Time Data Set and the SPF on a non-commercial, open-source model site
>
> Dear Real-Time Data Research Center,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its policy-rule and forecasting models can read the Real-Time Data Set for Macroeconomists and the Survey of Professional Forecasters on a user's own computer, with the attribution "Source: Federal Reserve Bank of Philadelphia. Croushore and Stark (2001), A Real-Time Data Set for Macroeconomists."
>
> We are preparing a website, pyeconomics.dev, that runs the same models in a browser. It is non-commercial at launch: free, with no advertising and nothing for sale, and educational in purpose. Your terms allow informational, educational and research use; because a public website could be read as more than that, the site does not serve your data today.
>
> May pyeconomics.dev, with that attribution and a link to your pages:
>
> 1. display the RTDSM and SPF series its models use, in charts and model results;
> 2. keep a daily copy of only those series on its own server, refreshed from your published files;
> 3. offer those series and the models' results as downloadable files, each carrying the attribution; and
> 4. pass those values, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> We would never use the Bank's name to endorse anything, would remove the data at once on request, and would follow any conditions you set. If we do not hear back, your data stays available only on users' own computers.
>
> Thank you for the Real-Time Data Set and the SPF, and for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

### 6. Federal Reserve Bank of Atlanta: GDPNow

Send through the [GDPNow inquiry form](https://www.atlantafed.org/en/research-and-data/data/gdpnow/gdpnow-inquiry).
The GDPNow page grants reproduction "for personal and educational use only"; the
Bank's terms of use allow reproduction "not for commercial gain or monetary profit"
with attribution.

The form's Question field takes at most 512 characters, and its server refuses as
"invalid input" both a version with quotation marks, apostrophes, parentheses and a
slash and one naming the site's domain. So the form carried this plain 469-character
version of the letter below, submitted on 2026-11-12 (the page answered "You should
receive a response within 48 hours"); the full letter goes by email if the team asks
for detail:

> I maintain pyeconomics, a free and open source Python library of economics models, published on GitHub as pyeconomics-dev. May our non-commercial website display the GDPNow estimates in charts, keep a daily copy, offer them as downloads and pass them to an AI assistant a visitor connects, never for training, each credited to the Federal Reserve Bank of Atlanta, GDPNow? Until you allow it, GDPNow stays on the computers of our users only. Thank you. Nathan Ramos, CFA

The full letter:

> **Subject:** Permission request: GDPNow on a non-commercial, open-source model site
>
> Dear GDPNow team,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). It can read GDPNow's own estimates (the current estimate and the historical tracking workbook, never the Blue Chip forecasts) on a user's own computer, with the attribution "Source: Federal Reserve Bank of Atlanta, GDPNow."
>
> We are preparing a website, pyeconomics.dev, that runs models in a browser and charts the data they use. It is non-commercial at launch: free, with no advertising and nothing for sale. The GDPNow page permits reproduction for personal and educational use only, so the site does not serve GDPNow today.
>
> May pyeconomics.dev, with that attribution and a link to the GDPNow page:
>
> 1. display GDPNow's estimates in charts;
> 2. keep a daily copy of those estimates on its own server, refreshed from your published workbook;
> 3. offer the estimates as downloadable files, each carrying the attribution; and
> 4. pass them, at the time of a request and never for training, to an AI assistant a visitor connects to the site?
>
> We would never use the Bank's name to endorse anything, would send you a copy of any reproduced content if you wish, and would remove the data at once on request. If we do not hear back, GDPNow stays available only on users' own computers.
>
> Thank you for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

### 7. Federal Reserve Bank of Cleveland: inflation expectations

Email public.information@clev.frb.org. Since the provider was classified (from the
Bank's 2022 terms: noncommercial, personal or educational use), the inflation
expectations page has added "This work by Federal Reserve Bank of Cleveland is
licensed under Creative Commons Attribution-ShareAlike 4.0 International" (read
2026-11-12). The letter asks the Bank to confirm that the licence covers the data
file, which would make the source hosted-safe under its terms.

> **Subject:** Question: does the CC BY-SA 4.0 licence cover the inflation expectations data file?
>
> Dear Public Information Office,
>
> I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). It can read the Bank's inflation expectations, real interest rates and risk premia (the inflation-expectations workbook) on a user's own computer, with the attribution "Source: Federal Reserve Bank of Cleveland" and your suggested citation.
>
> The inflation expectations page now says the work is licensed under Creative Commons Attribution-ShareAlike 4.0 International, while the Bank's terms of use (last updated April 13, 2022) allow reproduction for noncommercial, personal or educational purposes. We are preparing a website, pyeconomics.dev, that runs models in a browser and charts the data they use; it is non-commercial at launch. Could you confirm:
>
> 1. whether the CC BY-SA 4.0 licence covers the data in the downloadable workbook, as well as the page; and
> 2. if it does, that pyeconomics.dev may display the series, keep a daily copy of them on its server, offer them as downloadable files and pass them to an AI assistant a visitor connects to the site, each with your citation, the licence named and the share-alike terms passed on?
>
> We would never use the Bank's name to endorse anything and would remove the data at once on request. Until we hear from you, the data stays available only on users' own computers.
>
> Thank you for considering this.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics

### 8. CFA Institute: the mark in URL paths and filter values

Email trademark@cfainstitute.org. CFA Institute's guidance answers "No" to the mark
in "a company name, product name, URL, email address, or social media handle", and
publishes no rule that tells a URL's path from its domain, so the site keeps neutral
slugs until it answers (ROADMAP §5 "CFA Institute marks and content"; ADR-0013
decisions 2 and 12).

> **Subject:** Question about the CFA® mark in URL paths on a non-affiliated open-source site
>
> Dear Legal Services Group,
>
> I am a CFA charterholder, and I maintain pyeconomics, a free, open-source (Apache-2.0) Python library of economics and finance models with cited formulas and tested values (https://github.com/pyeconomics-dev/pyeconomics). Its website, pyeconomics.dev, maps its models to the topic areas of the 2027 CFA® Program as factual tags that link to cfainstitute.org. It copies no curriculum content, sells no exam preparation, uses no logo, and carries this notice on every page: "CFA® and Chartered Financial Analyst® are trademarks owned by CFA Institute. pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute."
>
> Your trademark guidance answers "No" to using the marks in a URL. Today the site and its documentation therefore use neutral identifiers in their addresses, for example pyeconomics.dev/models/?level=1&topic=l1-fixed-income and docs.pyeconomics.dev/en/main/study-paths/analyst-program-2027/. Could you tell us:
>
> 1. whether we may use "cfa" in the path or query of a page address on our own domains, such as /study-paths/cfa-program-2027/ or ?syllabus=cfa-program-2027, for these factual mapping pages; and
> 2. whether you would prefer different wording for the notice above, such as "registered trademarks", which your website's footer uses?
>
> We will keep the neutral identifiers unless you say otherwise, and will follow any conditions you set.
>
> Thank you for your guidance.
>
> Nathan Ramos, CFA
> Maintainer, pyeconomics
> nathan.ramos.github@gmail.com · https://github.com/pyeconomics-dev/pyeconomics
