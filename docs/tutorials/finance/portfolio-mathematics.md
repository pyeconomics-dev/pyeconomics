---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
---

# Portfolio mathematics

Harry Markowitz's 1952 paper changed the question from which asset is best to how
assets behave together. This notebook follows that thread: how combining assets
lowers risk, which combinations are worth holding, how much of them a given
investor should want, and how to judge the result afterwards.

```{code-cell} ipython3
:tags: [remove-cell]

# Keep model and notebook execution offline after the local kernel starts.
from pytest_socket import disable_socket

disable_socket()
```

## Two assets

A portfolio's expected return is the weighted average of its assets' expected
returns. Its risk is not. Volatility depends on how the assets move together,
which the correlation measures. Here are two invented assets, held 60/40.

```{code-cell} ipython3
import pandas as pd

import pyeconomics


def mixed(correlation: float) -> float:
    """Return the volatility of the 60/40 mix at a given correlation."""
    return pyeconomics.run(
        "portfolio.mean_variance",
        calculation="portfolio",
        expected_returns=[0.10, 0.06],
        volatilities=[0.20, 0.10],
        correlations=[[1.0, correlation], [correlation, 1.0]],
        weights=[0.6, 0.4],
    ).outputs.volatility


weighted_average = 0.6 * 0.20 + 0.4 * 0.10

table = pd.DataFrame({"correlation": [0.9, 0.5, 0.0, -0.5]})
table["volatility"] = table["correlation"].map(mixed)
assert table["volatility"].is_monotonic_decreasing
assert (table["volatility"] < weighted_average).all()
table.round(4)
```

The weighted average of the two volatilities is 16%, and the portfolio would match
it only if the assets moved in perfect step. The model refuses that case, because
some mix of the two would then have no variance at all. Anywhere below it the
swings partly cancel, while the return stays the same. That free reduction in risk
is diversification.

## The frontier

With more assets there are endless mixes. Markowitz's answer was to keep only the
efficient ones: for each target return, the mix with the smallest variance. Here
are three invented assets. The inputs are assumptions rather than estimates, and
short sales are allowed.

```{code-cell} ipython3
assets = {
    "expected_returns": [0.08, 0.12, 0.15],
    "volatilities": [0.15, 0.20, 0.25],
    "correlations": [[1.0, 0.3, 0.2], [0.3, 1.0, 0.5], [0.2, 0.5, 1.0]],
}

frontier = pyeconomics.run(
    "portfolio.mean_variance", calculation="frontier", points=7, **assets
).outputs

curve = pd.DataFrame(
    {"expected return": frontier.target_returns, "volatility": frontier.volatilities}
)
assert curve["volatility"].is_monotonic_increasing
curve.round(4)
```

The frontier starts at the mix with the least risk of all, and each step up in
return costs more volatility than the one before. Below that starting point lie
mixes no one should choose, because a higher return is available for the same
risk. Robert Merton worked out the shape of this curve in closed form in 1972.

```{code-cell} ipython3
least = pyeconomics.run(
    "portfolio.mean_variance", calculation="minimum_variance", **assets
).outputs

assert least.volatility < min(assets["volatilities"])
assert round(sum(least.weights), 10) == 1
{"weights": [round(weight, 3) for weight in least.weights], "volatility": round(least.volatility, 4)}
```

The least risky mix is less volatile than the least volatile asset on its own.

## Adding a safe asset

James Tobin added one more thing in 1958: a safe asset you can lend at or borrow
at. Mixing it with any risky portfolio gives a straight line from the safe rate,
and the steepest such line touches the frontier at the tangency portfolio. Every
investor then holds that same risky mix, in more or less, with the rest in the safe
asset. William Sharpe built the capital asset pricing model on that result in 1964.

```{code-cell} ipython3
safe_rate = 0.03
tangency = pyeconomics.run(
    "portfolio.mean_variance",
    calculation="tangency",
    risk_free_rate=safe_rate,
    **assets,
).outputs

reward_to_risk = (tangency.expected_return - safe_rate) / tangency.volatility
assert round(tangency.capital_market_line_slope, 10) == round(reward_to_risk, 10)
{
    "weights": [round(weight, 3) for weight in tangency.weights],
    "expected return": round(tangency.expected_return, 4),
    "volatility": round(tangency.volatility, 4),
    "slope": round(tangency.capital_market_line_slope, 4),
}
```

The slope of that line, the capital market line, is the extra return earned for
each unit of volatility. It is the highest such ratio any portfolio here reaches.

```{code-cell} ipython3
ratios = (curve["expected return"] - safe_rate) / curve["volatility"]
assert (ratios <= tangency.capital_market_line_slope + 1e-12).all()
ratios.round(4).tolist()
```

## How much risk to take

The tangency portfolio settles what to hold. How much of it depends on the
investor. A simple way to express that is a utility: expected return less a
penalty for variance, scaled by a risk-aversion number. John Pratt showed in 1964
how to measure risk aversion. Maximising that utility gives a formula for the
share to put in the risky portfolio.

```{code-cell} ipython3
def share(risk_aversion: float) -> float:
    """Return the share of the tangency portfolio at a level of risk aversion."""
    return pyeconomics.run(
        "portfolio.utility",
        calculation="optimal_risky_share",
        expected_return=tangency.expected_return,
        risk_free_rate=safe_rate,
        volatility=tangency.volatility,
        risk_aversion=risk_aversion,
    ).outputs.optimal_share


shares = pd.DataFrame({"risk aversion": [2.0, 4.0, 8.0]})
shares["risky share"] = shares["risk aversion"].map(share)
assert shares["risky share"].is_monotonic_decreasing
shares.round(3)
```

Doubling the risk aversion halves the share. A value above one means borrowing to
hold more than all of your money in the risky mix, which the formula allows and
real life makes harder.

## Judging the result

Afterwards, the question is whether the return was worth the risk. Each classic
measure answers it against a different yardstick:

- the **Sharpe ratio** (1966) divides excess return by total volatility;
- the **Treynor ratio** (1965) divides it by beta, the exposure to the market;
- **Jensen's alpha** (1968) is the return left over after allowing for that beta;
- the **Sortino ratio** (1994) counts only downside volatility in the denominator;
- **M²** (Modigliani and Modigliani, 1997) restates the Sharpe ratio as a return,
  at the benchmark's level of risk.

```{code-cell} ipython3
measures = pyeconomics.run(
    "performance.risk_adjusted",
    returns=[0.021, -0.013, 0.034, 0.008, -0.022, 0.015, 0.027, -0.005, 0.012, 0.019, -0.031, 0.024],
    benchmark_returns=[0.018, -0.01, 0.029, 0.011, -0.025, 0.012, 0.022, -0.002, 0.01, 0.016, -0.028, 0.02],
    risk_free_returns=[0.002] * 12,
    periods_per_year=12,
).outputs

pd.Series(
    {
        "Sharpe ratio": measures.sharpe_ratio,
        "Treynor ratio": measures.treynor_ratio,
        "Jensen's alpha": measures.jensen_alpha,
        "Sortino ratio": measures.sortino_ratio,
        "M²": measures.m_squared,
        "beta": measures.beta,
    }
).round(4)
```

A year of monthly returns is far too little to tell skill from luck. These ratios
describe what happened, and on so short a record they say almost nothing about
what comes next.

The weights here follow directly from assumed inputs, and they are very sensitive
to them: a small change in an expected return can move a weight a long way. These
numbers are invented, this example is educational, and no portfolio here is
investment advice or a suggestion to hold it.

## Next

The {doc}`in-browser frontier </wasm/index>` lets you change these assumptions
and watch the curve move, with nothing to install.

## References

- Jensen, M. C. (1968). The performance of mutual funds in the period 1945-1964.
  *The Journal of Finance*, 23(2), 389-416.
  <https://doi.org/10.1111/j.1540-6261.1968.tb00815.x>
- Markowitz, H. (1952). Portfolio selection. *The Journal of Finance*, 7(1), 77-91.
  <https://doi.org/10.1111/j.1540-6261.1952.tb01525.x>
- Merton, R. C. (1972). An analytic derivation of the efficient portfolio
  frontier. *Journal of Financial and Quantitative Analysis*, 7(4), 1851-1872.
  <https://doi.org/10.2307/2329621>
- Modigliani, F. and Modigliani, L. (1997). Risk-adjusted performance. *The Journal
  of Portfolio Management*, 23(2), 45-54. <https://doi.org/10.3905/jpm.23.2.45>
- Pratt, J. W. (1964). Risk aversion in the small and in the large. *Econometrica*,
  32(1/2), 122-136. <https://doi.org/10.2307/1913738>
- Sharpe, W. F. (1964). Capital asset prices: a theory of market equilibrium under
  conditions of risk. *The Journal of Finance*, 19(3), 425-442.
  <https://doi.org/10.1111/j.1540-6261.1964.tb02865.x>
- Sharpe, W. F. (1966). Mutual fund performance. *The Journal of Business*, 39(1),
  119-138. <https://doi.org/10.1086/294846>
- Sharpe, W. F. (1994). The Sharpe ratio. *The Journal of Portfolio Management*,
  21(1), 49-58. <https://doi.org/10.3905/jpm.1994.409501>
- Sortino, F. A. and Price, L. N. (1994). Performance measurement in a downside
  risk framework. *The Journal of Investing*, 3(3), 59-64.
  <https://doi.org/10.3905/joi.3.3.59>
- Tobin, J. (1958). Liquidity preference as behavior towards risk. *The Review of
  Economic Studies*, 25(2), 65-86. <https://doi.org/10.2307/2296205>
- Treynor, J. L. (1965). How to rate management of investment funds. *Harvard
  Business Review*, 43(1), 63-75.
- The models used here: {doc}`/reference/models/portfolio/mean_variance`,
  {doc}`/reference/models/portfolio/utility` and
  {doc}`/reference/models/performance/risk_adjusted`.
