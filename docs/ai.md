# The AI narrative

pyeconomics can ask a language model to explain a result in plain words: what
the model computed, from which inputs, and which assumption or limitation
matters most for reading it. The narrative is optional and off by default. It
runs on your machine with your own key, says what it cost, and sends the
provider nothing but the result's own facts.

A narrative is written by a language model. It can be wrong, and it is not
investment advice: every narrative carries that notice.

## Turning it on

The narrative is part of pyeconomics itself; the `ai` extra installs nothing,
because pyeconomics calls each provider's HTTPS API with the same transport it
uses for data, not with the provider's client library. Turn it on in
`pyeconomics.toml`:

```toml
ai_enabled = true
```

or for one shell with `PYECONOMICS_AI_ENABLED=1`, or from Python with
`configure(ai_enabled=True)`. Until then `narrate` refuses with the
`narrative-disabled` problem (exit code 6):

```python
>>> import pyeconomics
>>> from pyeconomics import ai
>>> result = pyeconomics.run(
...     "derivatives.black_scholes_merton",
...     {"calculation": "price", "spot": 42, "strike": 40, "years": 0.5,
...      "risk_free_rate": 0.1, "volatility": 0.2},
... )
>>> try:
...     ai.narrate(result)
... except ai.NarrativeDisabledError as error:
...     print(error)
the AI narrative is off; turn it on with ai_enabled = true in pyeconomics.toml or PYECONOMICS_AI_ENABLED=1
```

## Keys

Each provider is reached with your own key, read through the same chain as a
data provider's ({doc}`data/keys`): the provider's environment variable, the
`.env` file in your configuration directory, or the OS keyring.

| Provider | Id | Key variable | API |
|----------|----|--------------|-----|
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Messages API |
| Google | `gemini` | `GEMINI_API_KEY` | Gemini API (`generateContent`) |
| OpenAI | `openai` | `OPENAI_API_KEY` | Responses API, with `store: false` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | Chat completions, which reach many makers' models |

Store a key without it reaching your shell history:

```text
pyeconomics keys set openai
```

`pyeconomics keys list` shows where each key would be read from, never its
value. A key is attached to the request by the transport and nowhere else: it
never appears in the prompt, the narrative, a log line, an error or a problem.
A missing key is the `credential-unavailable` problem (exit code 7), naming the
variable.

## The default model and how to change it

The default is OpenAI's `gpt-6.1-sol`, chosen on 2026-10-26 with the project's
model selector for this task (a short plain-language explanation of one
result; knowledge, low complexity): the selector's Balanced choice, at the
model's own default reasoning level, Medium. Naming only a provider picks the
selector's choice that provider serves:

| Provider | Default model |
|----------|---------------|
| `openai` | `gpt-6.1-sol` |
| `anthropic` | `claude-haiku-5-5` |
| `gemini` | `gemini-3.8-flash` |
| `openrouter` | `openai/gpt-6.1-sol` |

```python
>>> ai.DEFAULT_PROVIDER, ai.DEFAULT_MODEL
('openai', 'gpt-6.1-sol')
>>> ai.PROVIDER_MODELS["anthropic"]
'claude-haiku-5-5'
```

Choose another in `pyeconomics.toml`:

```toml
ai_provider = "anthropic"
ai_model = "claude-sonnet-5-5"
```

or with `PYECONOMICS_AI_PROVIDER` and `PYECONOMICS_AI_MODEL`, or per call:

```text
>>> ai.narrate(result, provider="gemini")
>>> ai.narrate(result, provider="openrouter", model="anthropic/claude-haiku-5.5")
```

`ai_model` applies to the provider `ai_provider` names (or to the default
provider); a call that names another provider takes that provider's default
unless it also names a model.

## The cost line

Each narrative reports the tokens the provider counted and what they cost at
list prices, from a price table dated with the day its pages were read:

```text
Cost: $0.0035 (openai gpt-6.1-sol: 782 input and 190 output tokens at list prices read 2026-10-26)
```

Reasoning ("thinking") tokens are billed as output, and the cost counts them.
The cost is an upper bound when the provider caches part of the prompt. A model
missing from the table says `Cost: unknown` rather than guess. Every request
asks for at most 4,096 output tokens, which caps what one narrative of the
default model can cost at about five US cents. The table is read again at
least every 180 days, and a test fails when it is older.

## On the command line

`models run ... --narrate` prints the narrative after the result:

```text
pyeconomics models run derivatives.black_scholes_merton --calculation price --spot 42 --strike 40 --years 0.5 --risk-free-rate 0.1 --volatility 0.2 --format table --narrate
```

With `--format table` the narrative, its notice and its cost line follow the
tables. With `--format json` (the default), an export format or `--out`, they
go to standard error, so standard output stays exactly the canonical result.
The narrative is never written into an export, a bundle or the cache. `--batch`
does not narrate: one narrative per row would be one paid call per row.

## What is sent

One request per narrative, over HTTPS to the provider's one declared host,
holding a fixed instruction and these facts of the result, as plain text:

- the model's title, id, version and summary;
- each input and output with its unit and description (an array shows its first
  twelve values and how many follow);
- the result's warnings;
- the model card's assumptions and limitations.

Nothing else: not the manifest, so no source, series, terms page, retrieval
time or hash, and every piece of text is scrubbed of keys, URLs, host names and
file paths before it is sent. The narrative itself is cleaned of control
characters before it is printed. OpenAI is asked not to store the response;
each provider's own terms govern what it keeps of a request.

## What is refused, and why

`narrate` refuses before any request:

| Refusal | Problem | Exit code |
|---------|---------|-----------|
| Hosted mode (`mode = "hosted"`) | `narrative-not-hosted` (403) | 6 |
| The narrative is off (the default) | `narrative-disabled` (403) | 6 |
| Offline mode | `offline-cache-miss` (503) | 7 |
| The result carries data whose terms keep it from a language model | `llm-use-forbidden` (403) | 6 |
| No key for the provider | `credential-unavailable` (503) | 7 |

Every source declares whether its data may reach a language model
(`llm_use`: `allowed`, `unclear` or `forbidden`; {doc}`data/index`). A result
that carries data classed `forbidden` is never narrated, and data classed
`unclear` only after your opt-in, `allow_unclear_llm_use = true`, which is
read from `pyeconomics.toml` or the environment and never from a call's
arguments. A narrated command-line run binds its data under the same policy,
so a refused source is passed over for the next candidate where there is one.

FRED and ALFRED are classed `forbidden`. FRED's terms bar machine-learning
training; whether its data may reach a language model at inference time, as a
narrative would send it, is a question for counsel, and until it is answered
pyeconomics does not send it.

## Hosted mode waits for Phase 8

The hosted service never writes a narrative. A paid API called on a public
service needs a cost ledger and a cap first, which Phase 8 adds; until then
hosted mode refuses outright, and no REST route and no MCP tool narrates. The
providers are also declared library-only, so the transport would refuse them
in hosted mode even if the narrative did not.
