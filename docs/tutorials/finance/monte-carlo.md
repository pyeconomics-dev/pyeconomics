---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
---

# Monte Carlo simulation

Some questions have no neat formula. Monte Carlo methods answer them by brute
force: draw many possible futures at random, and read the answer off the crowd.
Nicholas Metropolis and Stanislaw Ulam published the method under that name in
1949, and Phelim Boyle brought it to option pricing in 1977. This notebook shows
the habits that make a simulation trustworthy: fixing the seed, measuring the
error, and shrinking it.

```{code-cell} ipython3
:tags: [remove-cell]

# Keep model and notebook execution offline after the local kernel starts.
from pytest_socket import disable_socket

disable_socket()
```

## A seeded run

`foundations.simulation` draws paths of geometric Brownian motion: a value that
grows at a steady rate on average, with random shocks proportional to its size,
so it can never fall below zero. Here is one year of a value that starts at 100,
with a drift of 5% and a volatility of 20%.

```{code-cell} ipython3
import math

import pandas as pd

import pyeconomics

setup = {
    "calculation": "gbm",
    "initial_value": 100,
    "drift": 0.05,
    "volatility": 0.2,
    "horizon": 1,
    "steps": 12,
    "percentiles": [0.05, 0.5, 0.95],
}

run = pyeconomics.run("foundations.simulation", paths=2000, seed=7, **setup)
run.outputs.terminal_mean, run.outputs.percentile_values
```

The seed fixes the sequence of random numbers, and that has a practical
consequence: the same seed gives the same answer, to the last digit, and so the
same `result_sha256`. A colleague can rerun your simulation and get your numbers.
A different seed gives a different estimate, and the gap between the two shows
what chance is doing.

```{code-cell} ipython3
same = pyeconomics.run("foundations.simulation", paths=2000, seed=7, **setup)
other = pyeconomics.run("foundations.simulation", paths=2000, seed=8, **setup)

assert same.manifest.result_sha256 == run.manifest.result_sha256
assert other.outputs.terminal_mean != run.outputs.terminal_mean
{"seed 7": round(run.outputs.terminal_mean, 3), "seed 8": round(other.outputs.terminal_mean, 3)}
```

A seed makes a run reproducible, not correct. Picking the seed that gives the
answer you like is a way of fooling yourself, so choose one before you look.

## How far off are we?

This case does have a formula, so the simulation can be checked against it. The
expected final value is the starting value compounded continuously at the drift.
The model reports a standard error with every estimate: the standard deviation of
the paths divided by the square root of their number.

```{code-cell} ipython3
exact = 100 * math.exp(0.05)
error = run.outputs.terminal_mean - exact

assert abs(error) < 3 * run.outputs.standard_error
{
    "exact": round(exact, 3),
    "estimate": round(run.outputs.terminal_mean, 3),
    "standard error": round(run.outputs.standard_error, 3),
}
```

The estimate falls within a few standard errors of the truth, as it should. The
standard error is what you report when no formula exists to check against.

## Convergence

Because of that square root, four times the paths gives half the error. Here is
that law at work.

```{code-cell} ipython3
sizes = [500, 2000, 8000, 32000]
results = [
    pyeconomics.run("foundations.simulation", paths=paths, seed=7, **setup).outputs
    for paths in sizes
]
convergence = pd.DataFrame(
    {
        "paths": sizes,
        "estimate": [result.terminal_mean for result in results],
        "standard error": [result.standard_error for result in results],
    }
)
convergence["ratio to previous"] = (
    convergence["standard error"].shift() / convergence["standard error"]
)
assert convergence["ratio to previous"].dropna().between(1.8, 2.2).all()
convergence.round(4)
```

That is the bad news about Monte Carlo: each extra digit of accuracy costs a
hundred times the work. So it pays to squeeze more out of the same paths.

## Antithetic variates

John Hammersley and Keith Morton's 1956 trick is to use each random draw twice,
once as it is and once with its sign flipped. A path that happened to run high is
paired with its mirror image running low, so their average swings less than two
independent paths would. The model pairs them for you and takes the standard error
from the pair averages.

```{code-cell} ipython3
plain = pyeconomics.run("foundations.simulation", paths=2000, seed=7, **setup).outputs
paired = pyeconomics.run(
    "foundations.simulation", paths=2000, antithetic=True, seed=7, **setup
).outputs

assert paired.standard_error < plain.standard_error
{
    "plain standard error": round(plain.standard_error, 4),
    "antithetic standard error": round(paired.standard_error, 4),
}
```

The same work buys a smaller error. It helps most when the result rises or falls
steadily with the random draw, as a final value does.

## What a run costs

Every model declares a cost class, which says how much computing a call may take:
`instant`, `light` or `heavy`. A simulation is `heavy`, because the work grows with
paths times steps.

```{code-cell} ipython3
from pyeconomics import registry

cost = registry.describe("foundations.simulation")["cost"]
assert cost == "heavy"
cost
```

On your own machine that is only a label, and you can wait as long as you like up
to the model's own limits: 100,000 paths of 1,000 steps. The hosted API sets a time
budget by cost class ({doc}`/api`), so a `heavy` run gets the longest
allowance and a run past it is stopped. A reasonable way to size a simulation is
to start small, read the standard error, and use the square-root law to work out
how many paths you need.

```{code-cell} ipython3
target = 0.25
needed = math.ceil(run.outputs.paths_simulated * (run.outputs.standard_error / target) ** 2)
sized = pyeconomics.run("foundations.simulation", paths=needed, seed=7, **setup).outputs

assert sized.standard_error < 1.1 * target
{"paths needed": needed, "standard error": round(sized.standard_error, 4)}
```

## Resampling what you have

A close cousin of simulation is Bradley Efron's bootstrap. When you have a small
sample and no formula for the uncertainty of a statistic, draw from the sample
itself, with replacement, many times. The spread of the statistic across those
resamples stands in for the spread you would see in fresh samples.

```{code-cell} ipython3
sample = [0.021, -0.013, 0.034, 0.008, -0.022, 0.015, 0.027, -0.005, 0.012, 0.019]
boot = pyeconomics.run(
    "foundations.simulation",
    calculation="bootstrap",
    sample=sample,
    statistic="median",
    resamples=2000,
    confidence=0.95,
    seed=7,
).outputs

assert boot.interval_lower <= boot.estimate <= boot.interval_upper
{
    "median": round(boot.estimate, 4),
    "standard error": round(boot.standard_error, 4),
    "interval": (round(boot.interval_lower, 4), round(boot.interval_upper, 4)),
}
```

The median has no simple standard-error formula, which is where the bootstrap
earns its keep. It cannot add information the sample lacks: from ten observations
the interval is only a rough guide.

These numbers are invented. This example is educational, not investment advice.

## Next

{doc}`portfolio-mathematics` turns from one asset to several, and to what holding
them together does to risk.

## References

- Boyle, P. P. (1977). Options: a Monte Carlo approach. *Journal of Financial
  Economics*, 4(3), 323-338. <https://doi.org/10.1016/0304-405X(77)90005-8>
- Efron, B. (1979). Bootstrap methods: another look at the jackknife. *The Annals
  of Statistics*, 7(1), 1-26. <https://doi.org/10.1214/aos/1176344552>
- Efron, B. and Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*.
  Chapman & Hall.
- Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer.
- Hammersley, J. M. and Morton, K. W. (1956). A new Monte Carlo technique:
  antithetic variates. *Mathematical Proceedings of the Cambridge Philosophical
  Society*, 52(3), 449-475. <https://doi.org/10.1017/S0305004100031455>
- Metropolis, N. and Ulam, S. (1949). The Monte Carlo method. *Journal of the
  American Statistical Association*, 44(247), 335-341.
  <https://doi.org/10.1080/01621459.1949.10483310>
- Osborne, M. F. M. (1959). Brownian motion in the stock market. *Operations
  Research*, 7(2), 145-173. <https://doi.org/10.1287/opre.7.2.145>
- The model used here: {doc}`/reference/models/foundations/simulation`.
