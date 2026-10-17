# Research and forecast data

The research providers fetch one series per query so each series retains its
own observation dates and publication history. Rates and growth forecasts are
decimals; missing values remain `None`.

| Provider | Example series id | Meaning |
| --- | --- | --- |
| `philadelphia_fed` | `rtd:ROUTPUT`, `rtd:P`, `rtd:PCONX`, `rtd:RUC` | Real output, GDP/core PCE price indexes, monthly unemployment |
| `philadelphia_fed` | `spf:median:RGDP:3`, `spf:mean:UNEMP:A` | SPF level forecasts, quarterly or annual horizon |
| `philadelphia_fed` | `spf_growth:median:RGDP:3` | SPF growth forecast, converted from percent |
| `philadelphia_fed` | `spf:median:CPI10` | SPF ten-year inflation expectation |
| `atlanta_fed` | `gdpnow` | Current GDPNow estimate and archived updates |
| `cleveland_fed` | `expected_inflation:10`, `real_rate:10y`, `inflation_risk_premium:10` | Monthly expected inflation, real rate and risk premium |
| `cbo` | `quarterly:real_potential_gdp`, `calendar:potential_lf`, `fiscal:noncyclical_rate_of_unemployment` | CBO projections and potential output inputs |
| `penn_world_table` | `USA:rgdpna`, `DEU:rkna`, `USA:labsh` | Country series in PWT 11.0 |

## Publication dates and vintages

Philadelphia's real-time matrices use the information available on the 15th
day of the middle month of each quarter: February, May, August and November.
Observation dates are period ends. A missing leading cell means the observation
had not been published; a missing cell in a later vintage remains missing.

SPF forecasts use the source's [news-release calendar](https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/survey-of-professional-forecasters/spf-release-dates.txt).
Surveys before 1990Q2 have unknown publication dates and are excluded. The delayed
1990Q2 and Q3 surveys share a release day; the later survey supersedes an earlier
annual forecast on that day. Horizon `1` is the preceding quarter, `2` is the
survey quarter and `3` is the next quarter. Annual horizons `A` through `D`
start with the survey year. A long-term forecast has its survey quarter as
the observation date and its horizon recorded in metadata.

GDPNow uses each update's actual date as the vintage and the quarter being
forecast as the observation period. Only GDPNow's own estimates are read;
the workbook's proprietary Blue Chip forecasts are excluded.

CBO uses exact report publication days. Its [data page](https://www.cbo.gov/data/budget-economic-data)
directs automated users to [CBO's own machine-readable repository](https://github.com/US-CBO/cbo-data).
The provider retains every report currently supplied in that economic-projections
archive: February and June 2024, January and September 2025, and February 2026.
The report dates are February 7 and June 18, 2024; January 17 and September 12,
2025; and February 11, 2026. A month label is never treated as its first day.
Quarterly and calendar-year series end in December; fiscal-year series end in
September. Other historical CBO releases are outside this archive's coverage.

These three providers support `latest`, `first_release`, `all` and
`as_of:YYYY-MM-DD`. Real-time intervals include both endpoints. Selection occurs
before the observation cap, so an early `as_of` query cannot lose its history
to later revisions. Their `vintages` operation lists publication dates.

Cleveland's downloadable workbook and the current PWT release retain revised
data, without publication histories. They carry `revised_data`; an `as_of` or
`first_release` request fails rather than implying historical availability.
PWT metadata records release 11.0, published October 7, 2025. PWT shares and
rates are already decimals; capital services `rkna` is an index, while capital
stock `rnna` is a monetary level.

## Terms and storage

Terms were read on October 17, 2026. The Philadelphia, Atlanta and Cleveland
Fed products are `library-only` under their research, educational or
noncommercial terms. They are refused in hosted mode, carry their source
attribution and notice, and have `llm_use=unclear`. Local caching is allowed;
only minimal synthetic workbooks are committed as their cassettes.

[CBO's copyright policy](https://www.cbo.gov/about/privacy) identifies government
documents as public domain. CBO data are `hosted-safe`, with attribution.
[PWT 11.0](https://www.rug.nl/ggdc/productivity/pwt/) is `hosted-safe` under CC BY
4.0; every frame carries the authors' required Feenstra, Inklaar and Timmer
(2015) citation. Both allow caching and LLM use. These permissions apply to
the specified products and do not grant rights to third-party material.

## Spreadsheet boundary

Workbooks are parsed entirely in memory, using openpyxl with defusedxml,
read-only cached values, and disabled external links. ZIP entries, compressed
and expanded bytes, actual cells, rows and columns have finite bounds. XML
entities and DTDs are rejected before openpyxl reads any member. Formulae are
never evaluated. Fixture serialization uses a minimal in-memory OOXML producer;
openpyxl's writer would create temporary worksheet files. Formatting-only rows at Excel's last row do not allocate a
million empty rows; actual out-of-bounds values are refused even when a file
falsifies its declared dimensions. Parser failures are scrubbed and unchained.

The shared reader derives from the unfinished Step 7 reader, with additional
actual-cell and XML checks required by these sources. It does not include
Step 7's providers or legacy XLS support. The defusedxml PSFL metadata exception
retains the maintainer's October 16 approval: its bundled licence is PSF v2.
