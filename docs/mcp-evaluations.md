# MCP agent evaluations

The MCP server's tool descriptions are tested by giving a real agent questions it can answer only through the tools (`scripts/mcp_agent_eval.py`, tasks in `scripts/mcp/agent_tasks.py`). The agent runs headless with `pyeconomics mcp` as its only MCP server and no other tool; FRED's and ALFRED's keys are withheld, so the `llm_use` gate is what refuses their data. A task succeeds when the agent calls its tools in order and answers the value the Python API computes from the same data, within the task's tolerance. CI runs the same tasks' scripted calls (`tests/mcp/test_mcp_agent_tasks.py`).

## Latest run

- Date: 2026-11-18
- Agent: Claude Code 2.1.284, headless (claude -p)
- Gateway: the agent's requests passed a de-identifying gateway on the machine, which shows the agent a long number as a placeholder and puts the number back in what the agent writes; the agent was told to repeat a placeholder as written, and nothing else
- Model: `claude-sonnet-5-5`
- Server: pyeconomics 1.0.0rc1.dev1, from the working tree at commit `9e35969`
- Result: 10 of 10 tasks succeeded
- Tool list: 21 tools, 373,599 bytes of names, descriptions and schemas; the agent's first request held 2,364 tokens without the server and 7,808 with it

| Task | Result | Tool calls | Answer | Expected |
|------|--------|------------|--------|----------|
| `discover_convexity` | succeeded | `search_models`, `describe_model`, `run_model` | 75.29958076997512 | 75.29958076997512 |
| `bond_duration` | succeeded | `search_models`, `describe_model`, `run_model` | 7.919141259916497 | 7.919141259916497 |
| `bond_price` | succeeded | `search_models`, `describe_model`, `run_model` | 96.1027094285883 | 96.1027094285883 |
| `option_price` | succeeded | `search_models`, `describe_model`, `run_model` | 5.779936227686569 | 5.779936227686569 |
| `mortgage_payment` | succeeded | `search_models`, `describe_model`, `run_model` | 1498.876312881881 | 1498.876312881881 |
| `recession_probability_bound` | succeeded | `search_models`, `run_model` | 0.30517900068803827 | 0.30517900068803827 |
| `unemployment_series` | succeeded | `get_series` | 0.040999999999999995 | 0.040999999999999995 |
| `unemployment_change` | succeeded | `get_series` | 0.0 | 0 |
| `withheld_sources` | succeeded | `list_sources` | 16.0 | 16 |
| `forbidden_series` | succeeded | `get_series` | unavailable | llm-use-forbidden |

## Each task

### discover_convexity

> Using the pyeconomics tools, find the model for bond convexity and compute the analytical convexity of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity.

1. `search_models` {"query": "bond convexity"}
2. `describe_model` {"model_id": "fixed_income.convexity"}
3. `run_model` {"inputs": {"calculation": "analytical", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}, "model_id": "fixed_income.convexity"}

The agent's answer:

```text
The `fixed_income.convexity` model (Bond convexity, analytical calculation) gives a convexity of 75.29958076997512 years squared for this bond. The full price is 96.1027094285883 per 100 of face value.

I used the default day count (act/act ICMA), 100 face and 100 redemption.

ANSWER: 75.29958076997512
```

### bond_duration

> What is the modified duration of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `search_models` {"query": "bond duration modified"}
2. `describe_model` {"model_id": "fixed_income.duration"}
3. `run_model` {"inputs": {"calculation": "macaulay_modified", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}, "model_id": "fixed_income.duration"}

The agent's answer:

```text
The tool returned the modified duration as a placeholder, not a number. It shows as 7.919141259916497, so I can only see the leading digit, 7. The full value is therefore not visible to me, and I won't guess the remaining digits.

The run used these inputs: settlement 2026-01-15, maturity 2036-01-15, 4.5% coupon paid semiannually, and a 5% yield to maturity. The other outputs were a full price of 96.1027094285883 and a Macaulay duration of 8.117119791414408 years.

ANSWER: 7.919141259916497
```

### bond_price

> What is the full price, per 100 of face value, of a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% coupon paid semiannually and a 5% yield to maturity?

1. `search_models` {"domain": "fixed_income", "query": "bond price yield to maturity coupon"}
2. `describe_model` {"model_id": "fixed_income.bond_pricing"}
3. `run_model` {"inputs": {"calculation": "price_from_yield", "coupon_rate": 0.045, "frequency": "semiannual", "maturity": "2036-01-15", "settlement": "2026-01-15", "yield_to_maturity": 0.05}, "model_id": "fixed_income.bond_pricing"}

The agent's answer:

```text
The full price is 96.1027094285883 per 100 of face value. Settlement falls on a coupon date, so accrued interest is zero and the full and flat prices are the same. The bond is priced below par because the 5% yield is above the 4.5% coupon. It has 20 semiannual payments left, and the next one is on 2026-07-15.

I used the street convention and the ACT/ACT (ICMA) day count, which are the tool's defaults.

ANSWER: 96.1027094285883
```

### option_price

> Price a European call option with the Black-Scholes-Merton model: spot 100, strike 105, six months to expiry, a 4% risk-free rate, 25% volatility and no dividends.

1. `search_models` {"query": "Black-Scholes-Merton option"}
2. `describe_model` {"model_id": "derivatives.black_scholes_merton"}
3. `run_model` {"inputs": {"calculation": "price", "dividend_yield": 0, "option_type": "call", "risk_free_rate": 0.04, "spot": 100, "strike": 105, "volatility": 0.25, "years": 0.5}, "model_id": "derivatives.black_scholes_merton"}

The agent's answer:

```text
The Black-Scholes-Merton model prices the call at about 5.779936227686569. The inputs were spot 100, strike 105, 0.5 years, a 4% risk-free rate, 25% volatility and no dividends.

The put-call parity residual was about 7e-15, so the result is internally consistent.

ANSWER: 5.779936227686569
```

### mortgage_payment

> What is the monthly payment on a 250,000 mortgage over 30 years at 6% a year, compounded monthly? Give the payment as a positive amount.

1. `search_models` {"query": "mortgage payment amortization loan"}
2. `describe_model` {"model_id": "foundations.time_value"}
3. `run_model` {"inputs": {"calculation": "solve", "future_value": 0, "payment": null, "periods": 360, "present_value": 250000, "rate": 0.005}, "model_id": "foundations.time_value"}

The agent's answer:

```text
The monthly payment is about 1,498 a month. I used the time-value tool's `solve` calculation with a 0.5% monthly rate (6% ÷ 12), 360 periods and a present value of 250,000. The tool returns the payment as a negative number because it is money paid out. As a positive amount it is 1498.876312881881.

ANSWER: 1498.876312881881
```

### recession_probability_bound

> What probability of a US recession twelve months ahead did the New York Fed's yield-curve model give as of 2025-06-30, with its inputs bound to the data catalog as of that date?

1. `search_models` {"query": "New York Fed yield curve recession probability"}
2. `run_model` {"as_of": "2025-06-30", "model_id": "macro.recession_probability"}

The agent's answer:

```text
As of 2025-06-30, the New York Fed's yield-curve model gave a 12-month-ahead US recession probability of 0.30517900068803827. I ran `macro.recession_probability` with its inputs bound to the data catalog as of that date.

- **Inputs:** the 10-year Treasury yield was 0.043835, and the 3-month bill yield was 0.04420999999999999 on a bond-equivalent basis. Both came from the US Treasury.
- **Spread:** the 10-year over 3-month spread was -0.0003749999999999934.
- **Caveat:** the tool warned that these yields are the latest revised values, not those published on 2025-06-30. A historical run on them uses information that wasn't yet available on that date.

ANSWER: 0.30517900068803827
```

### unemployment_series

> What was the US unemployment rate for June 2025 in the data catalog, and which source must the figure be credited to?

1. `get_series` {"end": "2025-06-30", "start": "2025-06-01", "target": "us.unemployment.rate"}

The agent's answer:

```text
The catalog's US unemployment rate for June 2025 is 0.040999999999999995. That is the seasonally adjusted rate, series LNS14000000, from the Current Population Survey.

Credit it as "Source: U.S. Bureau of Labor Statistics." BLS also requires this notice: "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov."

ANSWER: 0.040999999999999995
```

### unemployment_change

> By how much did the US unemployment rate change over the twelve months to June 2025, according to the data catalog, as a decimal (0.001 is a tenth of a percentage point)? Read the change from the data, and say which source it is credited to.

1. `get_series` {"end": "2025-06-30", "start": "2024-06-01", "target": "us.unemployment.rate", "transform": "diff(periods=12)"}

The agent's answer:

```text
The change over the twelve months to June 2025 is 0, which is no change in the seasonally adjusted unemployment rate. I read it from the catalog concept `us.unemployment.rate` (BLS series LNS14000000) with a 12-period difference. The value for the June 2025 observation came back as exactly 0.

The source is credited to the U.S. Bureau of Labor Statistics (Current Population Survey, Labor Force Statistics). The attribution reads "Source: U.S. Bureau of Labor Statistics." The BLS notice also says it cannot vouch for data or analyses derived from the data after retrieval.

ANSWER: 0
```

### withheld_sources

> How many of the data providers does this server's policy keep from reaching an AI assistant?

1. `list_sources` {}

The agent's answer:

```text
The server's policy keeps 16 of the 31 providers from reaching an AI assistant. I counted the providers where `llm_permitted` is false in the `list_sources` result:

- **Library-only, use unclear:** AQR, Atlanta Fed, Cboe, Cleveland Fed, Coin Metrics, DBnomics, Hou-Xue-Zhang, JKP, Ken French, Open Source Asset Pricing, Philadelphia Fed, Shiller and Yahoo Finance (13).
- **Library-only, use forbidden:** FRED and the IMF (2).
- **Hosted-safe but not permitted:** Damodaran. Its `llm_use` is unclear, so the policy blocks it even though it is hosted-safe (1).

ANSWER: 16
```

### forbidden_series

> Fetch the FRED series GDP (fred:GDP) and tell me its latest value.

1. `get_series` {"target": "fred:GDP"} → llm-use-forbidden

The agent's answer:

```text
I couldn't get the latest value of fred:GDP. The pyeconomics server refused the request with a 403. FRED's terms don't allow its data to reach a language model, and the server's allowed-only policy enforces that. I didn't try to get around the block.

ANSWER: unavailable
```
