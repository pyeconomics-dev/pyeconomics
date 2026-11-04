---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
---

# pandas with pyeconomics results

pandas, which Wes McKinney built for working with financial time series, is where
most finance work in Python ends up. This notebook moves results into pandas,
lines up two models' answers in one table, and writes the table out without
losing track of where its numbers came from.

```{code-cell} ipython3
:tags: [remove-cell]

# Keep model and notebook execution offline after the local kernel starts.
from pytest_socket import disable_socket

disable_socket()
```

## A result is one row

A run gives a `Result`. `to_pandas()` turns it into a DataFrame with one row: the
inputs under `inputs.`, the outputs under `outputs.`, and the result's hash last.

```{code-cell} ipython3
import pyeconomics

bond = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
}

result = pyeconomics.run(
    "fixed_income.bond_pricing",
    calculation="price_from_yield",
    yield_to_maturity=0.05,
    **bond,
)
row = result.to_pandas()
assert len(row) == 1
row[["inputs.coupon_rate", "inputs.yield_to_maturity", "outputs.flat_price"]]
```

Dates arrive as dates and numbers as numbers, so you can sort, filter and
calculate at once. Every rate is a decimal: `0.05` is five percent, here and
everywhere else in the library.

## A batch is a table

Trying one calculation across many inputs is a matter of writing the inputs as a
table. Each column of the DataFrame names an input, each row is one run, and
`run_batch` returns a row of results for each, in the same order.

```{code-cell} ipython3
import pandas as pd

yields = pd.DataFrame(
    {
        "calculation": "price_from_yield",
        "yield_to_maturity": [0.03, 0.04, 0.045, 0.05, 0.06],
    }
).assign(**bond)

prices = pyeconomics.run_batch("fixed_income.bond_pricing", yields).to_pandas()
assert len(prices) == len(yields)
prices[["inputs.yield_to_maturity", "outputs.flat_price"]]
```

The price falls as the yield rises, and the bond sells at exactly par, 100, where
the yield equals its coupon. The fall is also uneven: each step up in the yield
costs a little less than the step before.

```{code-cell} ipython3
at_the_coupon = prices.set_index("inputs.yield_to_maturity").loc[0.045]
assert round(at_the_coupon["outputs.flat_price"], 8) == 100
```

## Joining two models

Two models often describe one thing. Here a second batch asks for the same bond's
duration, which measures how sensitive its price is to the yield. The two tables
share their input columns, so `merge` lines them up by the yield.

```{code-cell} ipython3
durations = pyeconomics.run_batch(
    "fixed_income.duration",
    yields.assign(calculation="macaulay_modified"),
).to_pandas()

joined = prices.merge(
    durations,
    on="inputs.yield_to_maturity",
    suffixes=(".price", ".duration"),
    validate="one_to_one",
)
table = joined[
    [
        "inputs.yield_to_maturity",
        "outputs.flat_price",
        "outputs.modified_duration",
    ]
].rename(
    columns={
        "inputs.yield_to_maturity": "yield",
        "outputs.flat_price": "price",
        "outputs.modified_duration": "modified duration",
    }
)
table
```

`validate="one_to_one"` is worth the extra argument: it stops the join rather than
quietly multiplying rows if a key turns up twice.

Now a question neither model answers alone. Modified duration estimates a price
change, in percent, for a change in the yield. How good is that estimate over a
whole percentage point?

```{code-cell} ipython3
at_four = table.set_index("yield").loc[0.04]
at_five = table.set_index("yield").loc[0.05]

estimate = -at_four["modified duration"] * 0.01 * at_four["price"]
actual = at_five["price"] - at_four["price"]
assert actual > estimate
{"estimated change": round(estimate, 3), "actual change": round(actual, 3)}
```

The estimate is a little too pessimistic. A straight line overstates the fall,
because the price curve bends, and that bend is what convexity measures.

## Keeping the record

A table of numbers is only as useful as your memory of what produced it. The
`result_sha256` column is a fingerprint of a run's inputs and outputs, so a row
can always be matched to the run that made it, and two runs that agree have the
same hash.

```{code-cell} ipython3
again = pyeconomics.run(
    "fixed_income.bond_pricing",
    calculation="price_from_yield",
    yield_to_maturity=0.05,
    **bond,
)
assert again.to_pandas().loc[0, "result_sha256"] == row.loc[0, "result_sha256"]
row.loc[0, "result_sha256"][:16]
```

`pyeconomics.exports.export` writes a result or a batch to CSV, Excel, Parquet,
Arrow or JSON. A CSV file carries the record in its leading `#` lines, which
`comment="#"` skips on the way back in. `float_precision="round_trip"` keeps
every digit.

```{code-cell} ipython3
import tempfile
from pathlib import Path

from pyeconomics.exports import export

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "prices.csv"
    export(result, "csv", path)
    header = path.read_text(encoding="utf-8").splitlines()[:4]
    back = pd.read_csv(path, comment="#", float_precision="round_trip")

assert back.loc[0, "outputs.flat_price"] == result.outputs.flat_price
header
```

The {doc}`exports guide </exports>` covers the other formats, and the
{doc}`how-to guide </how-to/pandas>` covers data series and Parquet.

This example is educational, not investment advice. The bond and its yields are
invented.

## Next

{doc}`return-statistics` starts from a price series and works out what can be
said about its returns and its risk.

## References

- McKinney, W. (2010). Data structures for statistical computing in Python.
  *Proceedings of the 9th Python in Science Conference*, 56-61.
  <https://doi.org/10.25080/Majora-92bf1922-00a>
- Macaulay, F. R. (1938). *Some Theoretical Problems Suggested by the Movements
  of Interest Rates, Bond Yields and Stock Prices in the United States since
  1856*. National Bureau of Economic Research.
- The models used here: {doc}`/reference/models/fixed_income/bond_pricing` and
  {doc}`/reference/models/fixed_income/duration`.
