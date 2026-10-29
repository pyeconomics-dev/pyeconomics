# Model Tier Cost Scale

Tier classification is based solely on **Output price per 1M tokens** from each
provider's published API pricing. The four-tier scale below defines the
boundary used in `model-selector.txt`.

## Tier Boundaries


| Tier      | Output price (per 1M tokens) |
| --------- | ---------------------------- |
| Low       | < $10                        |
| Medium    | $10 – $14.99                 |
| High      | $15 – $24.99                 |
| Very High | ≥ $25                        |


*Boundary is inclusive on the lower end of each tier (e.g. exactly $10 → Medium,
exactly $15 → High, exactly $25 → Very High).*

---

## Full Model Pricing Reference

Prices sourced from Cursor's model pricing page (Cursor Models pool + Other Models pool).
All prices are per 1M tokens. The **Notes** column mirrors the rightmost cell of
each row in Cursor's `models-and-pricing` Markdown source — these are the
hovertext annotations that appear next to the info icon in Cursor's IDE pricing
table and surface material cost / availability / capability constraints.

### Cursor Models Pool


| Model                | Input | Cache Write | Cache Read | Output | Tier   | Notes |
| -------------------- | ----- | ----------- | ---------- | ------ | ------ | ----- |
| Composer 2.5         | $0.50 | –           | $0.20      | $2.50  | Low    | -     |
| Composer 2.5 (Fast)  | $3.00 | –           | $0.50      | $15.00 | High   | -     |
| Grok 4.5             | $2.00 | –           | $0.50      | $6.00  | Low    | Jointly trained by Cursor and SpaceXAI |
| Grok 4.5 (Fast)      | $4.00 | –           | $1.00      | $18.00 | High   | Jointly trained by Cursor and SpaceXAI |
| Grok 4.6             | $2.00 | –           | $0.50      | $6.00  | Low    | Jointly trained by Cursor and SpaceXAI |
| Grok 4.6 (Fast)      | $4.00 | –           | $1.00      | $12.00 | Medium | Jointly trained by Cursor and SpaceXAI |
| Grok 4.7             | $2.00 | –           | $0.50      | $6.00  | Low    | Jointly trained by Cursor and SpaceXAI; Long context (>256k input tokens) is billed at 2x standard rates, up to 500k; Fast mode is available at 2x pricing; Fast mode for long context (>256k) is billed at 3x standard rates |
| Grok 4.7 (Fast)      | $4.00 | –           | $1.00      | $12.00 | Medium | Jointly trained by Cursor and SpaceXAI; Long context (>256k input tokens) is billed at 2x standard rates, up to 500k; Fast mode is available at 2x pricing; Fast mode for long context (>256k) is billed at 3x standard rates |
| Grok 4.7 500k        | $4.00 | –           | $1.00      | $12.00 | Medium | Jointly trained by Cursor and SpaceXAI; Long context (>256k input tokens) is billed at 2x standard rates, up to 500k; Fast mode is available at 2x pricing; Fast mode for long context (>256k) is billed at 3x standard rates |
| Grok 4.7 500k (Fast) | $6.00 | –           | $1.50      | $18.00 | High   | Jointly trained by Cursor and SpaceXAI; Long context (>256k input tokens) is billed at 2x standard rates, up to 500k; Fast mode is available at 2x pricing; Fast mode for long context (>256k) is billed at 3x standard rates |


### API Pool — Anthropic (Claude)


| Model                       | Input  | Cache Write | Cache Read | Output  | Tier      | Notes |
| --------------------------- | ------ | ----------- | ---------- | ------- | --------- | ----- |
| Claude 4 Sonnet             | $3.00  | $3.75       | $0.30      | $15.00  | High      | Hidden by default; Thinking variant counts as 2 requests in legacy pricing |
| Claude 4 Sonnet 1M          | $6.00  | $7.50       | $0.60      | $22.50  | High      | Hidden by default; Thinking variant counts as 2 requests in legacy pricing; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens |
| Claude 4.5 Haiku            | $1.00  | $1.25       | $0.10      | $5.00   | Low       | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x |
| Claude Haiku 5.5            | $0.10  | $0.125      | $0.01      | $0.50   | Low       | Requires Max Mode on legacy request-based plans; Requests above 100k input tokens bill at 5x the standard rates ($0.50/M input, $0.625/M cache write, $0.05/M cache read, $2.50/M output); 90% cheaper than Claude 4.5 Haiku on input and output for requests up to 100k input tokens |
| Claude 4.5 Opus             | $5.00  | $6.25       | $0.50      | $25.00  | Very High | Hidden by default; Requires Max Mode on legacy request-based plans |
| Claude 4.5 Sonnet           | $3.00  | $3.75       | $0.30      | $15.00  | High      | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude 4.6 Opus             | $5.00  | $6.25       | $0.50      | $25.00  | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude 4.6 Sonnet           | $3.00  | $3.75       | $0.30      | $15.00  | High      | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude 4.7 Opus             | $5.00  | $6.25       | $0.50      | $25.00  | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude Fable 5              | $10.00 | $12.50      | $1.00      | $50.00  | Very High | Hidden by default; Requires data retention approval for Enterprise customers, Teams and individual customers with Privacy Mode enabled; Anthropic stores agent input and output data for harm-prevention processes; this data is not used to train or improve Anthropic models or products; Requests that trip a security guardrail are automatically routed to Claude Opus; About 2x the cost of Claude Opus 5; Requires Max Mode on legacy request-based plans |
| Claude Fable 5.1            | $10.00 | $12.50      | $0.25      | $50.00  | Very High | Requires data retention approval for Enterprise customers, Teams and individual customers with Privacy Mode enabled; Anthropic stores agent input and output data for harm-prevention processes; this data is not used to train or improve Anthropic models or products; Requests that trip a security guardrail are automatically routed to Claude Opus; Prompt-cache reads are $0.25/M, 75% below the standard cache-read rate; About 2.5x the cost of Claude Opus 5.5 on input and output; Requires Max Mode on legacy request-based plans |
| Claude Opus 4.7 (fast mode) | $30.00 | $37.50      | $3.00      | $150.00 | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Limited research preview; Up to 1M tokens with extended context at the same per-token rates as shorter context |
| Claude Opus 4.8             | $5.00  | $6.25       | $0.50      | $25.00  | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Fast mode (`claude-opus-4-8-fast`) requires Max Mode on legacy request-based plans; Fast mode is 3x lower per-token pricing than Opus 4.7 fast mode; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude Opus 5               | $5.00  | $6.25       | $0.50      | $25.00  | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Fast mode (`claude-opus-5-fast`) requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude Opus 5.5             | $4.00  | $5.00       | $0.20      | $20.00  | High      | Requires Max Mode on legacy request-based plans; Fast mode (`claude-opus-5-5-fast`) requires Max Mode on legacy request-based plans; 20% cheaper than Claude Opus 5 on input and output; Prompt-cache reads are $0.20/M (0.05x input), down from 0.10x input on Claude Opus 5; Regional and US-only endpoints are priced 10% higher ($4.40/M input, $22/M output); Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |
| Claude Sonnet 5             | $2.00  | $2.50       | $0.20      | $10.00  | Medium    | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge); Uses an updated tokenizer, so the same input can map to more tokens |
| Claude Sonnet 5.5           | $2.00  | $2.50       | $0.10      | $10.00  | Medium    | Requires Max Mode on legacy request-based plans; Same per-token rates as Claude Sonnet 5; US-only endpoints are priced 10% higher ($2.20/M input, $11/M output); Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge) |


### API Pool — Cursor Composer


| Model        | Input | Cache Write | Cache Read | Output | Tier   | Notes |
| ------------ | ----- | ----------- | ---------- | ------ | ------ | ----- |
| Composer 2.5 | $0.50 | –           | $0.20      | $2.50  | Low    | -     |


### API Pool — Google (Gemini)


| Model                      | Input | Cache Write | Cache Read | Output | Tier   | Notes |
| -------------------------- | ----- | ----------- | ---------- | ------ | ------ | ----- |
| Gemini 2.5 Flash           | $0.30 | –           | $0.03      | $2.50  | Low    | Hidden by default |
| Gemini 3 Flash             | $0.50 | –           | $0.05      | $3.00  | Low    | Hidden by default |
| Gemini 3 Pro               | $2.00 | –           | $0.20      | $12.00 | Medium | Hidden by default |
| Gemini 3 Pro Image Preview | $2.00 | –           | $0.20      | $12.00 | Medium | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (~$0.134 per 1K/2K image, ~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| Gemini 3.1 Flash-Lite      | $0.25 | –           | –          | $1.50  | Low    | Provider-direct Google API per-token pricing (not via the Cursor pool) |
| Gemini 3.1 Pro             | $2.00 | –           | $0.20      | $12.00 | Medium | -                 |
| Gemini 3.5 Flash           | $1.50 | –           | $0.15      | $9.00  | Low    | Hidden by default |
| Gemini 3.5 Flash-Lite      | $0.30 | –           | –          | $2.50  | Low    | Provider-direct Google API per-token pricing (not via the Cursor pool) |
| Gemini 3.6 Flash           | $1.50 | –           | $0.15      | $7.50  | Low    | Hidden by default |
| Gemini 3.7 Flash           | $0.75 | –           | $0.075     | $3.50  | Low    | Hidden by default |
| Gemini 3.8 Flash           | $0.75 | –           | $0.075     | $3.50  | Low    | -                 |
| Gemini 4 Argon             | $2.00 | –           | $0.10      | $10.00 | Medium | -                 |


### API Pool — Meta


| Model          | Input | Cache Write | Cache Read | Output | Tier | Notes |
| -------------- | ----- | ----------- | ---------- | ------ | ---- | ----- |
| Muse Spark 1.3 | $1.25 | –           | $0.15      | $4.25  | Low  | Requires Max Mode on legacy request-based plans; Up to 1M tokens in Max Mode at the same per-token rates (no long-context surcharge); Cached input is billed at $0.15 per million tokens with no separate cache-write charge |
| Muse Wonder    | $4.00 | –           | $0.20      | $20.00 | High | Up to 1M tokens in Max Mode at the same per-token rates (no long-context surcharge); Cached input is billed at $0.20 per million tokens with no separate cache-write charge |


### API Pool — OpenAI (GPT)


| Model              | Input | Cache Write | Cache Read | Output | Tier      | Notes |
| ------------------ | ----- | ----------- | ---------- | ------ | --------- | ----- |
| GPT-5              | $1.25 | –           | $0.125     | $10.00 | Medium    | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high |
| GPT-5 Fast         | $2.50 | –           | $0.25      | $20.00 | High      | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast |
| GPT-5 Mini         | $0.25 | –           | $0.025     | $2.00  | Low       | Hidden by default |
| GPT-5-Codex        | $1.25 | –           | $0.125     | $10.00 | Medium    | Hidden by default; Agentic and reasoning capabilities |
| GPT-5.1 Codex      | $1.25 | –           | $0.125     | $10.00 | Medium    | Hidden by default; Agentic and reasoning capabilities |
| GPT-5.1 Codex Max  | $1.25 | –           | $0.125     | $10.00 | Medium    | Hidden by default |
| GPT-5.1 Codex Mini | $0.25 | –           | $0.025     | $2.00  | Low       | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex |
| GPT-5.2            | $1.75 | –           | $0.175     | $14.00 | Medium    | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high |
| GPT-5.2 Codex      | $1.75 | –           | $0.175     | $14.00 | Medium    | Hidden by default; Agentic and reasoning capabilities |
| GPT-5.3 Codex      | $1.75 | –           | $0.175     | $14.00 | Medium    | Hidden by default; Requires Max Mode on legacy request-based plans; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high |
| GPT-5.4            | $2.50 | –           | $0.25      | $15.00 | High      | Hidden by default; Requires Max Mode on legacy request-based plans; Agentic and reasoning capabilities; 90% discount on cached input tokens; Fast mode is 15% faster with 2x pricing; Long context supports up to 1M tokens with 2x input pricing |
| GPT-5.4 Mini       | $0.75 | –           | $0.075     | $4.50  | Low       | Hidden by default; Smaller, faster variant of GPT-5.4; 90% discount on cached input tokens |
| GPT-5.4 Nano       | $0.20 | –           | $0.02      | $1.25  | Low       | Hidden by default; Smallest GPT-5.4 variant, optimized for cost; 90% discount on cached input tokens |
| GPT-5.5            | $5.00 | –           | $0.50      | $30.00 | Very High | Hidden by default; Requires Max Mode on legacy request-based plans; Agentic and reasoning capabilities; More token-efficient than GPT-5.4 on comparable tasks; Improved persistence on long-running tasks; Fast mode is available at higher rates; Long context supports up to 1M tokens with 2x input pricing |
| GPT-5.6 Luna       | $0.20 | $0.25       | $0.02      | $1.20  | Low       | Requires Max Mode on legacy request-based plans; Smallest GPT-5.6 variant, optimized for cost and speed; Agentic and reasoning capabilities; Fast mode is available at 2x pricing; Long context supports up to 1M tokens with 2x input pricing; Fast mode is available for long context (>272k) at 2x Fast input pricing; Cache writes are billed at 1.25x the uncached input rate |
| GPT-5.6 Sol        | $4.00 | $5.00       | $0.40      | $20.00 | High      | Requires Max Mode on legacy request-based plans; Agentic and reasoning capabilities; Fast mode is available at 2x pricing; Long context supports up to 1M tokens with 2x input pricing; Fast mode is available for long context (>272k) at 2x Fast input pricing; Cache writes are billed at 1.25x the uncached input rate; Promotional pricing through November 21, 2026 |
| GPT-5.6 Terra      | $2.00 | $2.50       | $0.20      | $12.00 | Medium    | Requires Max Mode on legacy request-based plans; Mid-tier GPT-5.6 variant between Sol and Luna; Agentic and reasoning capabilities; Fast mode is available at 2x pricing; Long context supports up to 1M tokens with 2x input pricing; Fast mode is available for long context (>272k) at 2x Fast input pricing; Cache writes are billed at 1.25x the uncached input rate |
| GPT-6 Astra        | $10.00 | –          | –          | $50.00 | Very High | Provider-direct OpenAI API per-token pricing (not via the Cursor pool) |
| GPT-6 Luna         | $0.10 | –           | –          | $0.50  | Low       | Provider-direct OpenAI API per-token pricing (not via the Cursor pool) |
| GPT-6 Sol          | $2.00 | –           | –          | $10.00 | Medium    | Provider-direct OpenAI API per-token pricing (not via the Cursor pool) |
| GPT-6.1 Sol        | $2.00 | –           | –          | $10.00 | Medium    | Provider-direct OpenAI API per-token pricing (not via the Cursor pool) |


### API Pool — Moonshot


| Model          | Input | Cache Write | Cache Read | Output | Tier | Notes |
| -------------- | ----- | ----------- | ---------- | ------ | ---- | ----- |
| Kimi K2.7 Code | $0.95 | –           | $0.19      | $4.00  | Low  | Hidden by default |
| Kimi K3        | $3.00 | –           | $0.30      | $15.00 | High | Hidden by default; Requires Max Mode on legacy request-based plans; Up to 1M tokens with extended context at the same per-token rates (no long-context surcharge); No separate cache-write fee |


### API Pool — Z.ai


| Model   | Input | Cache Write | Cache Read | Output | Tier | Notes |
| ------- | ----- | ----------- | ---------- | ------ | ---- | ----- |
| GLM 5.2 | $1.40 | –           | $0.26      | $4.40  | Low  | Hidden by default |
| GLM 5.3 | $1.40 | –           | $0.26      | $4.40  | Low  | Hidden by default; Same per-token rates as GLM 5.2 |
| GLM 5.3 Flash | $0.15 | –     | $0.029     | $0.50  | Low  | Hidden by default |


---

<!-- subscription-tiers-reviewed: 2026-09-30 -->

## Subscription Tiers and Access Methods

The per-token tables above are one dimension of cost. Many of the same
models are reachable through flat-monthly subscription plans whose
marginal cost per call is effectively $0 until the subscription's usage
budget or token pool is exhausted. The selector's `<access-selection>`
step uses this table to rank platforms; the user-specific subscription
state lives in [`docs/user-context.md`](user-context.md).

This table is a DERIVED VIEW of each provider's official pricing page,
rebuilt weekly by [`update/update_models.py`](../update/update_models.py)
using Anthropic's `web_search` server-side tool per the rules in
[`update/prompt.md`](../update/prompt.md) § "Subscription tiers". Each
run discovers the canonical pricing page for every provider enumerated
in `<access-methods>` of [`docs/model-selector.txt`](model-selector.txt),
enumerates the consumer tiers shown, and writes the resulting row set
into this table. Manual edits to the table body will be overwritten on
the next run. To change which providers are in scope, edit
`<access-methods>` (which is editorial and remains protected by the
existing model-lifecycle rules); the next cron run picks up the new
provider automatically.

The **`Annual`** column (the full yearly total in USD) is rebuilt by the
same `web_search` pass as the monthly price, with two safeguards (see
[`update/prompt.md`](../update/prompt.md) § "Annual column"): a **sanity
guard** accepts a captured annual `A` for a tier with monthly `M` only
when `8 × M ≤ A ≤ 12 × M` (a real annual discount, never a misparse), and
**preserve-on-miss** keeps the existing cell verbatim when no annual is
found or the guard trips — so a transient fetch miss never downgrades a
known-good price. A tier with no annual plan carries `—` (parsed as a
null `annual_usd`, which suppresses the annual price + savings in the UI
without breaking the tier). To pin or correct an annual price by hand,
edit the cell directly; the next rebuild keeps it unless it re-derives a
guarded value that differs (and then logs the change).

`tests/test_subscription_freshness.py` watches the
`<!-- subscription-tiers-reviewed: YYYY-MM-DD -->` marker above. The
cron bumps the marker to today's date only when every in-scope
provider's rebuild completed without tripping a sanity guard; a stale
marker (>180 days) therefore means the cron has been running but
subscription rebuild has been persistently failing — most likely a
provider has redesigned its pricing page in a way the AI can no longer
parse cleanly. When that happens, eyeball the failing provider's page
and adjust the rebuild rules in [`update/prompt.md`](../update/prompt.md).


| Subscription           | Monthly | Annual  | Provider  | Access methods unlocked | Coverage                                                                                                  |
| ---------------------- | ------- | ------- | --------- | ----------------------- | --------------------------------------------------------------------------------------------------------- |
| Claude Pro             | $20     | $200    | Anthropic | claude-code, claude-web | Opus 5, Sonnet 5, Fable 5.1, and Claude 4.5 Haiku on web / desktop and inside Claude Code (CLI + IDE), with roughly 5x the usage of the Free tier. |
| claude.ai Max ($100)   | $100    | —       | Anthropic | claude-code, claude-web | Same model coverage as Pro at roughly 5x the Pro usage budget; priority access during peak traffic.       |
| claude.ai Max ($200)   | $200    | —       | Anthropic | claude-code, claude-web | Same model coverage as Pro at roughly 20x the Pro usage budget; highest consumer-tier Claude budget.      |
| ChatGPT Go             | $8      | —       | OpenAI    | chatgpt-app, codex-cli  | Budget tier with GPT-5.3 Instant unlimited and GPT-5.3 quota, more uploads and image generation than Free; ads still shown; lacks advanced reasoning models, Sora, Codex full access, Agent Mode, and Deep Research. |
| ChatGPT Plus           | $20     | —       | OpenAI    | chatgpt-app, codex-cli  | GPT-5.6 Sol default model with full feature suite — Deep Research, Sora video, Codex, Agent Mode; GPT-5.6 Terra and GPT-5.6 Luna also available. |
| ChatGPT Pro ($100)     | $100    | —       | OpenAI    | chatgpt-app, codex-cli  | Same model suite as Pro $200 (GPT-5.6 Sol, GPT-5.5, o1 Pro mode) at 5x Plus usage limits; Codex access included with promotional 10x multiplier through May 31, 2026. |
| ChatGPT Pro ($200)     | $200    | —       | OpenAI    | chatgpt-app, codex-cli  | Same core Pro features as Pro $100 (Pro models, Codex, deep research, image creation, memory, file uploads) with more usage than Pro $100; new subscriptions are open again, and new subscriptions not eligible for grandfathering get a lower usage allowance than the previous Pro 200. |
| ChatGPT Pro ($500)     | $500    | —       | OpenAI    | chatgpt-app, codex-cli  | Highest-usage ChatGPT Pro tier (more included usage than Pro $100 and Pro $200); includes Astra Ultrafast plus the core Pro features (Pro models, Codex, deep research, image creation, memory, file uploads). |
| Google AI Plus         | $4.99   | —       | Google    | gemini-app              | Entry-paid Google AI tier with 2x higher usage limits than Free in the Gemini app, access to Gemini 3.1 Pro / Nano Banana Pro / Daily Brief / Gemini Omni video generation, 200 Google Flow Credits, and 400 GB of cloud storage (price cut from $7.99 to $4.99 on 2026-06-08; storage doubled from 200 GB to 400 GB). |
| Google AI Pro          | $19.99  | $199.99 | Google    | gemini-app, antigravity | Gemini 3.1 Pro and supporting multimodal features in the Gemini app, Antigravity quota refreshed every five hours up to a weekly limit, plus Deep Research, Nano Banana Pro, Veo 3.1 access, 1,000 monthly AI credits, and 5 TB of Google One storage; includes YouTube Premium Lite; 50% off the first year for new subscribers. |
| Google AI Ultra ($100) | $99.99  | —       | Google    | gemini-app, antigravity | Developer-focused Ultra tier (May 2026): 5x Pro usage limits in Gemini app and Google Antigravity, Gemini 3.5 Flash integration, priority access to Antigravity, 20 TB cloud storage, and YouTube Premium individual plan. |
| Google AI Ultra ($200) | $199.99 | —       | Google    | gemini-app, antigravity | Highest access to Gemini 3.1 Pro, Deep Think, Project Genie, Veo 3.1 with 25,000 monthly AI credits, $100/month Google Cloud credits, and 30 TB Google One storage (price reduced from $249.99 to $199.99 at Google I/O 2026). |
| Cursor Pro             | $20     | $192    | Cursor    | cursor                  | Two monthly usage pools — Cursor Models (generous included usage for Grok 4.7, Grok 4.6, Grok 4.5, Composer 2.5) and Other Models (third-party models at API price); on-demand overage billed at API rates. |
| Cursor Pro+            | $60     | $576    | Cursor    | cursor                  | Same model coverage as Pro at roughly 3x the OpenAI / Claude / Gemini usage budget.                       |
| Cursor Ultra           | $200    | $1920   | Cursor    | cursor                  | Same model coverage as Pro at roughly 20x the OpenAI / Claude / Gemini usage budget; priority access to new features. |


The "Access methods unlocked" column references method ids enumerated in
the `<access-methods>` block of
[`docs/model-selector.txt`](model-selector.txt). The dollar values are
list prices at time of writing; verify against each provider's billing
page before publishing.

Subscriptions whose surface is web-chat-only (no CLI / IDE / API path
beyond a chat box) are intentionally omitted — only subscriptions that
unlock at least one access method enumerated in `<access-methods>`
appear here.

---

## Existing model-selector.txt Classification Audit


| Model (file id)  | Output  | Correct Tier | Current Tier | Status |
| ---------------- | ------- | ------------ | ------------ | ------ |
| opus-4.7         | $25.00  | Very High    | Very High    | ✓      |
| opus-4.8         | $25.00  | Very High    | Very High    | ✓      |
| claude-opus-5    | $25.00  | Very High    | Very High    | ✓      |
| claude-opus-5-5  | $20.00  | High         | High         | ✓      |
| claude-fable-5   | $50.00  | Very High    | Very High    | ✓      |
| claude-fable-5.1 | $50.00  | Very High    | Very High    | ✓      |
| gpt-5.5          | $30.00  | Very High    | Very High    | ✓      |
| gpt-6-astra      | $50.00  | Very High    | Very High    | ✓      |
| gpt-5.6-sol      | $20.00  | High         | High         | ✓      |
| sonnet-4.6       | $15.00  | High         | High         | ✓      |
| claude-sonnet-5  | $10.00  | Medium       | Medium       | ✓      |
| claude-sonnet-5-5 | $10.00 | Medium       | Medium       | ✓      |
| gpt-5.4          | $15.00  | High         | High         | ✓      |
| gpt-5.6-terra    | $12.00  | Medium       | Medium       | ✓      |
| gpt-6-sol        | $10.00  | Medium       | Medium       | ✓      |
| gpt-6.1-sol      | $10.00  | Medium       | Medium       | ✓      |
| gpt-5.3-codex    | $14.00  | Medium       | Medium       | ✓      |
| gpt-5.2          | $14.00  | Medium       | Medium       | ✓      |
| gpt-5.2-codex    | $14.00  | Medium       | Medium       | ✓      |
| kimi-k3          | $15.00  | High         | High         | ✓      |
| gemini-3.1-pro   | $12.00  | Medium       | Medium       | ✓      |
| gemini-4-argon   | $10.00  | Medium       | Medium       | ✓      |
| gemini-3-pro     | $12.00  | Medium       | Medium       | ✓      |
| gpt-5            | $10.00  | Medium       | Medium       | ✓      |
| gpt-5.1-codex    | $10.00  | Medium       | Medium       | ✓      |
| gpt-5.1-codex-max | $10.00 | Medium       | Medium       | ✓      |
| gemini-3.5-flash | $9.00   | Low          | Low          | ✓      |
| gemini-3.6-flash | $7.50   | Low          | Low          | ✓      |
| gemini-3.7-flash | $3.50   | Low          | Low          | ✓      |
| gemini-3.8-flash | $3.50   | Low          | Low          | ✓      |
| gemini-3.5-flash-lite | $2.50 | Low        | Low          | ✓      |
| gemini-3.1-flash-lite | $1.50 | Low        | Low          | ✓      |
| mistral-medium-3.5 | $7.50 | Low          | Low          | ✓      |
| grok-4.5         | $6.00   | Low          | Low          | ✓      |
| grok-4.6         | $6.00   | Low          | Low          | ✓      |
| grok-4.7         | $6.00   | Low          | Low          | ✓      |
| gpt-5.6-luna     | $1.20   | Low          | Low          | ✓      |
| gpt-6-luna       | $0.50   | Low          | Low          | ✓      |
| claude-4.5-haiku | $5.00   | Low          | Low          | ✓      |
| claude-haiku-5-5 | $0.50   | Low          | Low          | ✓      |
| muse-spark-1.3   | $4.25   | Low          | Low          | ✓      |
| muse-wonder      | $20.00  | High         | High         | ✓      |
| gpt-5.4-mini     | $4.50   | Low          | Low          | ✓      |
| glm-5.2          | $4.40   | Low          | Low          | ✓      |
| glm-5.3          | $4.40   | Low          | Low          | ✓      |
| glm-5.3-flash    | $0.50   | Low          | Low          | ✓      |
| kimi-k2.7-code   | $4.00   | Low          | Low          | ✓      |
| gemini-3-flash   | $3.00   | Low          | Low          | ✓      |
| composer-2.5     | $2.50   | Low          | Low          | ✓      |
| gemini-2.5-flash | $2.50   | Low          | Low          | ✓      |
| grok-4.3         | $2.50   | Low          | Low          | ✓      |
| glm-4.6          | $2.20   | Low          | Low          | ✓      |
| gpt-5-mini       | $2.00   | Low          | Low          | ✓      |
| gpt-5.1-codex-mini | $2.00 | Low          | Low          | ✓      |
| mistral-large-3  | $1.50   | Low          | Low          | ✓      |
| gpt-5.4-nano     | $1.25   | Low          | Low          | ✓      |
| glm-4.5-air      | $1.10   | Low          | Low          | ✓      |
| codestral        | $0.90   | Low          | Low          | ✓      |
| deepseek-v4-pro  | $1.98   | Low          | Low          | ✓      |
| gpt-oss-120b     | $0.60   | Low          | Low          | ✓      |
| mistral-small-4  | $0.30   | Low          | Low          | ✓      |
| gpt-oss-20b      | $0.30   | Low          | Low          | ✓      |
| deepseek-flash   | $0.60   | Low          | Low          | ✓      |


Routing meta-models (Cursor's "Auto" / "Premium" modes; analogous
routers from other providers) are intentionally NOT enumerated in
`docs/model-selector.txt` `<model-options>`. The catalog tracks fixed-
engine models only — a routing model's benchmarks, jurisdiction, and
cost are by construction unknowable in advance, which conflicts with
the selector's per-model tier ratings and the jurisdiction filter
(see `<jurisdiction-context>` in `docs/model-selector.txt` for the
rationale). The "Cursor Models Pool" table at the top of this
document continues to document Cursor's first-party model pricing for
reference (Grok 4.5, Grok 4.6, Grok 4.7, Composer 2.5, plus their Fast
variants), but the `auto` and `premium` model ids no longer appear as
recommendable engines.

## Recently Added / Updated Models


| Model id           | Output | Tier | Change                                                                                                                     |
| ------------------ | ------ | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| Claude Haiku 5.5   | $0.50  | Low  | New 2026-10-19 (released 2026-10-07). Anthropic's Haiku 4.5 successor at $0.10/$0.50 for prompts up to 100k tokens, 5x above that; on Anthropic's own pricing page and Cursor's. Provider-direct (Federation rule: prices owned by `catalog-anthropic.json`). |
| Gemini 4 Argon     | $10.00 | Medium | New 2026-10-19 (released 2026-10-13). Google's flagship reasoning model at $2/$10 (Google raises it to $4/$20 on 2026-12-01); on Google's own pricing page and Cursor's. Provider-direct (Federation rule: prices owned by `catalog-google.json`). |
| Muse Wonder        | $20.00 | High | New 2026-10-19 on Cursor's pricing page (released 2026-10-12). Meta's Muse Wonder at $4/$20, up to 1M tokens in Max Mode at the same rates. |
| Gemini 3.5 Flash-Lite | $2.50 | Low | New 2026-10-07 via the provider-discovery lane. Google's own Gemini API pricing page now prices gemini-3.5-flash-lite at $0.30/$2.50 (previously listed there without a price), and it is not on Cursor's pricing page. Provider-direct (Federation rule: prices owned by the Google provider snapshot). The selector pass adds it to `<model-options>` in the Low bucket |
| Gemini 3.1 Flash-Lite | $1.50 | Low | New 2026-10-07 via the provider-discovery lane. Google's own Gemini API pricing page now prices gemini-3.1-flash-lite at $0.25/$1.50 (previously listed there without a price), and it is not on Cursor's pricing page. Provider-direct (Federation rule: prices owned by the Google provider snapshot). The selector pass adds it to `<model-options>` in the Low bucket |
| GPT-6.1 Sol        | $10.00 | Medium | New 2026-10-01 via the provider-discovery lane. OpenAI's own pricing page lists gpt-6.1-sol at $2/$10, and it is not on Cursor's pricing page. Provider-direct (Federation rule: prices owned by `catalog-openai.json`). The selector pass adds it to `<model-options>` in the Medium bucket |
| Claude Sonnet 5.5  | $10.00 | Medium | New 2026-09-29 on Cursor's pricing page — Anthropic's Sonnet 5 successor at the same $2/$10 rates (US-only endpoints 10% higher at $2.20/$11); visible by default. Selector pass adds it to `<model-options>`; Anthropic is provider-direct, so `catalog-anthropic.json` must carry it for the G4 gate |
| Claude Sonnet 5    | $10.00 | Medium | Notes refreshed 2026-09-29 — Cursor flipped Sonnet 5 to "Hidden by default" after the Sonnet 5.5 launch (pricing unchanged) |
| GLM 5.3            | $4.40  | Low  | New 2026-09-29 on Cursor's pricing page — z.ai's GLM 5.3 at the same $1.40/$4.40 rates as GLM 5.2 (Hidden by default) |
| GLM 5.3 Flash      | $0.50  | Low  | New 2026-09-29 on Cursor's pricing page — z.ai's GLM 5.3 Flash at $0.15/$0.50 (Hidden by default) |
| GPT-6 Astra        | $50.00 | Very High | New 2026-09-25 via the provider-discovery lane — OpenAI's own pricing page lists gpt-6-astra at $10/$50; not on Cursor's pricing page. Provider-direct (Federation rule: prices owned by `catalog-openai.json`) |
| GPT-6 Sol          | $10.00 | Medium | New 2026-09-25 via the provider-discovery lane — OpenAI's own pricing page lists gpt-6-sol at $2/$10; not on Cursor's pricing page. Provider-direct |
| GPT-6 Luna         | $0.50  | Low  | New 2026-09-25 via the provider-discovery lane — OpenAI's own pricing page lists gpt-6-luna at $0.10/$0.50; not on Cursor's pricing page. Provider-direct |
| Claude Opus 5.5    | $20.00 | High | New 2026-09-23 on Cursor's pricing page — Anthropic's Opus 5 successor at $4/$20 (20% cheaper than Opus 5 on input and output); prompt-cache reads $0.20/M (0.05x input, down from 0.10x on Opus 5); regional and US-only endpoints priced 10% higher ($4.40/$22); visible by default (not Hidden). Selector-pass will add to `<model-options>` per the Anthropic Federation rule (input/output owned by `catalog-anthropic.json`) |
| Claude Fable 5.1   | $50.00 | Very High | Notes refreshed 2026-09-23 — Cursor updated the Fable 5.1 hovertext from "About 2x the cost of Claude Opus 5" to "About 2.5x the cost of Claude Opus 5.5 on input and output" following the Opus 5.5 launch (Fable 5.1 pricing itself unchanged at $10/$50) |
| Grok 4.7           | $6.00  | Low  | New 2026-09-22 in the Cursor Models pool — xAI/SpaceXAI released Grok 4.7 on 2026-09-21 as a same-price, same-speed upgrade over Grok 4.6 at $2/$6 (2.1T parameters, 500K context, xhigh reasoning). Fast variant $4/$12 (Medium tier); 500k long-context variant $4/$12 (Medium tier); 500k Fast variant $6/$18 (High tier). Not yet added to `<model-options>` (selector-pass will handle) |
| Grok 4.7 (Fast)    | $12.00 | Medium | New 2026-09-22 Cursor first-party Fast variant of Grok 4.7 (2x standard rates for higher output speed)                     |
| Grok 4.7 500k      | $12.00 | Medium | New 2026-09-22 Cursor first-party long-context (>256k) variant of Grok 4.7 (2x standard rates apply to all tokens)         |
| Grok 4.7 500k (Fast) | $18.00 | High | New 2026-09-22 Cursor first-party long-context Fast variant of Grok 4.7 (3x standard rates for combined fast + long context) |
| deepseek-flash     | $0.60  | Low  | New 2026-09-21 (editorial, closes #583 / #606) — DeepSeek-V4.1-Flash under the API name `deepseek-flash`, the provider-direct successor to `deepseek-v4-flash`: $0.15/$0.60 off-peak ($0.30/$1.20 peak), 1M context, native image input (V4-Flash-Vision-Exp folded in), AA Intelligence Index 39.5 (v4.3). Tier ratings inherited from V4-Flash except multimodal D→C; MIT weights on Hugging Face |
| deepseek-v4-flash  | —      | —    | RETIRED 2026-09-21 from `<model-options>` — DeepSeek retired DeepSeek-V4-Flash-0731 (and -Vision-Exp) from its pricing page 2026-09-17; the legacy API names are still accepted but served by DeepSeek-V4.1-Flash at the Flash price, so the element is replaced by `deepseek-flash` rather than kept |
| deepseek-v4-pro    | $1.98  | Low  | Price basis made explicit 2026-09-21 — DeepSeek's pricing page splits every rate into OFF-PEAK / PEAK (peak = 2×, 01:00–04:00 and 06:00–10:00 UTC Mon–Fri only); the catalog lists the OFF-PEAK rate for both DeepSeek models (~79% of the week, all US/EU working hours) and the snapshot records `price_basis` + the peak figures. Aggregators such as OpenRouter list the PEAK rate ($1.32/$3.96) |
| Composer 1         | —      | —    | REMOVED 2026-09-17 from cost scale — Cursor's pricing page no longer lists Composer 1 in any pool (Composer 2.5 supersedes it in the Cursor Models pool) |
| Muse Spark 1.3     | $4.25  | Low  | New 2026-09-10 on Cursor's pricing page — Meta's Muse Spark 1.3 at $1.25/$4.25 (first Meta-provider entry in the cost scale); requires Max Mode on legacy request-based plans with 1M context available in Max Mode |
| GPT-5.1 Codex Mini | $2.00  | Low  | New 2026-09-10 on Cursor's pricing page — smaller/cheaper GPT-5.1 Codex variant at $0.25/$2.00 (4x rate limits vs GPT-5.1 Codex, Hidden by default) |
| Grok 4.6           | $6.00  | Low       | New 2026-09-04 on Cursor's pricing page — Cursor first-party model at $2/$6 (mirrors Grok 4.5 pricing), jointly trained by Cursor and SpaceXAI. Fast variant $4/$12 (Medium tier). Not yet added to `<model-options>` (selector-pass will handle) |
| Claude Fable 5.1   | $50.00 | Very High | New 2026-09-04 on Cursor's pricing page — Anthropic's Fable 5 successor at $10/$50 (same tier pricing as Fable 5); cache-read reduced 75% to $0.25/M vs Fable 5's $1/M. Not yet added to `<model-options>` (selector-pass will handle) |
| Gemini 3.7 Flash   | $3.50  | Low       | New 2026-09-04 on Cursor's pricing page — Google's Gemini 3.7 Flash at $0.75/$3.50 (Hidden by default). Not yet added to `<model-options>` |
| Gemini 3.8 Flash   | $3.50  | Low       | New 2026-09-04 on Cursor's pricing page — Google's Gemini 3.8 Flash at $0.75/$3.50 (visible, not Hidden by default); supersedes Gemini 3.7 in same series at equal output price. Not yet added to `<model-options>` |
| gpt-5.6-sol        | $20.00 | High      | Price DROPPED 2026-09-04 on Cursor's pricing page from $5/$30 to $4/$20 (promotional pricing through November 21, 2026); tier moves Very High → High as a result. Notes updated to add long-context clauses and promotional-pricing disclosure |
| gpt-5.6-terra      | $12.00 | Medium    | Price DROPPED 2026-09-04 on Cursor's pricing page from $2.50/$15 to $2/$12; tier moves High → Medium. Notes updated to add "Requires Max Mode on legacy request-based plans" prefix and long-context clauses |
| gpt-5.6-luna       | $1.20  | Low       | Price DROPPED 2026-09-04 on Cursor's pricing page from $1/$6 to $0.20/$1.20 (5x cheaper output); Notes updated to add "Requires Max Mode on legacy request-based plans" prefix and long-context clauses; still Low tier |
| Claude Sonnet 5    | $10.00 | Medium    | Corrected 2026-09-12 from $3/$15 (High) to $2/$10 (Medium): Anthropic's own pricing page, mirrored in `catalog-anthropic.json`, lists $2/$10 as the standard rate, so the launch-promotion clause is retired from the Notes column; the selector was corrected in roadmodel 0.2.31 and the cost scale now matches it |
| Grok 4.6 (Fast)    | $12.00 | Medium    | New 2026-09-04 Cursor first-party Fast variant of Grok 4.6                                                                 |
| Grok 4.5 (Fast)    | $18.00 | High      | New 2026-09-04 Cursor first-party Fast variant of Grok 4.5                                                                 |
| Composer 2.5 (Fast) | $15.00 | High   | New 2026-09-04 Cursor first-party Fast variant of Composer 2.5                                                             |
| Auto (pool rate)   | —      | —         | REMOVED 2026-09-04 — Cursor's pricing page no longer lists a separate "Auto" billed line item; the Cursor Models pool now enumerates the covered first-party models (Grok 4.6, Grok 4.5, Composer 2.5) directly, and Auto routing bills at the routed model's list price |
| Claude Opus 5      | $25.00 | Very High | New 2026-08-05 on Cursor's pricing page — Anthropic's Opus 5 successor at $5/$25 (same tier pricing as Opus 4.7/4.8); requires Max Mode on legacy request-based plans; native 1M context via extended-context toggle |
| Gemini 3.6 Flash   | $7.50  | Low       | New 2026-08-05 on Cursor's pricing page — Google's Gemini 3.6 Flash at $1.50/$7.50. Reportedly released 2026-07-21. Now Hidden by default (was visible on initial listing) |
| Kimi K3            | $15.00 | High      | New 2026-08-05 on Cursor's pricing page — Moonshot's Kimi K3 at $3/$15 with 1M extended-context support at flat per-token rates |
| claude-sonnet-5    | $10.00 | Medium    | Price CORRECTED 2026-09-05 to $2/$10 from Anthropic's own pricing page, which is authoritative for Anthropic models per the Federation rule; tier High → Medium. The catalog had carried the aggregator mirror's $3/$15 because update/extract_anthropic_catalog.py had been failing silently since the page restyled its "Base input tokens" header, and claude-sonnet-5 was never in that extractor's name map — so G4 had nothing to reconcile. The July note called $2/$10 a promotion through 2026-08-31; Anthropic lists it as the standard rate today |
| gpt-5.6-sol        | $30.00 | Very High | Initial listing 2026-07-15 on Cursor's pricing page — OpenAI's GPT-5.6 Sol flagship at $5/$30 (mirrors GPT-5.5 pricing); requires Max Mode on request-based plans |
| gpt-5.6-terra      | $15.00 | High      | Initial listing 2026-07-15 on Cursor's pricing page — GPT-5.6 Terra mid-tier variant at $2.50/$15                           |
| gpt-5.6-luna       | $6.00  | Low       | Initial listing 2026-07-15 on Cursor's pricing page — smallest GPT-5.6 variant at $1/$6, optimized for cost and speed       |
| gpt-5.2-codex      | $14.00 | Medium    | New 2026-07-15 on Cursor's pricing page — Codex variant of GPT-5.2 at $1.75/$14 (same pricing as GPT-5.2, agentic + reasoning) |
| gpt-5.1-codex-max  | $10.00 | Medium   | New 2026-07-15 on Cursor's pricing page — GPT-5.1 Codex Max at $1.25/$10                                                    |
| kimi-k2.7-code     | $4.00  | Low       | New 2026-07-15 on Cursor's pricing page — Moonshot's Kimi K2.7 Code at $0.95/$4 (supersedes Kimi K2.5 row; K2.5 no longer on Cursor's pricing page) |
| grok-4.5           | $6.00  | Low       | New 2026-07-15 on Cursor's pricing page — jointly trained by Cursor and SpaceXAI, first-party model; not yet available in the EU |
| glm-5.2            | $4.40  | Low       | New 2026-06-27 in cost-scale — z.ai's GLM 5.2 now visible on Cursor's pricing page (provider header "Z.ai"); already present in `<model-options>` via provider-direct `zai-api` method, prices preserved per the Federation rule (provider-direct catalog owns input/output) |
| grok-4.3           | $2.50  | Low       | LEFT Cursor's pricing page 2026-07-15 (Grok 4.5 is Cursor's first-party replacement) but RETAINED in `<model-options>` as provider-direct via the `xai-api` method — still on xAI's own API at $1.25/$2.50; prices owned by `catalog-xai.json` per the Federation rule (xAI is now `overlay_mode: whole-element`, like DeepSeek) |
| grok-build-0.1     | —      | —         | REMOVED 2026-07-15 from Cursor's pricing page — Grok Build 0.1 no longer listed                                             |
| composer-2         | —      | —         | REMOVED 2026-07-15 from Cursor's pricing page — Composer 2 removed in favor of Composer 2.5 (2.5 supersedes 2 in Cursor's own listing) |
| composer-1.5       | —      | —         | REMOVED 2026-07-15 from Cursor's pricing page — Composer 1.5 no longer listed (Composer 1 still visible as legacy)          |
| gemini-2.5-flash   | $2.50  | Low       | New — added 2026-05-21; cheap multimodal Flash model now visible in `<model-options>` for SaaS-backend free-tier picks      |
| gemini-3-flash     | $3.00  | Low       | New — added 2026-05-21; Gemini 3 generation Flash variant; previously Hidden-by-default on Cursor's pricing page            |
| gemini-3-pro       | $12.00 | Medium    | New — added 2026-05-21; Gemini 3 generation Pro variant alongside gemini-3.1-pro                                            |
| gemini-3.5-flash   | $9.00  | Low       | New — added 2026-05-24; Gemini 3.5 Flash visible (un-hidden) on Cursor's pricing page; AA Intelligence Index 55.3 (high reasoning) places it as the strongest Flash-tier Gemini |
| gpt-5              | $10.00 | Medium    | New — added 2026-05-21; baseline GPT-5 family flagship                                                                      |
| gpt-5-mini         | $2.00  | Low       | New — added 2026-05-21; cheapest GPT-5 family variant ($2.00/M output)                                                      |
| gpt-5.1-codex      | $10.00 | Medium    | New — added 2026-05-21; earlier-generation Codex variant at $10/M output                                                    |
| composer-2.5       | $2.50  | Low       | New — added 2026-05-21; Composer 2 successor (same output price, equal-output-price replacement rule)                       |
| kimi-k2.5          | $3.00  | Low       | New — added 2026-05-21; Moonshot's Kimi K2.5 (routed via Cursor pool; no direct Moonshot access method enumerated yet)      |
| opus-4.8           | $25.00 | Very High | Benchmarks indexed 2026-06-04 — AA Intelligence Index 61.4 (#1), HLE 45.7%, Terminal-Bench Hard 58.3, τ²-bench retail 94.4%; tier-agentic bumped from A to S based on Terminal-Bench Hard + τ²-bench evidence |
| auto               | —      | —         | REMOVED 2026-05-21; Cursor-managed routing meta-model. Opaque routing conflicts with per-model tier ratings + jurisdiction filter |
| premium            | —      | —         | REMOVED 2026-05-21; Cursor-managed routing meta-model. Same rationale as `auto` removal                                     |


---

## Provider Jurisdictions

The selector's [`<jurisdiction-context>`](model-selector.txt) filter
consumes this reference table when applying the user's allowed-
jurisdictions list. Each row maps a provider HQ to an ISO-3166-1
alpha-2-style code; the `jurisdiction` attribute on every
`<model>` in `<model-options>` and the `provider-jurisdiction`
attribute on every `<method>` in `<access-methods>` derive from
this table.


| Provider HQ name              | Jurisdiction code | Models in catalog                                                                                                       |
| ----------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Anthropic (San Francisco, US) | `us`              | opus-4.8, opus-4.7, sonnet-4.6, claude-4.5-haiku                                                                        |
| OpenAI (San Francisco, US)    | `us`              | gpt-5.5, gpt-5.4, gpt-5.3-codex, gpt-5.2, gpt-5.1-codex, gpt-5, gpt-5.4-mini, gpt-5.4-nano, gpt-5-mini                  |
| Google (Mountain View, US)    | `us`              | gemini-3.1-pro, gemini-3-pro, gemini-3.5-flash, gemini-3-flash, gemini-2.5-flash                                        |
| xAI (Palo Alto, US)           | `us`              | grok-4.3                                                                                                                |
| Cursor (San Francisco, US)    | `us`              | composer-2, composer-2.5 — note: base weights for these Composer models derive from Moonshot's Kimi K2 series; Cursor's operator status determines the jurisdiction code per `<jurisdiction-context>` (data flow governed by Cursor's privacy policy and US law) |
| Meta (Menlo Park, US)         | `us`              | muse-spark-1.3                                                                                                                                                      |
| Moonshot AI (Beijing, CN)     | `cn`              | kimi-k2.5                                                                                                               |
| DeepSeek (Hangzhou, CN)       | `cn`              | deepseek-v4-pro, deepseek-flash                                                                                         |
| z.ai / Zhipu AI (Beijing, CN) | `cn`              | glm-5.2, glm-4.6, glm-4.5-air                                                                                           |
| Mistral AI (Paris, FR/EU)     | `eu`              | mistral-medium-3.5, mistral-small-4, mistral-large-3, codestral                                                         |
| Groq (Mountain View, US)      | `us`              | gpt-oss-120b, gpt-oss-20b (hosts OpenAI's open-weight gpt-oss; pinned host that defines per-token price + access)        |


Notes on the mapping:

- The jurisdiction code reflects the **operator** — the entity whose
  terms govern the data flow when a call is placed — not the base-
  weight origin. Composer 2 / Composer 2.5 are `us` because Cursor
  operates them; the Moonshot lineage is disclosed in the model's
  `best-for` for users whose compliance posture cares about base-
  weight origin.
- Newly-detected providers default to `unknown` per
  [`update/prompt.md`](../update/prompt.md)'s auto-add rule;
  maintainer fills them in editorially after one refresh cycle.
- This table is the source of truth — the per-model `jurisdiction`
  attribute and the per-method `provider-jurisdiction` attribute
  in `model-selector.txt` MUST match the codes in this table
  byte-for-byte. CI tests enforce the cross-doc invariant.

## Declined Models (discovery lane)

Models a provider's own pricing page lists that this catalog deliberately
does not carry. When the catalog cron declines a model the discovery lane
flags (`update/discovery.py`), it adds a line here and the flag stops. One
model per line, in exactly this form:
`- <provider>/<slug> — <reason> (declined YYYY-MM-DD)`.

- anthropic/Claude Mythos 5 — provider-page name for the Fable 5 model already carried as claude-fable-5 (identical $10/$50 pricing; Fable 5 is the Mythos-class model) (declined 2026-09-25)
- anthropic/Claude Mythos 5.1 — provider-page name for the Fable 5.1 model already carried as claude-fable-5.1 (identical $10/$50 pricing) (declined 2026-09-25)
- google/Gemini 2.5 Computer Use — computer-use variant, not a general text model (declined 2026-09-25)
- xai/grok-4.20-0309-non-reasoning — dated (0309) snapshot of the Grok 4.20 generation; the catalog carries grok-4.3 / grok-4.6 / grok-4.7 as the Grok line (declined 2026-09-25)
- xai/grok-4.20-0309-reasoning — dated (0309) snapshot of the Grok 4.20 generation; the catalog carries grok-4.3 / grok-4.6 / grok-4.7 as the Grok line (declined 2026-09-25)
- xai/grok-4.20-multi-agent-0309 — dated (0309) multi-agent variant of the Grok 4.20 generation; not a fixed single-engine model the catalog tracks (declined 2026-09-25)
- xai/grok-build-0.1 — build-agent preview removed from the catalog on 2026-07-15 when Cursor delisted it; retired (declined 2026-09-25)
- google/Gemini 3.1 Flash-Lite Image — an image, audio, video, embedding, robotics or computer-use model; the catalog rates general text models (declined 2026-10-07)
- google/Gemini Robotics Er 2 — an image, audio, video, embedding, robotics or computer-use model; the catalog rates general text models (declined 2026-10-07)
