# MCP agent evaluations

The MCP server's tool descriptions are tested by giving a real agent questions it can answer only through the tools (`scripts/mcp_agent_eval.py`, tasks in `scripts/mcp/agent_tasks.py`). The agent runs headless with `pyeconomics mcp` as its only MCP server and no other tool; FRED's and ALFRED's keys are withheld, so the `llm_use` gate is what refuses their data. A task succeeds when the agent calls its tools in order and answers the value the Python API computes from the same data, within the task's tolerance. CI runs the same tasks' scripted calls (`tests/mcp/test_mcp_agent_tasks.py`).

## Latest run

- Date: 2026-10-26
- Agent: Claude Code 2.1.284, headless (claude -p)
- Model: `claude-sonnet-5-5`
- Server: pyeconomics 1.0.0b1.dev1, from the working tree at commit `15c91bf`
- Result: 9 of 9 tasks succeeded
- Tool list: 21 tools, 369,901 bytes of names, descriptions and schemas; the agent's first request held 2,760 tokens without the server and 72,142 with it

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
I used the `fixed_income.convexity` model (Bond convexity) with the `analytical` calculation. The inputs were settlement 2026-01-15, maturity 2036-01-15, a 4.5% coupon paid semiannually and a 5% yield to maturity. The other inputs took the model's defaults: act/act ICMA day count, face value 100 and redemption 100.

The convexity is about 75.2996 years squared, and the full price is about 96.1027.

ANSWER: 75.29958076997512
```

### bond_duration

> What is the modified duration of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_duration` {"calculation": "macaulay_modified", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The modified duration is about 7.919 years. For this bond, the tool also returned a Macaulay duration of 8.117 years and a full price of 96.10.

ANSWER: 7.919141259916497
```

### bond_price

> What is the full price, per 100 of face value, of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_bond_pricing` {"calculation": "price_from_yield", "coupon_rate": 0.045, "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The full price is 96.1027 per 100 of face value. Settlement falls on a coupon date, so accrued interest is zero and the full price equals the flat price. The tool used its default street convention and act/act ICMA day count, with 20 semiannual payments.

ANSWER: 96.1027094285883
```

### option_price

> Price a European call option with the Black-Scholes-Merton model: spot 100, strike 105, six months to expiry, a 4% risk-free rate, 25% volatility and no dividends.

1. `derivatives_black_scholes_merton` {"calculation": "price", "dividend_yield": 0, "option_type": "call", "risk_free_rate": 0.04, "spot": 100, "strike": 105, "volatility": 0.25, "years": 0.5}

The agent's answer:

```text
The Black-Scholes-Merton price of the call is about 5.78. That is for spot 100, strike 105, 0.5 years, a 4% risk-free rate, 25% volatility and no dividends.

The tool also returned these Greeks:
- **Delta:** 0.4703
- **Gamma:** 0.02251
- **Vega:** 28.13
- **Theta:** -8.683
- **Rho:** 20.63

The put-call parity residual was effectively zero (about 7e-15).

ANSWER: 5.779936227686569
```

### mortgage_payment

> What is the monthly payment on a 250,000 mortgage over 30 years at 6% a year, compounded monthly? Give the payment as a positive amount.

1. `foundations_time_value` {"calculation": "amortization", "periods": 360, "principal": 250000, "rate": 0.005}

The agent's answer:

```text
The monthly payment is about 1,498.88. This is a 250,000 loan at 0.5% per month (6% a year, compounded monthly) over 360 payments. The tool returned a level payment of 1,498.876312881881.

ANSWER: 1498.876312881881
```

### recession_probability_bound

> What probability of a US recession twelve months ahead did the New York Fed's yield-curve model give as of 2025-06-30, with its inputs bound to the data catalog as of that date?

1. `search_models` {"query": "recession probability yield curve New York Fed"}
2. `run_model` {"as_of": "2025-06-30", "model_id": "macro.recession_probability"}

The agent's answer:

```text
The New York Fed's yield-curve model gave a recession probability of about 30.5% for twelve months ahead as of 2025-06-30. I ran the `macro.recession_probability` model with its inputs bound to the data catalog as of that date.

The bound inputs came from the US Treasury:
- **10-year yield:** 4.3835%
- **3-month yield:** 4.421% (bond-equivalent basis)
- **Spread:** about -0.04 percentage points, so the curve was just barely inverted.

The tool warned that these yields are the latest revised values, not the ones published on 2025-06-30. A true real-time evaluation could differ slightly.

ANSWER: 0.30517900068803827
```

### unemployment_series

> What was the US unemployment rate for June 2025 in the data catalog, and which source must the figure be credited to?

1. `get_series` {"end": "2025-06-30", "start": "2025-06-01", "target": "us.unemployment.rate"}

The agent's answer:

```text
The catalog gives a US unemployment rate of 0.041 (4.1%) for June 2025. It is the seasonally adjusted rate, BLS series LNS14000000, from the Current Population Survey.

Credit the figure as "Source: U.S. Bureau of Labor Statistics." The BLS terms also require this notice: "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov. Data accessed through the BLS Public Data API on 2026-10-26."

ANSWER: 0.041
```

### withheld_sources

> How many of the data providers does this server's policy keep from reaching an AI assistant?

1. `list_sources` {}

The agent's answer:

```text
16 of the 31 listed providers have `llm_permitted: false`, so the server's policy keeps their data from reaching an AI assistant. They are:

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

Damodaran is the odd one out. Its licence is hosted-safe, but its `llm_use` is "unclear" and the policy still blocks it. I counted it as blocked because the question is about the policy, not the licence class.

ANSWER: 16
```

### forbidden_series

> Fetch the FRED series GDP (fred:GDP) and tell me its latest value.

1. `get_series` {"target": "fred:GDP"} → llm-use-forbidden

The agent's answer:

```text
I couldn't fetch it. The pyeconomics server refused the request for `fred:GDP` with a 403. FRED's terms (https://fred.stlouisfed.org/legal/) don't allow its data to be passed to a language model, and the server's policy only permits sources that do allow it. I didn't try another route to get the number, so I have no GDP value to give you.

ANSWER: unavailable
```
