// web/tests/unit/tokens.test.ts
// The design tokens' contrast (Phase 5 Step 17), computed from global.css in
// both themes: every pair of a text token and the surface it is written on
// reaches 4.5:1 (WCAG 2.2 SC 1.4.3), and every interface boundary and the
// focus ring reaches 3:1 against the surfaces they sit on (SC 1.4.11). A new
// token that carries text or marks a control joins TEXT or BOUNDARIES. axe
// checks the rendered pages; this checks the palette itself, every pair, in
// both themes, including pairs no sample page happens to show.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { contrastRatio, oklchToRgb, parseColour, themeTokens } from "@/lib/contrast";

const CSS = readFileSync(fileURLToPath(new URL("../../src/styles/global.css", import.meta.url)), "utf8");
const THEMES = themeTokens(CSS);

/** Text tokens and the surfaces each is written on: 4.5:1. */
const TEXT: readonly [string, readonly string[]][] = [
  ["foreground", ["background", "card", "muted", "accent", "secondary"]],
  ["card-foreground", ["card"]],
  ["muted-foreground", ["background", "card", "muted"]],
  ["primary-foreground", ["primary"]],
  ["secondary-foreground", ["secondary"]],
  ["accent-foreground", ["accent"]],
  ["link", ["background", "card", "muted"]],
  ["destructive", ["background", "card"]],
  ["highlight-foreground", ["highlight"]],
];

/** Interface boundaries and focus, and the surfaces they sit on: 3:1. */
const BOUNDARIES: readonly [string, readonly string[]][] = [
  ["input", ["background", "card"]],
  ["ring", ["background", "card", "muted"]],
  ["primary", ["background", "card"]],
];

describe("contrast arithmetic", () => {
  it("matches WCAG's own end points", () => {
    const black = parseColour("#000000", new Map());
    const white = parseColour("#ffffff", new Map());
    expect(contrastRatio(black, white)).toBeCloseTo(21, 5);
    expect(contrastRatio(white, white)).toBeCloseTo(1, 5);
  });

  it("converts OKLCH to sRGB", () => {
    const white = oklchToRgb(1, 0, 0);
    expect(white.r).toBeCloseTo(1, 3);
    expect(white.g).toBeCloseTo(1, 3);
    expect(white.b).toBeCloseTo(1, 3);
    // CSS Color 4's example: oklch(62.8% 0.2577 29.23) is sRGB red.
    const red = oklchToRgb(0.628, 0.2577, 29.23);
    expect(red.r).toBeCloseTo(1, 2);
    expect(red.g).toBeCloseTo(0, 2);
    expect(red.b).toBeCloseTo(0, 2);
  });

  it("composites a translucent colour over its surface", () => {
    const tokens = new Map([["base", "#ffffff"]]);
    const half = parseColour("oklch(0 0 0 / 50%)", tokens);
    expect(half.a).toBe(0.5);
    expect(contrastRatio(half, parseColour("var(--base)", tokens))).toBeLessThan(5);
  });
});

for (const [theme, tokens] of Object.entries(THEMES)) {
  describe(`the ${theme} theme`, () => {
    const colour = (name: string) => {
      const value = tokens.get(name);
      if (value === undefined) throw new Error(`global.css sets no --${name} in the ${theme} theme`);
      return parseColour(value, tokens);
    };

    for (const [text, surfaces] of TEXT) {
      for (const surface of surfaces) {
        it(`--${text} on --${surface} reaches 4.5:1`, () => {
          expect(contrastRatio(colour(text), colour(surface))).toBeGreaterThanOrEqual(4.5);
        });
      }
    }

    for (const [boundary, surfaces] of BOUNDARIES) {
      for (const surface of surfaces) {
        it(`--${boundary} against --${surface} reaches 3:1`, () => {
          expect(contrastRatio(colour(boundary), colour(surface))).toBeGreaterThanOrEqual(3);
        });
      }
    }
  });
}
