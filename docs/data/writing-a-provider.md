# Writing a provider

A provider is how pyeconomics reads one data source. It is a `DataProvider`
subclass that says what the source is (`ProviderInfo`) and how to turn a query
into requests and the answers into a `Series` or a `Table`. Everything else is
shared: the transport sends the requests, the key chain supplies the key, the
registry finds the provider, and one contract suite holds every provider to the
same rules. The same contract serves the built-in sources, a third-party package
and, from Phase 6, vendors such as Bloomberg.

This page is the contract. [ADR-0011](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/adr/0011-data-platform.md)
records why it is this way.

## The pipeline

```text
Query -> build_requests -> exchange (a Transport) -> parse -> Series | Table
```

A provider overrides the hooks of the capabilities it declares and nothing
else. The public methods are final: `fetch`, `search`, `describe`, `vintages`
and `run_case` check the capability and the platform, refuse a source hosted mode
may not serve before any request, map every response's status to the error
taxonomy, and check what `parse` returned. A subclass that defines one is refused
when it is created, so no provider can skip a gate.

| Capability | Hooks to override | Public method |
|------------|-------------------|---------------|
| `fetch` | `build_requests`, `parse` | `fetch(query)` |
| `search` | `build_search`, `parse_search` | `search(text, limit=25)` |
| `describe` | `build_describe`, `parse_describe` | `describe(series_id)` |
| `vintages` | `build_vintages`, `parse_vintages` | `vintages(series_id)` |
| `bulk` | none: it declares that one request returns a whole dataset | |

`classify_error` maps a source's own error body to the taxonomy, `exchange` is
the seam a non-HTTP source overrides, `next_page` returns the request for a
source's next page (FRED v2's cursor), and `synthesize` replaces observed values
for the recorder.

## A provider in forty lines

This provider reads an invented source. It declares itself, builds one request
per series and parses the answer. A canned transport stands in for the network
so that this page can run.

```python
import datetime as dt

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    CachePolicy,
    DataProvider,
    DateConvention,
    LicenceClass,
    LlmUse,
    ObservationFrequency,
    ProviderInfo,
    RateLimit,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Terms,
    UnitRecord,
)
from pyeconomics.data.transport.base import Request, request_path


class Demo(DataProvider):
    info = ProviderInfo(
        id="demo",
        name="Demo Statistics Office",
        homepage="https://www.demo.example.org",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.demo.example.org/terms",
            checked=dt.date(2026, 10, 15),
            attribution="Source: Demo Statistics Office.",
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        hosts=("api.demo.example.org",),
        rate_limits=(RateLimit(requests=30, per="minute"),),
    )

    def build_requests(self, query):
        return [
            Request(
                host="api.demo.example.org",
                path=request_path("v1", "series", series_id),
                series=series_id,
            )
            for series_id in query.series
        ]

    def parse(self, responses, query):
        body = responses[0].json(provider="demo")
        meta = SeriesMeta(
            provider="demo",
            series_id=query.series[0],
            title=body["title"],
            unit=UnitRecord(text="Percent", kind=UnitKind.RATE),
            frequency=ObservationFrequency.ANNUAL,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_END,
            terms=self.info.terms,
        )
        days = tuple(dt.date(int(year), 12, 31) for year, _ in body["data"])
        # A rate is a decimal: the source publishes percent, so divide.
        values = tuple(None if v is None else v / 100 for _, v in body["data"])
        return Series(days, values, meta)
```

Nothing above opens a socket. To run it, hand `fetch` a transport. Here a
canned one answers; in real use the default HTTPS transport does.

```python
import json

from pyeconomics.data.transport.base import Response


class Canned:
    def send(self, info, request, *, key=None):
        body = {"title": "Demo rate", "data": [["2023", 4.5], ["2024", None]]}
        when = dt.datetime(2026, 10, 15, 12, tzinfo=dt.UTC)
        return Response(200, json.dumps(body).encode(), when)


series = Demo().fetch({"series": ["RATE"]}, transport=Canned())
print(series.values, series.meta.retrieved_at.date())
```

A year-end date, `0.045` for `4.5`, `None` for the missing year, and the time the
transport got the answer: the provider did none of that bookkeeping. Check the
provider against every rule with the registry:

```python
from pyeconomics.data.registry import ProviderRegistry

ProviderRegistry.from_providers(Demo).validate()
```

## What a provider owes the contract

`parse` returns data that follows the data layer's conventions
([ADR-0011](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/adr/0011-data-platform.md)
decisions 2 to 6); the contract suite checks them.

- **Dates.** A period's observation is indexed by the period's last day, in the
  frame's frequency. A source that dates months and quarters by their first day
  (FRED, BLS, BEA) is converted, and `source_dating` records what the source did.
- **Rates are decimals.** `0.05`, not `5`: convert percent with
  `pyeconomics.core.rates.percent_to_decimal` in `parse`. A `rate`, `return`,
  `probability` or `volatility` unit has scale 1.
- **Missing values are `None`**, never NaN. Each provider maps its source's marker
  (FRED's `.`, say) to `None`.
- **Every frame is labelled.** Units (as published, with a unit kind, scale and
  currency), frequency, seasonal adjustment, the source's terms (licence class,
  attribution, notice, `llm_use`, cache policy) and, from the base class, the
  retrieval time.
- **Vintages.** A source that keeps them returns every row with its
  `RealtimePeriod`, and the base class selects the vintage the query asked for.
  `None` ends a period that is still current.
- **A series may carry its own terms.** Where one source mixes classes, `parse`
  gives the series `terms.with_overrides(...)` from the source's own marker; hosted
  mode checks that class too, after the response arrives.
- **Size.** A query names at most 1,000 series and 100,000 observations;
  `max_observations` keeps the most recent rows.
- **Notes.** What the source says about the data travels in the metadata's
  `notes`: a snake_case code and, after `": "`, a detail. BEA's
  `revised_data` (it serves only current estimates), BLS's footnotes
  (`footnote: P preliminary (2026-08-31)`) and FRED's copyright status are
  notes.

## Declaring the provider

`ProviderInfo` accepts what it is given; `pyeconomics.data.registry.validate()`
reports each flaw as `<id>: [<rule>] <detail>`:

| Rule | What it holds |
|------|---------------|
| `provider-id` | A permanent snake_case id (ADR-0003), a name and an `https` home page |
| `terms` | Complete `Terms`: a licence class, the terms page, the date it was read |
| `attribution` | Whom to credit, not a placeholder |
| `notice` | The source's own required wording, if any |
| `llm-use` | A vendor source (`byok`, `premium-local`) is never `allowed` |
| `cache-policy` | `allowed` or `forbidden`; `forbidden` means no cache path at all. `ttl_seconds` is a whole number of seconds (`0` turns the cache off) |
| `hosts` | The exact host names, lower case, HTTPS only, no port or wildcard |
| `rate-limit` | The source's published limits, which the transport holds it to |
| `capabilities` | Each declared capability has its hooks, and no hook is undeclared |
| `auth` | A key's placement and name, which the redaction layer can scrub |
| `extra` | An extra the registering distribution declares |
| `platforms` | The platforms it runs on, and `fetch` refuses any other |
| `size-cap` | The largest response the transport reads |
| `released` | A released id is never deleted or renamed |

The 13-month freshness of a provider's terms is a test, not a rule
(`tests/providers/test_provider_terms.py`), because `validate()` reads no clock. The exact
attribution and notice are pinned, per provider, in
`tests/providers/test_notices.py`, so a change to a notice is a reviewed diff.

### Licence class, hosted mode and caching

The class decides where a source's data may flow (ADR-0005). In hosted mode
(`PYECONOMICS_MODE=hosted`) every public operation raises `LicenceError`, naming
the class and the terms page, before any request, unless the source is
`hosted-safe` or `user-supplied`. A source whose terms forbid storage has
`CachePolicy.FORBIDDEN`: it is fetched live and never written to disk, with no
opt-in. Read the class from the source's own terms page when the provider is
written, never from a plan.

A source that allows storage is cached by the base class, not by the provider:
`fetch` asks the cache first and keeps the result for `ProviderInfo.ttl_seconds`
(one hour by default; a user's `PYECONOMICS_TTL_<PROVIDER>` overrides it), and a
closed past vintage for as long as the size cap allows. Choose the time-to-live
from how often the source publishes. A provider writes no cache code. A series that
needs its own policy gets it from `terms.with_overrides(cache=CachePolicy.FORBIDDEN)`
in `parse`, and the cache honours it. [The cache and offline mode](cache.md)
describes the behaviour; offline mode needs nothing from a provider either, because
`search`, `describe` and `vintages` refuse to run while it is on.

### Authentication

`Authentication.key("api_key", KeyPlacement.QUERY)` says where the transport puts
the key: a query parameter, a body field or a header (with a `scheme` such as
`Bearer`). The key comes from the key chain as a `Secret`; **provider code never
sees it.** A `Request` refuses a parameter, body field or header named like a
credential. `Authentication.contact()` is for a source that wants the user's name
and email in the User-Agent (SEC EDGAR). The environment variable is
`<PROVIDER>_API_KEY`.

A source whose API versions take the key differently declares the others as
`alternates`, one `KeySlot` per placement, and a request names the one it needs
with `Request.key_placement`: FRED's v1 reads the `api_key` query parameter, its
v2 an `Authorization: Bearer` header.

A key that only raises the limits is `required=False`. The provider's build and
parse hooks read `self.sends_key` to choose the keyed or the keyless API (BLS's
v2 or v1), and a limit that holds only without a key is
`RateLimit(..., without_key=True)`. A `Case` with `keyless=True` runs with the
key chain's key withheld (`pyeconomics.data.credentials.withheld`).

A source that answers a bad key with a redirect to a page that echoes the
request (Census) sets `follow_redirects=False`: the transport returns the
redirect, and `classify_error`, which sees every status outside 2xx, maps it.

## Errors

The transport returns the final response for any HTTP status, after its retries.
The base class maps it:

| Final status | Error |
|--------------|-------|
| 401, 403 | `CredentialError`, naming the provider and its variable |
| 404 | `SeriesNotFoundError` |
| 429 | `RateLimitError`, with `retry_after` |
| 5xx | `TransportError` |
| other failures, a malformed body | `ResponseError` |

A source that answers a missing series with HTTP 400 and a JSON message
overrides `classify_error`. No message holds a key or a URL's query.

## Registering a provider

A package lists its provider classes in a module's `__all__` and names the module
in an entry point; importing the module registers nothing by itself:

```toml
[project.entry-points."pyeconomics.providers"]
demo = "demo_package.providers"
```

`pyeconomics.data.registry.ids()`, `get(id)` and `validate()` read the group. A
provider id is permanent once released.

## Cassettes, the recorder and the contract suite

Tests never touch the network (sockets are disabled). A provider's offline tests
replay *cassettes*: canonical-JSON files under
`tests/providers/cassettes/<provider>/<case>.json` that a deliberate local
recording wrote. A provider lists its `cases` (an operation, an argument and, for
an error cassette, the error it must raise).

```console
uv run --no-config python scripts/record_cassettes.py fred --list
uv run --no-config python scripts/record_cassettes.py fred fetch_ok error_not_found
```

The recorder runs each case live through the real transport with the
maintainer's keys, then scrubs every key, credential parameter, header and cookie.
A rate limit or an outage is never provoked on purpose: a case with
`simulate=429` (or a 5xx) builds its real requests, sends none, records that
status with a `Retry-After` of 60 seconds, and is marked synthetic.
A cassette holds at most 24 observations per series and 32 KiB. **A source that
is not hosted-safe, or that forbids storage, is recorded through its
`synthesize()` hook, which replaces every observed value, and the cassette says
`"synthetic": true`.** A test fails for one that does not. Nothing in
`tests/providers/cassettes` is a dataset.

The shared suite (`tests/providers/provider_contract.py`, run by
`test_provider_contract.py`) takes every registered provider and the toy providers:

- the provider validates, and every capability has a success case and every case a
  cassette, with 404 and 429 error cases (and 401 for a keyed source);
- each cassette replays into a valid result, with decimal rates, `None` for
  missing values and the cassette's `recorded_on` as the retrieval time;
- the transport refuses a foreign host and `http://`, redirects included, and the
  rate limiter holds on a fake clock;
- hosted mode refuses every class but `hosted-safe` and `user-supplied`;
- every cassette passes the secret scan.

Run it against the real APIs with `uv run pytest -m live --force-enable-socket
tests/providers` (deselected by default; the scheduled run skips a source whose
terms bar automated collection).

## Sources that are not HTTP

Phase 6 adds Bloomberg over its Desktop API: a local session on `localhost`, with
no HTTP in it. A design spike in `tests/providers/test_bloomberg_spike.py` runs a
provider over a fake session and found that the contract holds such a source with
no change:

- `ProviderInfo(access=Access.SESSION, hosts=())` and an `exchange()` override. The
  provider talks to a session (open a service, send a request, iterate its
  events) and returns `Response` values; no HTTP transport can send for it,
  because it declares no host.
- It names its service with a `Request` on a `*.localhost` host, which no
  allowlist admits, and builds the request body as JSON like any other.
- A session reports a failure with the HTTP statuses the taxonomy already maps:
  404 for an unknown security, 429 for a limit. A limit error is never retried.
- The session owns the clock, as the HTTP transport does, and stamps each
  `Response`.
- Tickers contain spaces, so the provider sets `query_type` to a `Query` subclass
  that widens the id pattern.
- `licence=PREMIUM_LOCAL`, `platforms=(Platform.WINDOWS,)` and `llm_use=FORBIDDEN`
  keep it out of hosted mode, off other platforms and away from language models.
  Its hit budget (securities times fields, refused over budget unless forced)
  lives in the provider, because a session has no rate limits to declare.

## A security checklist

- The transport is the only code that opens a socket, builds a URL or reveals a
  key; the `secret-reveal` rule and a layering test enforce it.
- A provider builds a `Request` from its own hosts and `request_path` segments;
  an input can never choose the scheme, the host or the structure of the path.
- Parse JSON with `Response.json()` (the standard library, strict). Never pickle,
  `eval` or `yaml.load` a response, and parse XML only with defusedxml.
- Never print, log or record a key. A key a request echoes back is scrubbed from
  the cassette, and a failing test names the sinks that held a canary, never the
  canary.
