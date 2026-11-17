// web/scripts/form-room.ts
// How well each model page holds room for its calculator (Phase 5 Step 18).
// A page reserves, before its calculator's form loads, the height src/lib/
// calculator.ts formRoom estimated for it at build time (an invisible <svg> in
// the calculator's card, one for a phone and one for a wide card), so nothing
// after the calculator moves when the form arrives. This opens every model
// page of the built site in Chromium at 390 and 1440 wide, reads the height
// held, lets the form load, measures the card, and prints the difference for
// each model with the median and the largest. tests/e2e/layout-shift.spec.ts
// is the gate; this is the instrument for refitting formRoom's numbers when a
// form's layout changes.
//
// Usage, after `npm run build`, with `npm run serve` running in another shell:
//     node scripts/form-room.ts
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const ORIGIN = "http://127.0.0.1:8788";
const WIDTHS = [
  { name: "narrow", width: 390, height: 844 },
  { name: "wide", width: 1440, height: 900 },
] as const;

interface Row {
  id: string;
  size: string;
  held: number;
  measured: number;
}

/** A model's page: `fixed_income.bond_pricing` is /models/fixed-income/bond-pricing/. */
function pagePath(id: string): string {
  return `/models/${id.replaceAll("_", "-").replace(".", "/")}/`;
}

function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted.at(Math.floor(sorted.length / 2)) ?? 0;
}

async function main(): Promise<number> {
  // The site data's registry export, a fixed path under web/.
  const registryFile = fileURLToPath(new URL("../src/data/generated/registry.json", import.meta.url));
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  const registry = JSON.parse(readFileSync(registryFile, "utf8")) as { models: { id: string }[] };
  const browser = await chromium.launch();
  const rows: Row[] = [];
  try {
    for (const size of WIDTHS) {
      const context = await browser.newContext({ viewport: { width: size.width, height: size.height }, baseURL: ORIGIN });
      const page = await context.newPage();
      for (const model of registry.models) {
        await page.goto(pagePath(model.id), { waitUntil: "load" });
        const card = page.locator(".calculator-card").first();
        const held = Number(await card.locator(`.calculator-room-${size.name}`).getAttribute("height"));
        await card.scrollIntoViewIfNeeded();
        await page.locator('[data-calculator][data-ready="true"]').waitFor({ timeout: 30_000 });
        await page.waitForTimeout(150);
        const box = await card.boundingBox();
        // The card's own padding and border sit around the form the room is held for.
        const frame = await card.evaluate((element) => {
          const style = getComputedStyle(element);
          return ["paddingTop", "paddingBottom", "borderTopWidth", "borderBottomWidth"].reduce(
            (sum, name) => sum + parseFloat(style.getPropertyValue(name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`))),
            0,
          );
        });
        rows.push({ id: model.id, size: size.name, held, measured: Math.round((box?.height ?? 0) - frame) });
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  for (const size of WIDTHS) {
    const found = rows.filter((row) => row.size === size.name);
    const errors = found.map((row) => Math.abs(row.held - row.measured));
    process.stdout.write(`\n${size.name} (${String(size.width)} wide): median error ${String(median(errors))} px, largest ${String(Math.max(...errors))} px\n`);
    for (const row of found.sort((a, b) => Math.abs(b.held - b.measured) - Math.abs(a.held - a.measured)).slice(0, 8)) {
      process.stdout.write(`  ${row.id}: held ${String(row.held)}, measured ${String(row.measured)} (${String(row.held - row.measured)})\n`);
    }
  }
  return 0;
}

process.exit(await main());
