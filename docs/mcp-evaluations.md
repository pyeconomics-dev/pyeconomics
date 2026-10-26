# MCP agent evaluations

The MCP server's tool descriptions are tested by giving a real agent questions it can answer only through the tools (`scripts/mcp_agent_eval.py`, tasks in `scripts/mcp/agent_tasks.py`). The agent runs headless with `pyeconomics mcp` as its only MCP server and no other tool; FRED's and ALFRED's keys are withheld, so the `llm_use` gate is what refuses their data. A task succeeds when the agent calls its tools in order and answers the value the Python API computes from the same data, within the task's tolerance. CI runs the same tasks' scripted calls (`tests/mcp/test_mcp_agent_tasks.py`).

## Latest run

- Date: 2026-10-26
- Agent: Claude Code 2.1.284, headless (claude -p)
- Model: `claude-sonnet-5-5`
- Server: pyeconomics 1.0.0b1.dev1, from the working tree at commit `9901868`
- Result: 9 of 9 tasks succeeded
- Tool list: 21 tools, 369,901 bytes of names, descriptions and schemas; the agent's first request held 2,756 tokens without the server and 72,146 with it

| Task | Result | Tool calls | Answer | Expected |
|------|--------|------------|--------|----------|
| `discover_convexity` | succeeded | `search_models`, `describe_model`, `describe_model`, `run_model` | 75.29958076997512 | 75.29958076997512 |
| `bond_duration` | succeeded | `fixed_income_duration` | 7.919141259916497 | 7.919141259916497 |
| `bond_price` | succeeded | `fixed_income_bond_pricing`, `fixed_income_bond_pricing` | 96.1027094285883 | 96.1027094285883 |
| `option_price` | succeeded | `derivatives_black_scholes_merton` | 5.779936227686569 | 5.779936227686569 |
| `mortgage_payment` | succeeded | `foundations_time_value` | 1498.876312881881 | 1498.876312881881 |
| `recession_probability_bound` | succeeded | `search_models`, `run_model` | 0.30517900068803827 | 0.30517900068803827 |
| `unemployment_series` | succeeded | `get_series` | 0.041 | 0.040999999999999995 |
| `withheld_sources` | succeeded | `list_sources` | 16.0 | 16 |
| `forbidden_series` | succeeded | `get_series` | unavailable | llm-use-forbidden |

## Each task

### discover_convexity

> Using the pyeconomics tools, find the model for bond convexity and compute the analytical convexity of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity.

1. `search_models` {"query": "bond convexity"}
2. `describe_model` {} → error
3. `describe_model` {"model_id": "fixed_income.convexity"}
4. `run_model` {"inputs": {"calculation": "analytical", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}, "model_id": "fixed_income.convexity"}

The agent's answer:

```text
I used the `fixed_income.convexity` model (Bond convexity) with the `analytical` calculation. The inputs were:
- Settlement 2026-01-15 and maturity 2036-01-15.
- Coupon 4.5%, paid semiannually.
- Yield to maturity 5%.

The analytical convexity is about 75.2996 years squared. The full price at settlement is about 96.1027.

ANSWER: 75.29958076997512
```

### bond_duration

> What is the modified duration of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_duration` {"calculation": "macaulay_modified", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The modified duration is about 7.92 years. The tool also returned a Macaulay duration of 8.117 years and a full price of 96.10 per 100 of face value.

ANSWER: 7.919141259916497
```

### bond_price

> What is the full price, per 100 of face value, of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `fixed_income_bond_pricing` {"coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05} → invalid-input
2. `fixed_income_bond_pricing` {"calculation": "price_from_yield", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}

The agent's answer:

```text
The full price is about 96.1027 per 100 of face value. Settlement falls on a coupon date, so accrued interest is zero and the full price equals the flat price. The bond has 20 semiannual payments.

ANSWER: 96.1027094285883
```

### option_price

> Price a European call option with the Black-Scholes-Merton model: spot 100, strike 105, six months to expiry, a 4% risk-free rate, 25% volatility and no dividends.

1. `derivatives_black_scholes_merton` {"calculation": "price", "option_type": "call", "risk_free_rate": 0.04, "spot": 100, "strike": 105, "volatility": 0.25, "years": 0.5}

The agent's answer:

```text
The Black-Scholes-Merton price of the European call is about 5.7799.

The tool also returned these Greeks:
- **Delta:** 0.4703
- **Gamma:** 0.02251
- **Vega:** 28.13
- **Theta:** -8.683
- **Rho:** 20.63

The put-call parity residual was about 7e-15, so the result is internally consistent.

ANSWER: 5.779936227686569
```

### mortgage_payment

> What is the monthly payment on a 250,000 mortgage over 30 years at 6% a year, compounded monthly? Give the payment as a positive amount.

1. `foundations_time_value` {"calculation": "solve", "future_value": 0, "periods": 360, "present_value": 250000, "rate": 0.005}

The agent's answer:

```text
The monthly payment is about 1,498.88. The tool solved for the payment on a 250,000 loan at 0.5% per month (6% ÷ 12) over 360 months. It returned -1,498.876312881881, and the negative sign only means cash paid out, so the positive amount is 1,498.876312881881.

ANSWER: 1498.876312881881
```

### recession_probability_bound

> What probability of a US recession twelve months ahead did the New York Fed's yield-curve model give as of 2025-06-30, with its inputs bound to the data catalog as of that date?

1. `search_models` {"query": "recession probability yield curve"}
2. `run_model` {"as_of": "2025-06-30", "model_id": "macro.recession_probability"}

The agent's answer:

```text
The New York Fed's yield-curve model, with its inputs bound to the data catalog as of 2025-06-30, gave a 12-month-ahead US recession probability of about 30.5%.

- **10-year Treasury yield:** 4.3835%
- **3-month bill yield (bond-equivalent):** 4.421%
- **Spread (10-year minus 3-month):** about −0.04 percentage points, so the curve was slightly inverted.

The tool flagged the yields as revised data. They are the latest values, not the ones published on 2025-06-30.

ANSWER: 0.30517900068803827
```

### unemployment_series

> What was the US unemployment rate for June 2025 in the data catalog, and which source must the figure be credited to?

1. `get_series` {"end": "2025-06-30", "start": "2025-06-01", "target": "us.unemployment.rate"}

The agent's answer:

```text
The catalog gives a US unemployment rate of 0.041 (4.1%) for June 2025. This is the seasonally adjusted rate, BLS series LNS14000000, from the Current Population Survey. The tool returned 0.040999999999999995, which is 0.041 with floating-point rounding.

**Credit line:** "Source: U.S. Bureau of Labor Statistics."

The BLS terms also require this notice: "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov. Data accessed through the BLS Public Data API on 2026-10-26."

ANSWER: 0.041
```

### withheld_sources

> How many of the data providers does this server's policy keep from reaching an AI assistant?

1. `list_sources` {}

The agent's answer:

```text
The server's policy keeps 16 of the 31 listed providers from reaching an AI assistant. I counted the providers whose `llm_permitted` flag is false in the `list_sources` result.

The 16 blocked providers are:
- aqr
- atlanta_fed
- cboe
- cleveland_fed
- coin_metrics
- damodaran
- dbnomics
- fred
- hou_xue_zhang
- imf
- jkp
- ken_french
- open_source_asset_pricing
- philadelphia_fed
- shiller
- yfinance

Damodaran is a special case. Its licence class is hosted-safe, but its `llm_use` is "unclear", so `llm_permitted` is false. I counted it as blocked because the question is about the server's policy. Without it the count would be 15.

The other 15 providers are permitted.

ANSWER: 16
```

### forbidden_series

> Fetch the FRED series GDP (fred:GDP) and tell me its latest value.

1. `get_series` {"target": "fred:GDP"} → llm-use-forbidden

The agent's answer:

```text
I couldn't get the latest value of fred:GDP. The pyeconomics tool refused the request with a 403 error. FRED's terms (https://fred.stlouisfed.org/legal/) don't allow its data to be passed to a language model, and this server only permits sources that do. I didn't try other routes to the number.

ANSWER: unavailable
```
