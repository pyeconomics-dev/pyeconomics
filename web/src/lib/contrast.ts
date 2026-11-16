// web/src/lib/contrast.ts
// WCAG 2.2 contrast computed from the design tokens (Phase 5 Step 17): parse a
// token's colour (oklch(), with an optional alpha, a #hex, or var() of another
// token), composite a translucent colour over what it sits on, and compare
// relative luminance (WCAG 2.2, "contrast ratio"). OKLCH converts to sRGB
// through OKLab (Björn Ottosson's matrices), with out-of-gamut channels
// clipped as a browser clips them. The token test reads the palette with it,
// and the charts convert the tokens to the rgb() Plotly takes (plotly.ts
// themed()).

/** An sRGB colour, each channel in [0, 1] as encoded (not linear), with alpha. */
export interface Rgba {
  r: number;
  g: number;
  b: number;
  a: number;
}

const clip = (value: number) => Math.min(1, Math.max(0, value));

/** Encode one linear sRGB channel (the sRGB transfer function). */
function encode(linear: number): number {
  const value = clip(linear);
  return value <= 0.0031308 ? 12.92 * value : 1.055 * value ** (1 / 2.4) - 0.055;
}

/** Decode one encoded sRGB channel to linear light. */
function decode(encoded: number): number {
  return encoded <= 0.04045 ? encoded / 12.92 : ((encoded + 0.055) / 1.055) ** 2.4;
}

/** OKLCH (lightness 0..1, chroma, hue in degrees) to encoded sRGB. */
export function oklchToRgb(lightness: number, chroma: number, hue: number, alpha = 1): Rgba {
  const radians = (hue * Math.PI) / 180;
  const a = chroma * Math.cos(radians);
  const b = chroma * Math.sin(radians);
  const l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (lightness - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return {
    r: encode(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    g: encode(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    b: encode(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
    a: alpha,
  };
}

/** oklch(L C H) or oklch(L C H / A), each a number, L and A optionally in percent. */
function parseOklch(text: string): Rgba | null {
  if (!text.startsWith("oklch(") || !text.endsWith(")")) return null;
  const [channels = "", alphaText] = text.slice("oklch(".length, -1).split("/");
  const parts = channels.trim().split(/\s+/);
  if (parts.length !== 3) return null;
  const amount = (part: string, scale: number) => (part.endsWith("%") ? Number(part.slice(0, -1)) / scale : Number(part.replace(/deg$/, "")));
  const [lightness, chroma, hue] = [amount(parts[0] ?? "", 100), amount(parts[1] ?? "", 1), amount(parts[2] ?? "", 1)];
  const alpha = alphaText === undefined ? 1 : amount(alphaText.trim(), 100);
  if (![lightness, chroma, hue, alpha].every(Number.isFinite)) return null;
  return oklchToRgb(lightness, chroma, hue, alpha);
}
const HEX = /^#([0-9a-f]{6})$/i;
const VAR = /^var\(\s*--([\w-]+)\s*\)$/;

/** Parse a token's value, following var() through `tokens`. */
export function parseColour(value: string, tokens: ReadonlyMap<string, string>, depth = 0): Rgba {
  const text = value.trim();
  const reference = VAR.exec(text);
  if (reference) {
    const target = tokens.get(reference[1] ?? "");
    if (target === undefined || depth > 8) throw new Error(`unresolved colour ${text}`);
    return parseColour(target, tokens, depth + 1);
  }
  const hex = HEX.exec(text);
  if (hex) {
    const digits = hex[1] ?? "000000";
    const channel = (at: number) => parseInt(digits.slice(at, at + 2), 16) / 255;
    return { r: channel(0), g: channel(2), b: channel(4), a: 1 };
  }
  const colour = parseOklch(text);
  if (!colour) throw new Error(`not a colour this test reads: ${text}`);
  return colour;
}

/** A translucent colour over an opaque one, as a browser composites in sRGB. */
export function over(top: Rgba, bottom: Rgba): Rgba {
  const mix = (a: number, b: number) => a * top.a + b * (1 - top.a);
  return { r: mix(top.r, bottom.r), g: mix(top.g, bottom.g), b: mix(top.b, bottom.b), a: 1 };
}

/** WCAG's relative luminance of an opaque colour. */
export function luminance(colour: Rgba): number {
  return 0.2126 * decode(colour.r) + 0.7152 * decode(colour.g) + 0.0722 * decode(colour.b);
}

/** WCAG's contrast ratio of two colours; a translucent foreground is composited over the background. */
export function contrastRatio(foreground: Rgba, background: Rgba): number {
  const front = luminance(over(foreground, background));
  const back = luminance(background);
  return (Math.max(front, back) + 0.05) / (Math.min(front, back) + 0.05);
}

/**
 * The custom properties of a stylesheet's light :root block and of its dark
 * blocks (the system preference), each a map from name (no dashes) to value.
 * Dark values fall back to light ones the dark blocks do not set.
 */
export function themeTokens(css: string): { light: Map<string, string>; dark: Map<string, string> } {
  const read = (block: string) =>
    new Map([...block.matchAll(/--([\w-]+)\s*:\s*([^;]+);/g)].map((found) => [found[1] ?? "", (found[2] ?? "").trim()]));
  const body = (from: number) => {
    const open = css.indexOf("{", from);
    let depth = 0;
    for (let at = open; at < css.length; at += 1) {
      if (css.charAt(at) === "{") depth += 1;
      if (css.charAt(at) === "}") depth -= 1;
      if (depth === 0) return css.slice(open + 1, at);
    }
    throw new Error("unbalanced braces");
  };
  const lightAt = css.search(/^:root\s*\{/m);
  if (lightAt < 0) throw new Error("no :root block");
  const light = read(body(lightAt));
  const darkAt = css.search(/@media \(prefers-color-scheme: dark\)\s*\{/);
  if (darkAt < 0) throw new Error("no dark block");
  const dark = new Map([...light, ...read(body(darkAt))]);
  return { light, dark };
}
