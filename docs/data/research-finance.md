# Research finance and market data

These providers fetch data at runtime. Every result carries its source, units,
terms, attribution and retrieval time. Library-only data stays on the user's
machine; hosted mode refuses it before consulting the cache or making a request.
The offline test recordings for these sources contain synthetic numbers.

| Provider | Example `Query.series` item | Result and source units |
|---|---|---|
| `ken_french` | `ff5:monthly`, `ff3:annual`, `momentum:daily`, `size_bm25:monthly` | Factor/portfolio tables; percent returns become decimals |
| `shiller` | `us_equity` | Monthly price, dividend, earnings, CPI, long rate and CAPE; the long rate becomes decimal |
| `damodaran` | `implied_erp`, `country_risk:united_states`, `industry_betas:advertising`, `industry_multiples:advertising` | Credited aggregates; Excel percentages are already decimals |
| `aqr` | `bab:monthly`, `bab:daily`, `qmj:monthly` | Country/region factors; source returns are already decimals |
| `hou_xue_zhang` | `q5:monthly`, `q5:daily`, `q5:annual`, `benchmark:monthly` | Current 2025-release q5 factors and benchmark portfolios; percent returns become decimals |
| `jkp` | `usa:be_me:monthly:vw`, `usa:ret_12_1:daily:vw_cap` | Country/factor excess returns in USD, already decimals |
| `open_source_asset_pricing` | `predictor_long_short` | Monthly long-short returns of the 2025.10 release's predictors; percent returns become decimals |
| `cboe` | `vix` | Daily open, high, low and close; percent volatility becomes decimal |
| `coin_metrics` | `btc:PriceUSD:SplyCur`, `eth:TxCnt` | Community daily asset metrics, retaining their own USD/native/count units |
| `yfinance` | `prices:IBM`, `fundamentals:IBM`, `options:IBM:calls` | Personal-use local session; see the opt-in below |

For example, fetch the French five-factor monthly table with:

```python
from pyeconomics.data import Query, registry

factors = registry.get("ken_french").fetch(
    Query(series=("ff5:monthly",), start="2020-01-01", end="2024-12-31")
)
```

Each query selects one dataset, preserving its native frequency and calendar.
Monthly observations use month-end dates, annual observations December 31, and
daily observations their actual date. The French library's `-99.99` and `-999`
markers become `None`. Its monthly and annual sections remain separate; append
`:equal` to a portfolio id to select equal-weighted returns. The default is
value-weighted returns. Counts, firm sizes and valuation-ratio sections are not
read as portfolio returns. The library's move to CRSP CIZ is recorded in notes.

Shiller's `1871.01` is a January 1871 label, not an Excel serial date. CAPE is a
ratio, not a percentage. AQR and JKP decimal returns pass through unchanged.
Open Source Asset Pricing uses a small in-house client for the authors' published
wide CSV; the GPL-licensed `openassetpricing` client is neither installed nor used.

Damodaran is hosted-safe for the selected aggregates with attribution to Aswath
Damodaran, no resale and no bulk mirror. Select a country or industry explicitly;
company-level files are outside this provider. Snapshot dates come from the
file's published update. Notes retain that update and a content version; the
recorder preserves the original content version while trimming the workbook.
Current files do not establish historical availability, so the provider does
not promise an `as_of` history. The annual implied-ERP workbook retains its own
published update date even when it is older than its latest observation.

The other nine finance providers are library-only. JKP and Coin Metrics data
carry CC BY-NC 4.0. Coin Metrics also declares `ProviderInfo.never_paid=True`;
future paid-feature gates must check it independently of the hosted-mode gate.
The community endpoint exposes only public metrics and needs no API key. A query
is limited to 10,000 daily observations; request explicit smaller date windows
for longer histories.

## Yahoo personal-use opt-in

Install `pyeconomics[yfinance]`, then explicitly enable it after reviewing
[Yahoo's terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html):

```python
from pyeconomics.data import configure

configure(enable_yfinance=True)
```

Alternatively, put `enable_yfinance = true` in `pyeconomics.toml`. The default is
false; installing `[yfinance]` or `[all]` alone enables no requests. Without the
extra, fetching raises `MissingOptionalDependencyError` naming `[yfinance]`.
The real local session warns once per process about personal use and Yahoo's
restriction on automated collection. Hosted mode refuses it.

Prices retain the source's currency units. Fundamentals include numeric financial
fields, excluding textual company/contact data and administrative fields. Option
chains select `calls` or `puts`; append an expiry such as `:2027-01-15` to choose
it explicitly. Without an expiry, the first available one is selected. Each
contract has named numeric columns; an oversized chain is refused rather than
silently truncated. Implied volatility is decimal.

Yahoo is excluded from the scheduled live run and from live CI requests. A local
live run additionally requires the maintainer's `PYECONOMICS_LIVE_YFINANCE=1`.
Ordinary tests use an injected fake local session and synthetic recordings.

## Treasury, Federal Reserve and identifier data

This batch also delivers the four unblocked sources from the parked rates step:

| Provider | Selections |
|---|---|
| `treasury` | `par_nominal`, `par_real` with start/end dates; FiscalData `debt`, `statement`, `average_interest` |
| `fed_board` | `h15:RIFSPFF_N.B`, other daily H.15 series, `target_range`, `gsw`, `sep:YYYY-MM-DD` |
| `nyfed` | `sofr`, `effr`, `obfr`, `tgcr`, `bgcr`, `repo`, `reverse_repo`, `soma`, `acm`, `lw`, `hlw`, `nowcast` |
| `openfigi` | `records(Query(series=("ID_BB_GLOBAL:BBG000BLNNH6",)))` |

These four are hosted-safe subject to their source notices; H.15 third-party
series receive their own library-only terms. Treasury rates and NY Fed rates
become decimals. GSW beta coefficients use decimal rate units and tau parameters
use years. NY Fed volumes retain their published USD or billion-USD scale.
Historical r-star sheets use source labels such as `lw:2005q1` and `hlw:2025Q1`;
a sheet label supplies no invented historical availability date. Current r-star
estimates carry a `revised_data` note. OpenFIGI mappings are bounded, typed
`Records`, separate from numeric frames and unavailable for model bindings.
Its optional `OPENFIGI_API_KEY` uses the existing credential chain.

## SEC EDGAR

`sec_edgar` reads EDGAR's JSON APIs on data.sec.gov. It needs your SEC contact,
a name and an email address, in `PYECONOMICS_SEC_CONTACT` or `sec_contact` in
`pyeconomics.toml` ([Keys and settings](keys.md)); without it a request raises a
`CredentialError` naming the setting before anything is sent. The contact goes in
the User-Agent and nowhere else, and the transport holds every request to SEC's
fair-access limit of ten a second.

| Selection | Returns |
|---|---|
| `records(Query(series=("submissions:320193",)))` | the recent filings as `Filing` records: CIK, accession number, form, filing date and report date |
| `concept:320193:us-gaap:Assets:USD:instant` | one company's XBRL fact (the company concept API) |
| `facts:320193:us-gaap:Assets:USD:instant` | the same fact, read from the company facts API |
| `frame:us-gaap:Assets:USD:CY2024Q1I:320193` | one company's value in a calendar frame |

The last part of a concept or facts selection is the span: `instant`, `quarter`
or `year`. A filing reports one tag over several spans (a 10-Q gives three months
and the year to date, both ending on the same day), so a series keeps only the
facts SEC's frames assign to the span, one per calendar period from the latest
filing. Values are indexed by the filer's actual period end, not moved to a
calendar quarter, and carry `revised_data`: a restated value replaces the one
first filed. A CIK is up to ten digits and is zero-padded; taxonomies
(`us-gaap`, `ifrs-full`, `dei`, `srt`), tags and units must be identifiers, so no
selection can name a path; a ratio unit is `USD/shares` in a concept and
`USD-per-shares` in a frame, as SEC writes them. Filings carry no document name or URL, and no binding
reads them. The submissions file lists a company's latest 1,000 filings or its
last year, whichever is more; older filings are not read.

## File safety and dependency licences

ZIPs stay in memory, with entry-count, per-member and expanded-byte limits.
Traversal paths, duplicates and encrypted members are refused. XLSX readers
reject DTDs and external entities and bound actual rows, columns and cells before
materializing a sheet. A multi-dataset workbook can select one sheet within the
same limits. No archive is extracted. Workbook recording uses an in-memory OOXML
writer; legacy XLS trimming uses the development-only `xlwt` writer.

`xlrd` is the lazy, in-memory legacy XLS reader. Its reviewed BSD licences require
this acknowledgement here, in `NOTICE`, and in relevant advertising materials:

This product includes software developed by David Giffin <david@giffin.org>.

The yfinance extra's reviewed metadata exceptions cover peewee (MIT), multitasking
(Apache-2.0) and protobuf (BSD-3-Clause). The existing reviewed certifi, cffi and
defusedxml conditions continue to apply. All runtime dependencies and extras
remain subject to the licence gate and vulnerability audit.
