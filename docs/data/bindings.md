# Binding models to data

A pyeconomics model is a pure function: typed inputs in, typed outputs out, no
network and no files. A model that should run on live data does not fetch it. It
*declares* which data fills which input field, and `pyeconomics.bind` resolves
the declaration, before the model runs, through the same catalog and resolver
`pyeconomics.data.get` uses. `pyeconomics.run` then runs what `bind` returns and
records every series, vintage and retrieval time in the result's manifest.

```text
model declares bindings ──► bind(model_id, as_of=...) ──► Bound ──► run(model_id, bound)
   (plain data, in core)      (resolution, in the data layer)          (a Result whose manifest
                                                                         lists every source)
```

## Declaring bindings

A `Binding` names one input field's data. It is plain data, defined in
`pyeconomics.core`, so a model carries it without importing the data layer:

```python
from pyeconomics.core import AsOf, Binding, VintagePolicy

binding = Binding("unemployment", "us.unemployment.rate")
assert binding.as_of is AsOf.LAST_ON_OR_BEFORE
assert binding.vintage is VintagePolicy.REAL_TIME
assert binding.profile == "default"
```

| Field | Meaning |
| --- | --- |
| `field` | The model input field the data fills. Only a numeric field can be bound. |
| `concept` | The catalog concept id, such as `us.unemployment.rate`. |
| `transform` | One more transform, applied to the resolved series before the as-of rule (`diff`, `yoy`, `convert(to=quarterly,method=mean)`). The vocabulary is in `pyeconomics.core.transforms`. |
| `as_of` | How the value is picked at the evaluation date: `AsOf.LAST_ON_OR_BEFORE` (the last observation on or before the date), `AsOf.PERIOD` (the observation of the period that contains it) or `AsOf.WINDOW` (the last `window` observations, for an array field). |
| `window` | The number of observations of a window binding; set with, and only with, `AsOf.WINDOW`. |
| `vintage` | `VintagePolicy.REAL_TIME` (the default) or `VintagePolicy.LATEST`, which is revised data and is labelled so. |
| `profile` | The named set of bindings this one belongs to. |
| `tenors` | For a curve: the array field that receives the tenor, in years, of each value the curve's row holds (below). |

A **profile** is one complete set of bindings: realized data, a forecast source,
another economy. A model that declares bindings declares a `default` profile, and
can offer others; the same input field may be bound once in each. Pass the
bindings to the decorator with `@model(..., bindings=(...))`.

### Curves

A yield curve is a table concept whose columns are tenors, `1m` to `30y`
(`us.treasury.par_curve`). Its observation on a date is a row: one value per
tenor. A binding with `tenors` reads the curve's last row on or before the date
that holds anything, under `AsOf.LAST_ON_OR_BEFORE` and with no transform, and
fills two array fields from it: the bound field with the row's values and the
`tenors` field with each value's tenor in years, in increasing order. A tenor the
row leaves empty (Treasury began the 4-month bill in 2022) is left out of both,
so the two always pair by position. The manifest records the curve once for each
field, with the row's date.

```python
from pyeconomics.core import Binding

curve = Binding("yields", "us.treasury.par_curve", tenors="maturities")
assert curve.tenors == "maturities"
```

A caller who supplies the curve supplies both fields; one without the other is
refused. `fixed_income.curve_fitting` fits Treasury's par curve this way, and
`fixed_income.interest_rate_tree` calibrates to it.

`registry.validate()` holds every binding to its structural rules, each reported
as `<model>: [bindings] <detail>`: the field exists and is numeric; it is bound
once per profile; an array field has a window and a scalar field has none, within
the field's `max_length`, unless the binding reads a curve, whose values go to an
array and whose `tenors` go to another array of years, at the last observation
on or before the date and untransformed; the `default` profile exists; the
concept id follows the catalog's grammar; the transform is one the vocabulary
declares, with parameters its schema accepts, and reads one series. Core cannot
read the catalog, so `pyeconomics.data.validate_bindings()` checks the rest
against the installed concepts: that each exists, is a series (or, for a curve,
a table whose every candidate names tenor columns), suits the field's unit kind
and suits the as-of rule. Run both:

```text
uv run python -c "from pyeconomics import registry; registry.validate()"
uv run python -c "from pyeconomics import data; data.validate_bindings()"
```

`uv run python scripts/new_model.py <id> --bound` scaffolds a model with one
example binding and a bound example to complete.

### What a model's page shows

A model that declares bindings gets a **Data** section on its card, after the
variables, in the documentation and in `registry.describe(model_id)["card"]`. It
lists each profile's bindings, and then, for each bound concept, the sources that
can fill it with their licence classes, attributions and required notices. For a
model with two profiles of one input the section reads:

```markdown
## Data

This model reads data through bindings: resolve a profile with `pyeconomics.bind("macro.example_rule")` and run the result. A value read as revised data carries the `revised_data` warning.

### Profile `default`

| Field | Concept | Transform | As of | Vintage |
| --- | --- | --- | --- | --- |
| `unemployment` | `us.unemployment.rate` | none | last observation on or before the date | real time: as published by the date |

### Profile `revised`

| Field | Concept | Transform | As of | Vintage |
| --- | --- | --- | --- | --- |
| `unemployment` | `us.unemployment.rate` | none | last observation on or before the date | latest: revised data |
```

`registry.describe` also carries the bindings as data, in a `bindings` key placed
before `extra`: for each, the `field`, `concept`, `transform`, `as_of`, `window`,
`vintage`, `profile` and `tenors`.

## Binding and running

```pycon
>>> import datetime as dt
>>> import pyeconomics
>>> bound = pyeconomics.bind("<model id>", as_of=dt.date(2025, 9, 17))
>>> result = pyeconomics.run("<model id>", bound)
>>> result.manifest.data_sources[0].vintage
'as_of:2025-09-17'
```

`bind(model_id, /, *, as_of=None, vintage=None, mode=None, profile="default",
concepts=None, parameters=None, **overrides)` returns a `Bound`: the values by
input field, in each field's own unit, and one record per bound field.

- `as_of` is the evaluation date. Left out, each binding reads the latest data at
  its series' last observation.
- `vintage` replaces every binding's own policy: `"latest"` reads revised data.
- `mode` is `library` or `hosted`, as for `pyeconomics.data.get`; in hosted mode
  only sources whose terms allow a hosted service are read.
- `profile` picks the set of bindings.
- `concepts={field: concept}` rebinds a field to another concept of the **same
  unit kind and frequency**; any other is refused.
- `parameters` gives the values of a concept's parameters (the SEP `meeting`) to
  each bound concept that declares them.
- Any other keyword is an **override**: the value the caller supplies. A bound
  field's value is replaced, not read, and its record says `user-supplied` (it
  names the field, never the value, which is an input like any other). A field
  with no binding is an ordinary input.

`run(model_id, bound)` and `run_model(model, bound)` take a `Bound` as their
inputs. A `Bound` runs only the model it was bound for.

A model with several calculations (a union on `calculation`, such as
`macro.policy_rule`) needs the calculation named, `bind(..., calculation="taylor_1993")`,
and reads only the bindings of the fields that calculation takes: a profile can
serve every calculation, and a rule that reads no neutral rate fetches none.

An `AsOf.PERIOD` binding reads the period that contains the date, which ends
after it: the request runs to that period's end and no further, so a source with
nothing up to then is passed over rather than picked.

**Windows of one frequency end together.** A model that pairs array fields by
position (a regression of inflation on unemployment, a gap from actual and
potential output) must read the same periods in each. So every `AsOf.WINDOW`
binding of one frequency (after its own transform, such as
`convert(to=quarterly,method=mean)`) ends at the earliest of their last
observations on or before the date, or, with no date, of their last
observations: real GDP published to the second quarter and CBO's potential
projected years ahead both end with the second quarter. The record's
`window(count=...,date=...)` shows the date the windows share. Windows of
different frequencies, or of one frequency on another calendar (a fiscal year
ending in September beside a calendar year), are left alone.

**A window takes a source with the history.** A window binding asks the resolver
for the observations it reads (three months a quarter through
`convert(to=quarterly,...)`, and the periods a `pct_change` reaches back), and a
candidate with fewer is passed over as `no_observations`: an originator whose API
serves a few recent years (BLS without years asked) gives way to an aggregator
with the history (FRED). A source that runs years ahead (CBO's projections) can
hold enough in all and too few up to the date the windows share; the bind asks
again up to that date, and it gives way too. A window never takes a gap: a
quarter's average of a month the source left out is missing, so a model that
reads monthly data by the quarter can take each quarter's last month instead.

A concept whose sources answer for a window of dates (the Treasury curves) is
asked for enough of them to cover what the binding finally reads: a
`convert(to=monthly,method=mean)` binding is sized in months, so the month before
the date is always whole.

## Real time by default

Historical evaluation defaults to the vintage published **by the evaluation date**
wherever a source usable in the mode keeps vintages (ADR-0011 decision 6). A
forecaster on 20 March 2024 read the unemployment rate as first published, not as
revised in April, and a back-test that reads the revised number looks into the
future.

| What was asked | What `bind` reads | Record |
| --- | --- | --- |
| `as_of` and `REAL_TIME`, a source keeps vintages | the vintage `as_of:YYYY-MM-DD` | `vintage` is `as_of:...`; `realtime` covers the date |
| `as_of` and `REAL_TIME`, no source usable in the mode keeps vintages of the series | the latest data | warning code `revised_data` |
| `LATEST` | the latest data | warning code `revised_data` |
| no `as_of` | the latest data, at the last observation | none, unless the source itself says so |

Revised data is never passed off as real time. Its record carries `revised_data`,
the `Bound` lists the fields in `bound.revised`, and the result carries a
`revised_data` warning (so it never shares a `result_sha256` with the same
numbers read in real time). A source that publishes only its current estimates,
like BEA's API, marks every frame `revised_data` itself, and the record repeats
it. A provider that keeps vintages may still keep none of one series: ALFRED holds
none of FRED's daily rates (`EFFR`, the target range, `DGS10`, `DGS3MO`,
`DFII10`), so the catalog marks those candidates `vintages=False` and they are
read as revised data too. A source that could answer in real time but cannot, because its key is
missing or the cache has nothing offline, is an error to fix: `bind` raises
`CredentialError` or `OfflineError`, and never quietly reads revised data.

## What the manifest records

A manifest is schema 2. Its `data_sources` lists one `DataSource` record per
bound field, sorted by field: the provider, series, dataset, concept and field;
the vintage label and real-time period; the observation window actually read;
the transforms applied, ending with the as-of rule (`asof(date=2025-09-17)`); the
retrieval time; the licence class, attribution, notice, terms page and `llm_use`;
whether the cache or offline mode served it; the providers the resolver tried;
and warning codes about the data (`revised_data`, `served_offline`,
`skipped_<provider>_<reason>`).

A record never holds a request URL, a host, a path or a key. The only URL is the
source's public terms page. A manifest holds no clock *of the run* and no host,
user, path or environment value: a source's retrieval time is a fact about the
data, recorded where it was fetched. Two runs on the same inputs and the same
records give the same manifest bytes, and `result_sha256` keeps its definition:
it covers the inputs, outputs and warnings, never the manifest.

`Result.attributions()` returns the attribution and required notices of the data
a result read, each once, ready for an export to print; a value the caller
supplied needs neither.

## Offline and tests

`bind` reads through the provider cache. A source whose terms forbid storage (FRED
among them) is never written to disk; two bindings of one series in one `bind`
share an in-process memo, so the source is asked once. In offline mode
(`pyeconomics.data.configure(offline=True)`) only the cache answers.

A test binds with `pyeconomics.data.bind_model(model, ..., registry=..., transport=...)`:
a model object, an isolated provider registry and a replay or scripted transport.
