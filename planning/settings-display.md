# Settings display — turning the selector's output into a surface's real controls

`model-selector.txt` emits an **output contract version 2** block. Every
*setting* field in it is **platform-conditional** — the block carries only the
dials the chosen `PLATFORM` actually exposes:

```text
MAX MODE: [On/Off]                             emit iff exposes-max-mode="yes"     (today: Cursor)
EFFORT: [Low/Medium/High/XHigh/Max/Ultracode]  emit iff exposes-thinking="yes"
THINKING: [On/Off]                             emit iff exposes-thinking="yes" and the model is not always-thinks="yes"
ORCHESTRATION: [None/PerPrompt]                emit iff exposes-orchestration="yes" (today: Claude Code)
```

Two rules carry the weight, and they are worth restating because v1 broke both:

- **A dial the platform lacks means the LINE IS ABSENT** — never `Off`, never
  `N/A`, never an empty value. An omitted line means *"this surface has no such
  control"*, which is a different fact from *"the control exists and is off"*.
- **`EFFORT` carries the reasoning LEVEL; `THINKING` is a two-position toggle.**
  `THINKING` is only ever `On` or `Off` — never an effort word, never a number.
  `THINKING: Max` was the v1 bug this split exists to kill. The selector says
  a session-wide Ultracode as the **top value of `EFFORT`** (`EFFORT:
  Ultracode` = ultracode on at `xhigh`, what `claude --effort ultracode` sets).
- **A model that always thinks has no Thinking toggle on any surface.** Opus
  5.5, Sonnet 5.5, Haiku 5.5, Fable 5 and Fable 5.1 (`always-thinks="yes"` in
  the selector's `<model-options>`, `always_thinks` in `catalog.json`) cannot
  have extended thinking turned off: Claude Code shows "Thinking can't be
  turned off" in place of the switch (2.1.281) and its VS Code panel hides the
  toggle (2.1.300). Effort alone sets how much they think, so their settings
  carry **no Thinking row**, even when a block carried a `THINKING` line.

Even so, those field names are still the selector's **vocabulary**, not the
labels a user sees. Every surface names its dials differently, so the axes must
be mapped before they are shown in a roadmap table or a settings block.

**Who owns what.** The selector owns the **emission** rule — *which* dials exist
on a platform at all, driven by each access method's `exposes-max-mode` /
`exposes-thinking` / `exposes-orchestration` attributes (see `<output-format>`
and `<access-selection>` Step G). This doc owns the **display** rule — what to
*call* those dials on each surface, and how to fold them into the controls the
UI actually shows. The display rule deliberately stays out of the selector
because the daily effort/thinking conformance tracker pins the selector's
vocabulary (it requires, e.g., `Ultracode` to read as a session setting) and
would revert display-only wording. `roadmodel`'s own `recommend_structured`
applies exactly the rules below, so an offline consumer that follows this doc
produces byte-identical settings.

## Backward compatibility — v1 blocks still arrive

Cached engine responses, older `roadmodel` releases running in production, and
previously-exported offline planning kits all still emit **version 1** blocks:
`MAX MODE` always present (pinned `Off` off-Cursor), no `EFFORT` line, and
`THINKING` carrying the effort level (`Off/Low/Medium/High/XHigh/Max/N/A`).
Everything here **dual-accepts**. The rule is uniform:

> When a block carries an explicit `EFFORT`, use it verbatim and read `THINKING`
> as the On/Off toggle. When it does not, fall back to the v1 derivation, in
> which `THINKING` *is* the effort level.

## Claude Code → **Effort** + **Ultracode** + **Thinking**

Claude Code shows an **effort slider** — `Low` / `Medium` / `High` / `XHigh` /
`Max` — an **Ultracode on/off switch** beside it (its own toggle since 2.1.284,
working at any effort level), and a **Thinking on/off toggle only on models that
can turn thinking off** (Opus 5, Sonnet 5, the 4.x models). It has **no Max
Mode**; never show one, even if a legacy block carried the line. The settings
read in that order: effort, ultracode, thinking.

- **v2** — `EFFORT` → **Effort**, verbatim, except `EFFORT: Ultracode`, which is
  shown as the two controls it sets: **Effort `XHigh`** and **Ultracode `On`**.
  `THINKING` → **Thinking `On`/`Off`**; absent `THINKING` displays as `On` —
  unless the `MODEL` always thinks, which shows **no Thinking row**. An explicit
  `EFFORT` **wins outright**: on a transitional block that carries both `EFFORT`
  and a legacy `ORCHESTRATION: Ultracode`, the `EFFORT` value is displayed and
  the orchestration value is ignored (v2 restricts `ORCHESTRATION` to
  `None`/`PerPrompt`, so `Ultracode` there is stale input).
- **Frontier ladder** — where the scorer's row puts a Claude Code rung at `max`
  and the engine wrote `Ultracode`, the pick runs at **Effort `Max`** with
  **Ultracode `On`** (`/effort max`, then `/effort ultracode`).
- **v1 legacy** — `ORCHESTRATION: Ultracode` → **Effort `XHigh`**, **Ultracode
  `On`**, **Thinking `On`**. Never emit a separate "Orchestration" row —
  `Effort: High + Orchestration: Ultracode` is incoherent and does not match
  the UI.
- **v1 legacy** — `THINKING` of `Off` / `N/A` / `None` / `No` → **Effort `Low`**,
  **Thinking `Off`**. Otherwise → **Effort = the `THINKING` value**, **Thinking
  `On`**.
- On a model that always thinks, every case above drops its Thinking row.

## Codex + OpenAI API → **Intelligence**

- **Intelligence = the `EFFORT` value**, falling back to the `THINKING` value on
  a v1 block. No Max Mode row, no separate Thinking row.
- Applies to both Codex and the direct **OpenAI API** — OpenAI's reasoning
  surfaces expose a reasoning-effort dial (surfaced as Intelligence), never Max
  Mode. (ChatGPT the consumer app has no fine dial and stays in the catch-all.)

## Cursor → **Max Mode** + **Thinking**

- **Max Mode** = `ON` when the block's `MAX MODE` line is on, else `OFF`.
- **Thinking `On`** — always. Cursor's frontier models always reason but the IDE
  exposes **no thinking dial**, so a v2 block emits neither `EFFORT` nor
  `THINKING` (v1 emitted `THINKING: N/A`). Shown raw, either reads as "no
  controllable settings at all", which is wrong: the user's real dial on Cursor
  is Max Mode. **Never emit an Effort row for Cursor** — there is no such dial.

## Every other surface (Anthropic API, ChatGPT, …) → **Max Mode?** + **Effort/Thinking**

- **Max Mode is emitted ONLY when the block actually carried a `MAX MODE` line.**
  This is the D1 fix at the display layer: v1 pinned the line to `Off` on every
  non-Cursor surface, so an Anthropic-API or ChatGPT pick used to show a Max
  Mode row for a control those surfaces do not have. A v2 block omits the line;
  so do we.
- **v2** → **Effort = the `EFFORT` value**, **Thinking = `On`/`Off`** — no
  Thinking row for a model that always thinks, wherever it is served (Anthropic
  API, OpenRouter, Antigravity).
- **v1 legacy** → **Thinking = the `THINKING` value** (which carried the level),
  and no Effort row.

`MAX MODE` counts as on for `on` / `yes` / `true` / `enabled` (case-insensitive);
anything else is `OFF`. `THINKING` counts as off for `off` / `n/a` / `none` /
`no` (case-insensitive); anything else is `On`.

## Conformance table

Machine-checked against `roadmodel.recommend._structured_settings` — if this
table and the code ever disagree, the test suite fails.

The input columns are the **block fields as parsed**. An em dash (`—`) means the
block carried **no such line** (in the MODEL column: no model, so no model-specific
rule applies) — the v2 "this surface has no such dial" signal —
and is not the same as an explicit `Off` or `N/A`. Rows marked *v1* are the
legacy shape kept alive for cached responses and older releases.

<!-- conformance-table:start -->

| PLATFORM | MODEL | MAX MODE | EFFORT | THINKING | ORCHESTRATION | Displayed settings |
|---|---|---|---|---|---|---|
| Claude Code | — | — | Max | On | None | effort=Max; thinking=On |
| Claude Code | — | — | Ultracode | On | None | effort=XHigh; ultracode=On; thinking=On |
| Claude Code | — | — | XHigh | On | PerPrompt | effort=XHigh; thinking=On |
| Claude Code | — | — | Low | Off | None | effort=Low; thinking=Off |
| Claude Code | — | Off | XHigh | — | Ultracode | effort=XHigh; thinking=On |
| Claude Code | — | Off | — | XHigh | Ultracode | effort=XHigh; ultracode=On; thinking=On |
| Claude Code | — | Off | — | Max | Ultracode | effort=XHigh; ultracode=On; thinking=On |
| Claude Code | — | Off | — | XHigh | None | effort=XHigh; thinking=On |
| Claude Code | — | Off | — | High | None | effort=High; thinking=On |
| Claude Code | — | Off | — | Off | None | effort=Low; thinking=Off |
| Claude Code | — | Off | — | N/A | None | effort=Low; thinking=Off |
| Codex | — | — | XHigh | On | None | intelligence=XHigh |
| Codex | — | Off | — | High | None | intelligence=High |
| Codex | — | Off | — | XHigh | None | intelligence=XHigh |
| OpenAI API | — | — | High | On | None | intelligence=High |
| OpenAI API | — | Off | — | High | None | intelligence=High |
| OpenAI API | — | Off | — | XHigh | None | intelligence=XHigh |
| Cursor | — | On | — | — | None | max_mode=ON; thinking=On |
| Cursor | — | Off | — | — | None | max_mode=OFF; thinking=On |
| Cursor | — | On | — | N/A | None | max_mode=ON; thinking=On |
| Cursor | — | Off | — | N/A | None | max_mode=OFF; thinking=On |
| Anthropic API | — | — | Max | On | None | effort=Max; thinking=On |
| Anthropic API | — | — | High | Off | None | effort=High; thinking=Off |
| Anthropic API | — | On | — | High | None | max_mode=ON; thinking=High |
| ChatGPT | — | — | Medium | On | None | effort=Medium; thinking=On |
| ChatGPT | — | Off | — | Medium | None | max_mode=OFF; thinking=Medium |
| Claude Code | Opus 5.5 | — | High | On | None | effort=High |
| Claude Code | Opus 5.5 | — | Low | Off | None | effort=Low |
| Claude Code | claude-opus-5-5 | — | XHigh | — | None | effort=XHigh |
| Claude Code | Claude Opus 5.5 | — | Ultracode | On | None | effort=XHigh; ultracode=On |
| Claude Code | Fable 5.1 | — | Max | On | None | effort=Max |
| Claude Code | Sonnet 5.5 | Off | — | Off | None | effort=Low |
| Claude Code | Opus 5 | — | High | Off | None | effort=High; thinking=Off |
| Claude Code | Opus 4.8 | — | Ultracode | On | None | effort=XHigh; ultracode=On; thinking=On |
| Anthropic API | Haiku 5.5 | — | Medium | On | None | effort=Medium |
| OpenRouter | Opus 5.5 | — | High | On | None | effort=High |
| Anthropic API | Opus 5 | — | High | Off | None | effort=High; thinking=Off |

<!-- conformance-table:end -->
