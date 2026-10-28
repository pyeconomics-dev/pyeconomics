# MCP agent evaluations

The MCP server's tool descriptions are tested by giving a real agent questions it can answer only through the tools (`scripts/mcp_agent_eval.py`, tasks in `scripts/mcp/agent_tasks.py`). The agent runs headless with `pyeconomics mcp` as its only MCP server and no other tool; FRED's and ALFRED's keys are withheld, so the `llm_use` gate is what refuses their data. A task succeeds when the agent calls its tools in order and answers the value the Python API computes from the same data, within the task's tolerance. CI runs the same tasks' scripted calls (`tests/mcp/test_mcp_agent_tasks.py`).

## Latest run

- Date: 2026-10-28
- Agent: Claude Code 2.1.284, headless (claude -p)
- Model: `claude-sonnet-5-5`
- Server: pyeconomics 1.0.0b1.dev1, from the working tree at commit `3a9fde9`
- Result: 9 of 9 tasks succeeded
- Tool list: 21 tools, 369,901 bytes of names, descriptions and schemas; the agent's first request held 2,538 tokens without the server and 71,927 with it

| Task | Result | Tool calls | Answer | Expected |
|------|--------|------------|--------|----------|
| `discover_convexity` | succeeded | `search_models`, `describe_model`, `run_model` | 75.29958076997512 | 75.29958076997512 |
| `bond_duration` | succeeded | `fixed_income_duration` | 7.919141259916497 | 7.919141259916497 |
| `bond_price` | succeeded | `fixed_income_bond_pricing` | 96.1027094285883 | 96.1027094285883 |
| `option_price` | succeeded | `derivatives_black_scholes_merton` | 5.779936227686569 | 5.779936227686569 |
| `mortgage_payment` | succeeded | `foundations_time_value` | 1498.876312881881 | 1498.876312881881 |
| `recession_probability_bound` | succeeded | `search_models`, `run_model` | 0.30517900068803827 | 0.30517900068803827 |
| `unemployment_series` | succeeded | `get_series` | 0.041 | 0.040999999999999995 |
| `withheld_sources` | succeeded | `list_sources` | 16.0 | 16 |
| `forbidden_series` | succeeded | `get_series` | unavailable | llm-use-forbidden |

## Each task

### discover_convexity

> Using the pyeconomics tools, find the model for bond convexity and compute the analytical convexity of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity.

1. `search_models` {"query": "convexity"}
2. `describe_model` {"model_id": "fixed_income.convexity"}
3. `run_model` {"inputs": {"calculation": "analytical", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}, "model_id": "fixed_income.convexity"}

The agent's answer:

```text
The pyeconomics model `fixed_income.convexity` (analytical calculation) gives a convexity of about 75.2996 years². I ran it with these inputs:

- **Dates:** settlement 2026-01-15, maturity 2036-01-15
- **Coupon:** 4.5%, paid semiannually
- **Yield to maturity:** 5%
- **Other settings:** the model's defaults (act/act ICMA day count, face value 100, redemption 100)

The full price at settlement was 96.1027.

ANSWER: 75.29958076997512
```

### bond_duration

> What is the modified duration of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_duration` {"calculation": "macaulay_modified", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The modified duration is about 7.919 years. The tool also returned a Macaulay duration of 8.117 years and a full price of 96.10 per 100 of face value.

ANSWER: 7.919141259916497
```

### bond_price

> What is the full price, per 100 of face value, of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_bond_pricing` {"calculation": "price_from_yield", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The full price is 96.1027 per 100 of face value. Settlement falls on a coupon date, so accrued interest is 0 and the full and flat prices are the same.

ANSWER: 96.1027094285883
```

### option_price

> Price a European call option with the Black-Scholes-Merton model: spot 100, strike 105, six months to expiry, a 4% risk-free rate, 25% volatility and no dividends.

1. `derivatives_black_scholes_merton` {"calculation": "price", "dividend_yield": 0, "option_type": "call", "risk_free_rate": 0.04, "spot": 100, "strike": 105, "volatility": 0.25, "years": 0.5}

The agent's answer:

```text
The Black-Scholes-Merton price of the European call is about 5.78. This uses spot 100, strike 105, 0.5 years to expiry, a 4% risk-free rate, 25% volatility and no dividends.

The tool also returned these Greeks:
- **Delta:** 0.4703
- **Gamma:** 0.02251
- **Vega:** 28.13
- **Theta:** -8.683
- **Rho:** 20.63

ANSWER: 5.779936227686569
```

### mortgage_payment

> What is the monthly payment on a 250,000 mortgage over 30 years at 6% a year, compounded monthly? Give the payment as a positive amount.

1. `foundations_time_value` {"calculation": "amortization", "periods": 360, "principal": 250000, "rate": 0.005}

The agent's answer:

```text
The monthly payment is about 1,498.88. I used the amortization tool with a monthly rate of 0.5% (6% ÷ 12) over 360 payments. It returned a level payment of 1,498.8763128818810.

ANSWER: 1498.876312881881
```

### recession_probability_bound

> What probability of a US recession twelve months ahead did the New York Fed's yield-curve model give as of 2025-06-30, with its inputs bound to the data catalog as of that date?

1. `search_models` {"query": "recession probability yield curve"}
2. `run_model` {"as_of": "2025-06-30", "model_id": "macro.recession_probability"}

The agent's answer:

```text
The New York Fed yield-curve model gave a 12-month-ahead US recession probability of about 30.5% as of 2025-06-30.

- **Inputs:** The model pulled the 10-year Treasury yield (4.3835%) and the 3-month yield (4.4210%, bond-equivalent basis) from the data catalog as of that date.
- **Spread:** The 10-year minus 3-month spread was about −0.04 percentage points, so the curve was slightly inverted.
- **Caveat:** The tool flagged both yields as revised data. They are the latest values, not necessarily those published on 2025-06-30.

ANSWER: 0.30517900068803827
```

### unemployment_series

> What was the US unemployment rate for June 2025 in the data catalog, and which source must the figure be credited to?

1. `get_series` {"end": "2025-06-30", "start": "2025-06-01", "target": "us.unemployment.rate"}

The agent's answer:

```text
The US unemployment rate for June 2025 in the catalog is 0.041, which is 4.1%. This is the seasonally adjusted rate (BLS series LNS14000000, from the Current Population Survey). The tool returned it as 0.040999999999999995, a floating-point artifact of 0.041.

You must credit it as "Source: U.S. Bureau of Labor Statistics."

The BLS terms also require this notice: "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov. Data accessed through the BLS Public Data API on 2026-10-28."

ANSWER: 0.041
```

### withheld_sources

> How many of the data providers does this server's policy keep from reaching an AI assistant?

1. `list_sources` {}

The agent's answer:

```text
The server's policy keeps 16 of the 31 listed providers from reaching an AI assistant. These are the ones with `llm_permitted: false`:

- AQR
- Atlanta Fed
- Cboe
- Cleveland Fed
- Coin Metrics
- Damodaran
- DBnomics
- FRED
- Hou-Xue-Zhang
- IMF
- JKP
- Ken French
- Open Source Asset Pricing
- Philadelphia Fed
- Shiller
- Yahoo Finance

The other 15 are permitted.

Damodaran is marked `hosted_allowed: true` and `licence: hosted-safe`, but it is still `llm_permitted: false`, because its `llm_use` is "unclear". I counted it as blocked.

ANSWER: 16
```

### forbidden_series

> Fetch the FRED series GDP (fred:GDP) and tell me its latest value.

1. `get_series` {"target": "fred:GDP"} → llm-use-forbidden

The agent's answer:

```text
The pyeconomics tools couldn't fetch `fred:GDP`. The server returned a 403 because FRED's terms (licence class "library-only") don't allow its data to reach a language model, and the server's allowed-only policy enforces that. I haven't tried another route to get the number.

ANSWER: unavailable
```
