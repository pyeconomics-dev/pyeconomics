---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
---

# Return statistics

Almost everything in finance is measured in returns rather than prices, because a
return can be compared across assets and across time. This notebook takes a year
of prices and works out what they say: the returns, the average that matters, the
annual rate, and the risk.

```{code-cell} ipython3
:tags: [remove-cell]

# Keep model and notebook execution offline after the local kernel starts.
from pytest_socket import disable_socket

disable_socket()
```

## From prices to returns

Here are thirteen month-end prices of an invented fund, which give twelve monthly
returns. A simple return is the change in price over the starting price, and
pandas calls that `pct_change`.

```{code-cell} ipython3
import math

import pandas as pd

import pyeconomics

prices = pd.Series(
    [100.0, 102.1, 100.8, 104.2, 105.1, 102.8, 104.3, 107.1, 106.6, 107.9, 110.0, 106.6, 109.2],
    name="price",
)
returns = prices.pct_change().dropna()
returns.round(4).tolist()
```

Simple returns do not add up over time. A fall of 50% followed by a rise of 50%
leaves you with 75, not 100. The right way to chain them is to compound.

```{code-cell} ipython3
compounded = (1 + returns).prod() - 1
assert round(compounded, 10) == round(prices.iloc[-1] / prices.iloc[0] - 1, 10)
assert returns.sum() != compounded
{"compounded": round(compounded, 4), "plain sum": round(returns.sum(), 4)}
```

## Log returns

A log return is the natural logarithm of one plus the simple return. It describes
the same change in price, on a scale where changes do add. Log prices are also
how M. F. M. Osborne described the movement of stock prices in 1959, and they are
why the simulations in {doc}`monte-carlo` work in logs.

```{code-cell} ipython3
logs = pyeconomics.run(
    "foundations.returns",
    calculation="log",
    returns=returns.tolist(),
    direction="simple_to_log",
).outputs.converted

assert round(sum(logs), 10) == round(math.log(prices.iloc[-1] / prices.iloc[0]), 10)
round(sum(logs), 4)
```

The sum of the log returns is the log return of the whole year. Which to use
depends on the job. Log returns suit adding across time, and simple returns suit
adding across a portfolio, where a portfolio's return is the weighted sum of its
assets' simple returns.

## The average that matters

The arithmetic mean answers one question: what return should I expect next month?
The geometric mean answers another: what steady monthly return would have taken me
from the first price to the last? When returns vary, the second is always lower,
and the more they vary, the wider the gap.

```{code-cell} ipython3
means = pyeconomics.run(
    "foundations.returns", calculation="means", returns=returns.tolist()
).outputs

steady = prices.iloc[0] * (1 + means.geometric) ** len(returns)
assert round(steady, 8) == round(prices.iloc[-1], 8)
assert means.harmonic <= means.geometric <= means.arithmetic
{"arithmetic": round(means.arithmetic, 5), "geometric": round(means.geometric, 5)}
```

The harmonic mean sits below both. That ordering is the inequality of means.

## Annual rates

To compare this with a quoted annual figure, compound the geometric monthly rate
over twelve months. The inputs say how long the return took: one month, of twelve
in a year.

```{code-cell} ipython3
annual = pyeconomics.run(
    "foundations.returns",
    calculation="annualized",
    period_return=means.geometric,
    periods=1,
    periods_per_year=12,
).outputs.annualized_return

assert round(annual, 10) == round(compounded, 10)
round(annual, 4)
```

With exactly a year of data, the annual rate is the year's return, as it should
be. A return also lives alongside inflation, and Irving Fisher's relation takes
one out of the other. Dividing the gross returns is exact, while the subtraction
you may have seen is its approximation.

```{code-cell} ipython3
real = pyeconomics.run(
    "foundations.returns", calculation="real", nominal=annual, inflation=0.03
).outputs.real

assert round((1 + real) * 1.03 - 1, 10) == round(annual, 10)
round(real, 4)
```

## Risk

Volatility is the standard deviation of returns. Annualizing it multiplies by the
square root of the periods in a year, which is sound only if returns are
independent from one month to the next. This is an assumption, and a real series
often breaks it.

```{code-cell} ipython3
spread = pyeconomics.run(
    "foundations.risk_statistics",
    calculation="volatility",
    returns=returns.tolist(),
    periods_per_year=12,
).outputs

assert round(spread.volatility, 12) == round(returns.std(), 12)
assert round(spread.annualized_volatility, 12) == round(spread.volatility * 12**0.5, 12)
{"monthly": round(spread.volatility, 4), "annual": round(spread.annualized_volatility, 4)}
```

The first check shows the model agrees with pandas, and `std()` divides by `n - 1`
in the same way. Most investors mind falls more than rises, and Sortino and Price
built a measure on that thought. Semideviation counts only the returns below a
target.

```{code-cell} ipython3
downside = pyeconomics.run(
    "foundations.risk_statistics",
    calculation="semideviation",
    returns=returns.tolist(),
    target=0,
).outputs
round(downside.below_target, 4)
```

Two statistics describe the shape of the distribution. Skewness is negative when
the large moves are mostly falls, and excess kurtosis is positive when large moves
of either kind are more common than a normal distribution allows. Joanes and Gill
compared the ways of estimating them. A year of data is a thin basis for either,
so treat these two as illustrations.

```{code-cell} ipython3
shape = pyeconomics.run(
    "foundations.risk_statistics", calculation="moments", returns=returns.tolist()
).outputs
{"skewness": round(shape.skewness, 3), "excess kurtosis": round(shape.excess_kurtosis, 3)}
```

Maximum drawdown is the worst fall from a peak. It works on values rather than
returns, and it is the figure that describes what living through the year felt
like.

```{code-cell} ipython3
drawdown = pyeconomics.run(
    "foundations.risk_statistics", calculation="drawdown", values=prices.tolist()
).outputs

worst = (1 - prices / prices.cummax()).max()
assert round(drawdown.max_drawdown, 12) == round(worst, 12)
{
    "maximum drawdown": round(drawdown.max_drawdown, 4),
    "from month": drawdown.peak_index,
    "to month": drawdown.trough_index,
}
```

`cummax` tracks the running peak, so one line of pandas reproduces the model's
answer. That is a good habit in itself: check a library against a calculation you
understand.

These numbers are invented. This example is educational, not investment advice,
and a past return says nothing certain about a future one.

## Next

{doc}`monte-carlo` runs the idea the other way: instead of measuring one path of
returns that happened, it draws thousands that might.

## References

- Bacon, C. R. (2008). *Practical Portfolio Performance Measurement and
  Attribution*, 2nd ed. Wiley.
- Fisher, I. (1930). *The Theory of Interest*. Macmillan.
- Hardy, G. H., Littlewood, J. E. and Polya, G. (1952). *Inequalities*, 2nd ed.
  Cambridge University Press.
- Joanes, D. N. and Gill, C. A. (1998). Comparing measures of sample skewness and
  kurtosis. *Journal of the Royal Statistical Society: Series D (The
  Statistician)*, 47(1), 183-189. <https://doi.org/10.1111/1467-9884.00122>
- Osborne, M. F. M. (1959). Brownian motion in the stock market. *Operations
  Research*, 7(2), 145-173. <https://doi.org/10.1287/opre.7.2.145>
- Sortino, F. A. and Price, L. N. (1994). Performance measurement in a downside
  risk framework. *The Journal of Investing*, 3(3), 59-64.
  <https://doi.org/10.3905/joi.3.3.59>
- The models used here: {doc}`/reference/models/foundations/returns` and
  {doc}`/reference/models/foundations/risk_statistics`.
