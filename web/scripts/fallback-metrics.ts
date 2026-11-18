// web/scripts/fallback-metrics.ts
// The numbers behind the fallback faces of the site's text font (issue #354).
// Literata is declared `font-display: swap`, so a page whose font arrives after
// its first paint is drawn once in a system serif and again in Literata. Where
// the two differ in width and height, text reflows and what is under it moves.
// src/styles/global.css therefore declares fallback faces over the system
// serifs with Literata's metrics (`size-adjust`, `ascent-override`,
// `descent-override`, `line-gap-override`), so the swap changes the letters'
// shapes and not where anything is.
//
// This prints those descriptors as Chromium itself measures them: it loads
// Literata from the package's own file into a blank page and compares, in
// Literata and in each system serif this machine has, the width of a sample
// of text, the ascent and descent and the height of a line. Three faces for
// each serif: running text, headings (Literata is heavier there than a
// system bold) and the header's labels. The ratio of widths depends on the
// letters: Literata sets a row of capitalised words a hundredth wider,
// against Georgia, than it sets prose, and a face fitted to prose put one
// more link on the header's first line, which moved the row when the font
// arrived. tests/e2e/late-fonts.spec.ts is the gate (a page whose fonts
// arrive late must not move); this is the instrument for refitting the
// numbers when the font package or the header's words change.
//
// Usage:
//     node scripts/fallback-metrics.ts [--font "Noto Serif=regular.woff2,bold.woff2"]...
// A --font loads a face this machine lacks from its files (another system's
// serif), so its numbers can be measured here too.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

/** The system serifs a fallback face is declared over, in the order the stack tries them. */
const FALLBACKS = ["Georgia", "Times New Roman", "Liberation Serif", "Noto Serif"] as const;

/** A paragraph of plain prose: running text. */
const PROSE =
  "A model gives its formula, the sources it follows and the values it was tested against, so a reader can check " +
  "each step and cite the result. Rates, returns and yields are decimals throughout, and every number carries its " +
  "unit. The same inputs give the same result from the website, from Python and from the command line, every time.";

/** The words of the site's header: its main links and the fifteen domains. */
const LABELS =
  "Models Data Coverage Search Documentation GitHub Foundations Econometrics Macroeconomics International economics " +
  "Microeconomics Accounting Corporate finance Equity Fixed income Derivatives Alternatives Portfolio Asset pricing " +
  "Risk Performance";

/** Each face: Literata's weight there, the weight of the system face that stands in, and the text it is fitted to. */
const FACES = [
  { name: "text", literata: 400, fallback: 400, sample: PROSE },
  { name: "heading", literata: 650, fallback: 700, sample: PROSE },
  { name: "label", literata: 400, fallback: 400, sample: LABELS },
] as const;

interface Measure {
  available: boolean;
  width: number;
  ascent: number;
  descent: number;
  line: number;
}

function dataUrl(path: string): string {
  // The package's own font file, or one named on the command line by whoever runs this.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return `data:font/woff2;base64,${readFileSync(path).toString("base64")}`;
}

function percent(value: number): string {
  return `${(Math.round(value * 10000) / 100).toFixed(2)}%`;
}

async function main(): Promise<number> {
  const extra = new Map<string, string[]>();
  const args = process.argv.slice(2);
  for (let index = 0; index < args.length; index += 1) {
    if (args.at(index) !== "--font") continue;
    const [name = "", files = ""] = (args.at(index + 1) ?? "").split("=");
    extra.set(name, files.split(","));
  }
  const literata = fileURLToPath(
    new URL("../node_modules/@fontsource-variable/literata/files/literata-latin-wght-normal.woff2", import.meta.url),
  );
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent("<!doctype html><html><body></body></html>");
    const faces = [
      { family: "Literata Variable", url: dataUrl(literata), weight: "200 900" },
      ...[...extra].flatMap(([family, files]) =>
        files.map((file, index) => ({ family, url: dataUrl(file), weight: index === 0 ? "400" : "700" })),
      ),
    ];
    await page.evaluate(async (list) => {
      for (const face of list) {
        const loaded = await new FontFace(face.family, `url(${face.url})`, { weight: face.weight }).load();
        document.fonts.add(loaded);
      }
    }, faces);
    const measure = (family: string, weight: number, sample: string): Promise<Measure> =>
      page.evaluate(
        ([name, bold, text]) => {
          // The page's own layout, with the features the site turns on: what a line of text really takes.
          const span = (font: string) => {
            const element = document.createElement("span");
            element.textContent = text;
            element.setAttribute("style", `font: ${font}; white-space: nowrap; position: absolute; font-feature-settings: "kern", "liga"`);
            document.body.append(element);
            const box = element.getBoundingClientRect();
            element.remove();
            return box;
          };
          // A family this machine lacks measures as the generic one after it, whichever that is.
          const available =
            span(`${String(bold)} 100px "${name}", monospace`).width !== span(`${String(bold)} 100px monospace`).width &&
            span(`${String(bold)} 100px "${name}", sans-serif`).width !== span(`${String(bold)} 100px sans-serif`).width;
          const context = document.createElement("canvas").getContext("2d");
          if (!context) throw new Error("no canvas");
          context.font = `${String(bold)} 1000px "${name}"`;
          const metrics = context.measureText("Hg");
          return {
            available,
            width: span(`${String(bold)} 100px "${name}"`).width,
            ascent: metrics.fontBoundingBoxAscent / 1000,
            descent: metrics.fontBoundingBoxDescent / 1000,
            line: span(`${String(bold)} 1000px/normal "${name}"`).height / 1000,
          };
        },
        [family, weight, sample] as const,
      );
    for (const face of FACES) {
      const own = await measure("Literata Variable", face.literata, face.sample);
      const gap = Math.max(0, own.line - own.ascent - own.descent);
      process.stdout.write(
        `\n${face.name}: Literata at ${String(face.literata)}, ascent ${own.ascent.toFixed(4)}, descent ${own.descent.toFixed(4)}, ` +
          `line ${own.line.toFixed(4)}\n`,
      );
      for (const family of FALLBACKS) {
        const system = await measure(family, face.fallback, face.sample);
        if (!system.available) {
          process.stdout.write(`  ${family}: not on this machine\n`);
          continue;
        }
        const adjust = own.width / system.width;
        process.stdout.write(
          `  ${family}: size-adjust ${percent(adjust)}; ascent-override ${percent(own.ascent / adjust)}; ` +
            `descent-override ${percent(own.descent / adjust)}; line-gap-override ${percent(gap / adjust)}\n`,
        );
      }
    }
  } finally {
    await browser.close();
  }
  return 0;
}

process.exit(await main());
