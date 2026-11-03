# Migrating from 0.2.x to 1.0

pyeconomics 1.0 is a rewrite. 0.2.x was four monetary-policy rules on FRED data;
1.0 is a library of models with typed inputs, a data layer of many sources, and a
command line, a REST API and an MCP server on top. The rules are still here, and
their numbers still match, but no 0.2.x call runs unchanged.

## Before you start

- **Nothing moves you by surprise.** `pip install pyeconomics` keeps giving you
  0.2.6 until 1.0.0 is released. To stay there after that, pin `pyeconomics<1`:
  its releases stay on PyPI.
- **0.2.x ends at 1.0.0.** 0.2.x receives security fixes only and reaches
  end-of-life when pyeconomics 1.0.0 is released.
- **1.0 needs Python 3.12 or later.** Try it now with
  `pip install --pre pyeconomics`, in a new virtual environment.
- **1.0 is licensed under Apache-2.0.** Releases through 0.2.x remain
  MIT-licensed ({doc}`notices`).

## What changed, and why

**A registry of models.** 0.2.x exported a function per rule. In 1.0 every model
has a permanent id, such as `macro.policy_rule`, and one entry point runs them
all: `pyeconomics.run(id, ...)`. A model is a pure function with validated inputs
and outputs, so it never fetches, prints or plots. The four rules are four
*calculations* of one model. That one registry generates every surface, so a
result is the same bytes in Python, on the command line, over REST and through
MCP.

**A data layer.** 0.2.x read FRED through a global client. 1.0 reads 31 sources
through `pyeconomics.data`. You ask for a *concept*, such as
`us.unemployment.rate`, and a resolver chooses a source that delivers exactly
that, starting with the body that publishes it. FRED is one source among them
({doc}`data/index`).

**Real-time vintages.** A 0.2.x history used today's revised data, which nobody
had at the time. `pyeconomics.bind` reads each series as published on the date you
name, and labels any revised data as `revised_data` in the result
({doc}`data/bindings`).

**The manifest.** Every result carries how it was produced: the model's version,
the library's and its dependencies' versions, a hash of its inputs and outputs,
and a record of each series it read ({doc}`results`). A number can be checked
years later.

**Decimals for rates.** 0.2.x took and returned percent, so 2.5 meant 2.5%. Every
rate in 1.0 is a decimal, so 2.5% is `0.025`. Every input and output declares its
unit.

**Licence classes.** Every source declares what its terms allow, and data flows
only where they allow it. FRED's terms forbid storing its data and passing it to a
language model, so 1.0 never writes FRED data to disk and never sends it to an AI
assistant ({doc}`data/index`). 0.2.x kept FRED data in a local pickle cache:
delete the `cache` directory it left beside the package.

## The four rules

These examples hold one economy fixed: inflation and unemployment both at 3.5%, a
natural rate of 4.2%, a real rate of 2%, a policy rate of 5.375%, policy inertia of
0.7 and the lower bound on. Each 0.2.x call and its result come from the recorded
behaviour of 0.2.6, and a test holds both blocks to that record.

Every 1.0 weight below is the model's default, which is 0.2.x's default too. A
result is no longer rounded, so these examples round it to compare.

### Taylor rule

```text
>>> taylor_rule(
...     EconomicIndicators(
...         current_inflation_rate=3.5,
...         current_unemployment_rate=3.5,
...         natural_unemployment_rate=4.2,
...         long_term_real_interest_rate=2.0,
...         current_fed_rate=5.375,
...     ),
...     TaylorRuleParameters(rho=0.7, apply_elb=True),
... )
5.85
```

```python
>>> import pyeconomics
>>> result = pyeconomics.run(
...     "macro.policy_rule",
...     calculation="taylor_1993",
...     inflation=0.035,
...     unemployment=0.035,
...     natural_unemployment=0.042,
...     neutral_real_rate=0.02,
...     previous_rate=0.05375,
...     smoothing=0.7,
...     lower_bound=0.00125,
... )
>>> round(result.outputs.prescribed_rate * 100, 2)
5.85
```

### Balanced approach rule

```text
>>> balanced_approach_rule(
...     EconomicIndicators(
...         current_inflation_rate=3.5,
...         current_unemployment_rate=3.5,
...         natural_unemployment_rate=4.2,
...         long_term_real_interest_rate=2.0,
...         current_fed_rate=5.375,
...     ),
...     BalancedApproachRuleParameters(rho=0.7, apply_elb=True),
... )
6.06
```

```python
>>> result = pyeconomics.run(
...     "macro.policy_rule",
...     calculation="balanced_approach",
...     inflation=0.035,
...     unemployment=0.035,
...     natural_unemployment=0.042,
...     neutral_real_rate=0.02,
...     previous_rate=0.05375,
...     smoothing=0.7,
...     lower_bound=0.00125,
... )
>>> round(result.outputs.prescribed_rate * 100, 2)
6.06
```

### Balanced approach shortfalls rule

The option `use_shortfalls_rule=True` is now a calculation of its own. With
unemployment below its natural rate there is no shortfall, so this rule ignores the
tight labour market and prescribes less than the rule above.

```text
>>> balanced_approach_rule(
...     EconomicIndicators(
...         current_inflation_rate=3.5,
...         current_unemployment_rate=3.5,
...         natural_unemployment_rate=4.2,
...         long_term_real_interest_rate=2.0,
...         current_fed_rate=5.375,
...     ),
...     BalancedApproachRuleParameters(
...         rho=0.7, apply_elb=True, use_shortfalls_rule=True
...     ),
... )
5.64
```

```python
>>> result = pyeconomics.run(
...     "macro.policy_rule",
...     calculation="balanced_approach_shortfalls",
...     inflation=0.035,
...     unemployment=0.035,
...     natural_unemployment=0.042,
...     neutral_real_rate=0.02,
...     previous_rate=0.05375,
...     smoothing=0.7,
...     lower_bound=0.00125,
... )
>>> round(result.outputs.prescribed_rate * 100, 2)
5.64
```

### First-difference rule

This rule reads last year's unemployment rate and natural rate, and no real rate.

```text
>>> first_difference_rule(
...     EconomicIndicators(
...         current_inflation_rate=3.5,
...         current_unemployment_rate=3.5,
...         natural_unemployment_rate=4.2,
...         lagged_unemployment_rate=4.0,
...         lagged_natural_unemployment_rate=4.2,
...         current_fed_rate=5.375,
...     ),
...     FirstDifferenceRuleParameters(rho=0.7, apply_elb=True),
... )
5.75
```

```python
>>> result = pyeconomics.run(
...     "macro.policy_rule",
...     calculation="first_difference",
...     inflation=0.035,
...     unemployment=0.035,
...     natural_unemployment=0.042,
...     unemployment_lagged=0.04,
...     natural_unemployment_lagged=0.042,
...     previous_rate=0.05375,
...     smoothing=0.7,
...     lower_bound=0.00125,
... )
>>> round(result.outputs.prescribed_rate * 100, 2)
5.75
```

### Where the numbers differ

Every recorded 0.2.6 output either matches 1.0 at two decimals or falls under one
of three named differences, which a test proves case by case:

- **Half-way rounding.** 0.2.x rounded every result to two decimals, in percent.
  Where the exact result sits on a half-way value (x.xx5), the two versions'
  arithmetic land on either side of it in the last bit and round 0.01 apart. 1.0
  does not round.
- **The lower bound comes after smoothing.** 0.2.x floored the rule's rate and then
  smoothed it, so a smoothed rate could fall below the bound. 1.0 smooths and then
  floors, so a prescription never sits below the bound.
- **The lagged gap in a history.** 0.2.x's historical first-difference table reused
  the first month's lagged gap for the second and third months of a quarter. In
  1.0 each month reads its own unemployment rate a year earlier.

## Every public name

0.2.x's public names, and what replaces each. `pyeconomics.data` was a module of
dataclasses in 0.2.x and is the data layer in 1.0, so an old import there fails
rather than doing something else.

### Rules and estimates

| 0.2.x | 1.0 | Notes |
|-------|-----|-------|
| `taylor_rule` | `pyeconomics.run("macro.policy_rule", calculation="taylor_1993", ...)` | Pass values, or bind them to data ([below](#live-data)) |
| `balanced_approach_rule` | `calculation="balanced_approach"` | With `use_shortfalls_rule=True`: `calculation="balanced_approach_shortfalls"` |
| `first_difference_rule` | `calculation="first_difference"` | |
| `calculate_policy_rule_estimates` | One run per calculation | Removed: the four-row table was a view of four runs ([below](#several-rules-or-dates)) |
| `historical_taylor_rule` | `pyeconomics.run_batch` over your own table, or `pyeconomics.bind` per date | Removed: a model reads no history itself ([below](#several-rules-or-dates)) |
| `historical_balanced_approach_rule` | The same | |
| `historical_first_difference_rule` | The same | |
| `calculate_historical_policy_rates` | The same, one calculation at a time | |

### Inputs and options

The dataclasses are gone: every input is a named field of the run, and validated.

| 0.2.x | 1.0 | Notes |
|-------|-----|-------|
| `EconomicIndicators` | The run's input fields | Rates divided by 100 |
| `TaylorRuleParameters` | The run's input fields | |
| `BalancedApproachRuleParameters` | The run's input fields | |
| `FirstDifferenceRuleParameters` | The run's input fields | |
| `current_inflation_rate` | `inflation` | |
| `current_unemployment_rate` | `unemployment` | |
| `natural_unemployment_rate` | `natural_unemployment` | |
| `long_term_real_interest_rate` | `neutral_real_rate` | |
| `current_fed_rate` | `previous_rate` | |
| `lagged_unemployment_rate` | `unemployment_lagged` | |
| `lagged_natural_unemployment_rate` | `natural_unemployment_lagged` | |
| `inflation_series_id` | `concepts={"inflation": "..."}` on `bind`, or `--concept` | A catalog concept, not a FRED id |
| `unemployment_rate_series_id` | `concepts={"unemployment": "..."}` | |
| `natural_unemployment_series_id` | `concepts={"natural_unemployment": "..."}` | |
| `real_interest_rate_series_id` | `concepts={"neutral_real_rate": "..."}` | |
| `inflation_target` | `inflation_target` | A decimal: `0.02`, the default |
| `alpha` | `inflation_weight` | |
| `beta` | `resource_weight` | In output-gap units: the balanced approach's `beta=2.0` is `resource_weight=1.0` at an Okun coefficient of 2 |
| `okun_factor` | `okun_coefficient` | |
| `rho` | `smoothing` | Needs `previous_rate` |
| `elb` with `apply_elb` | `lower_bound` | A decimal: `0.00125`. Left out, there is no bound |
| `apply_elb` | `lower_bound` | |
| `use_shortfalls_rule` | `calculation="balanced_approach_shortfalls"` | |
| `verbose` | `--format table`, or `result.outputs` | Removed: a model prints nothing |

### Printing and plotting

Models print and plot nothing, so a result is data you can show as you like.
matplotlib is no longer a dependency.

| 0.2.x | 1.0 | Notes |
|-------|-----|-------|
| `print_fred_series_names` | `data.describe("us.unemployment.rate")` | Removed |
| `print_verbose_output` | `result.outputs`: `inflation_gap_term`, `resource_gap_term`, `unconstrained_rate` | Removed, with its advice to raise or lower the rate: 1.0 reports the rule's rate and advises nothing |
| `verbose_taylor_rule` | The same | Removed |
| `verbose_balanced_approach_rule` | The same | Removed |
| `verbose_first_difference_rule` | The same | Removed |
| `plot_historical_taylor_rule` | `to_pandas()` and your own plotting library | Removed |
| `plot_historical_bar_basr_rule` | The same | Removed |
| `plot_historical_fdr` | The same | Removed |
| `plot_historical_rule_estimates` | The same | Removed. `Result.plot()`, with the `plot` extra, draws a model's own charts, such as a forecast path |

### FRED and the cache

| 0.2.x | 1.0 | Notes |
|-------|-----|-------|
| `fred_client` | `pyeconomics.data.get("fred:UNRATE")` | Removed: importing 0.2.x built this client, and failed with no key. 1.0 reads a key only when a source needs one |
| `FredClient` | The same | Removed |
| `FredClient.fetch_data` | `data.get("fred:UNRATE").frame.to_pandas()` | Values are decimals |
| `FredClient.get_latest_value` | `data.get("fred:UNRATE").frame.values[-1]` | |
| `FredClient.get_historical_value` | `data.get("fred:UNRATE").frame.values[-13]` | |
| `FredClient.get_series_name` | `data.describe("fred:UNRATE")` | |
| `FredClient.get_data_or_fetch` | `pyeconomics.bind` | A field you pass is not fetched |
| `FredClient.reset_instance` | Nothing | Removed: there is no global client |
| `fetch_historical_fed_funds_rate` | `data.get("us.policy_rate.target_upper")` | Before 16 December 2008, when the target was one number, read `fred:DFEDTAR` |
| `save_to_cache` | Automatic | Removed: the data layer caches what a source's terms allow, as JSON, never a pickle ({doc}`data/cache`) |
| `load_from_cache` | Automatic | Removed |
| `FRED_API_KEY` | `FRED_API_KEY` | Still read |
| The keyring entry `fred` / `api_key` | `pyeconomics keys set fred` | Store it again: 1.0 reads service `pyeconomics`, user `fred` ({doc}`data/keys`) |

(live-data)=

## Live data

In 0.2.x, leaving out an indicator fetched it from FRED. In 1.0 you say so: `bind`
reads the data, `run` runs it, and the result records every series it read. On the
command line, any data option does both. These read live data, and need your keys
for the sources they reach ({doc}`data/keys`):

```shell
$ pyeconomics models run macro.policy_rule --calculation taylor_1993 --profile default
$ pyeconomics models run macro.policy_rule --calculation taylor_1993 --as-of 2024-06-28
```

From Python, the same run is
`pyeconomics.run("macro.policy_rule", pyeconomics.bind("macro.policy_rule", calculation="taylor_1993", as_of=date))`.

**The default series changed.** 1.0's default profile reads core PCE inflation, the
Holston-Laubach-Williams real rate and the effective federal funds rate, where
0.2.x read FRED's trimmed-mean PCE, the ten-year TIPS yield and the top of the
target range, so the same date gives a different answer. To read 0.2.x's series,
name their concepts:

```shell
$ pyeconomics models run macro.policy_rule --calculation taylor_1993 --as-of 2024-06-28 --concept inflation=us.inflation.pce_trimmed_mean.yoy --concept neutral_real_rate=us.treasury.real_10y --concept previous_rate=us.policy_rate.target_upper
```

| 0.2.x FRED series | 1.0 concept | Read by default? |
|-------------------|-------------|------------------|
| `PCETRIM12M159SFRBDAL` | `us.inflation.pce_trimmed_mean.yoy` | No: `us.inflation.pce_core.yoy` |
| `UNRATE` | `us.unemployment.rate` | Yes |
| `NROU` | `us.unemployment.noncyclical_rate` | Yes |
| `DFII10` | `us.treasury.real_10y` | No: `us.neutral_rate.hlw` |
| `DFEDTARU` | `us.policy_rate.target_upper` | No: `us.policy_rate.effective` |

(several-rules-or-dates)=

## Several rules or dates

`calculate_policy_rule_estimates` gave one table of four rules. Loop over the
calculations instead:

```python
>>> economy = {
...     "inflation": 0.035,
...     "unemployment": 0.035,
...     "natural_unemployment": 0.042,
...     "neutral_real_rate": 0.02,
... }
>>> for calculation in ("taylor_1993", "balanced_approach"):
...     run = pyeconomics.run("macro.policy_rule", calculation=calculation, **economy)
...     print(calculation, round(run.outputs.prescribed_rate * 100, 2))
taylor_1993 6.95
balanced_approach 7.65
```

A `historical_*` function fetched a history and returned a table. With your own
table, `run_batch` gives one row per date, in order:

```python
>>> import pandas as pd
>>> history = pd.DataFrame(
...     {
...         "calculation": ["taylor_1993"] * 3,
...         "inflation": [0.035, 0.03, 0.025],
...         "unemployment": [0.035, 0.04, 0.045],
...         "natural_unemployment": [0.042, 0.042, 0.042],
...         "neutral_real_rate": [0.02, 0.02, 0.02],
...     }
... )
>>> batch = pyeconomics.run_batch("macro.policy_rule", history)
>>> batch.to_pandas()["outputs.prescribed_rate"].round(4).tolist()
[0.0695, 0.057, 0.0445]
```

To read data as it stood on each date instead, run `bind` once per date. That
reads real-time vintages where a source keeps them, and labels revised data where
one does not. 0.2.x's forward-fill of missing months is gone too: each field reads
its last observation on or before the date, by a rule the model declares.

## Next

{doc}`tutorials/index` walks through 1.0 from the start, and the
{doc}`macro.policy_rule page </reference/models/macro/policy_rule>` has the rules'
formulas and every input.
