# International data

Install `pyeconomics[sdmx]` for IMF, OECD, ECB, BIS and Eurostat. World Bank
and DBnomics use small REST clients included in the base package. The
`pyeconomics.data.registry` discovers all seven; the generated provider pages
list their capabilities, hosts, terms and limits.

## Selecting observations

SDMX series ids are `agency/flow/key`. Search returns dataflow ids and titles;
the flow's published data structure determines the order and permitted values
of every key dimension. Supply one code for each non-time dimension. Fetch
several ids for a table; different frequencies must be fetched separately.
The provider checks the structure before sending the observation request.

| Provider | Example series id |
|----------|-------------------|
| ECB | `ECB/EXR/A.USD.EUR.SP00.A` |
| BIS | `BIS/WS_CBPOL/D.US` |
| IMF | `IMF.STA/CPI/USA.CPI._T.IX.A` |
| OECD | `OECD.SDD.STES/DSD_STES@DF_FINMARK/USA.M.IR3TIB.PA._Z._Z._Z._Z.N` |
| Eurostat | `ESTAT/prc_hicp_midx/M.I15.CP00.DE` |
| World Bank | `2/USA/NY.GDP.MKTP.CD` |
| DBnomics | `ECB/EXR/A.USD.EUR.SP00.A` |

World Bank ids select `source/country/indicator`: source 2 is World Development
Indicators. Indicator and country identities are checked against the API and
all response pages are read. A missing observation stays `None`.

DBnomics ids select `provider/dataset/series`. Search text prefixed with
`dataset:` searches its dataset catalog. Use `series:ECB/EXR:dollar`, for
example, to search series inside a dataset. Each frame credits both the
original provider and DBnomics. Its AGPL Python client is not installed.

Periods are indexed by their last day. Explicit percent units become decimals
only in the provider's transformation. These endpoints serve revised data;
frames record `revised_data`, and an unavailable historical vintage is refused.
Dataflow names, versions, keys and available dates can change upstream: use
the source's current structures rather than assuming an old IFS or DOTS key
still names an IMF dataflow.

## Reuse and attribution

IMF and DBnomics are library-only. IMF terms also prohibit LLM training without
permission, so its `llm_use` is `forbidden`; DBnomics's is `unclear` because the
original source's terms apply. Their recorded observations are synthetic.

OECD-owned data permits commercial reuse with attribution; marked third-party
or restricted data is library-only. World Bank data is hosted-safe only when
the indicator's `License_Type` explicitly says CC BY 4.0. Unknown and other
licences remain library-only and are never stored on disk. Eurostat's country and detailed-trade exceptions
override its provider classification. Hosted mode refuses restricted frames,
and the licence-aware cache enforces each returned frame's terms. DBnomics
uses memory-only reuse because its heterogeneous upstream rights cannot safely
be treated as permission to store every series.

Attribution, dataset identity, terms link and retrieval date travel with every
frame. ECB information must be identified as available free of charge before
payment and on access in a paid product. BIS data must add no charge to users.
Indicate any transformations; the library's decimal and period conversions
are explicit in its unit and source-dating metadata.

The SDMX extra uses sdmx1 (Apache 2.0), lxml and requests. The maintainer
approved the unmodified certifi certificate bundle's MPL 2.0 exception and
sdmx1's ambiguous Apache classifier on 2026-10-16. Requests are confined to
the existing transport, which owns the OS trust store, timeouts, retries,
response caps and rate limits. OECD declares its published 60-per-hour limit
(conservatively counting metadata requests too), in addition to a one-per-second
limit. No sdmx1 response cache is enabled. XML entities,
DTDs and network access during parsing are refused; source XML is suppressed
in third-party parser diagnostics.

Terms checked 2026-10-16: [IMF](https://www.imf.org/en/about/copyright-and-terms),
[OECD](https://www.oecd.org/en/about/terms-conditions.html),
[ECB](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html),
[BIS](https://data.bis.org/help/legal),
[Eurostat](https://ec.europa.eu/eurostat/help/copyright-notice),
[World Bank](https://www.worldbank.org/ext/en/legal/terms-conditions/datasets),
and [DBnomics](https://db.nomics.world/about).
