// web/tests/dogfood/teardown.ts
// After a harness run: gather every capture's record into index.json and an
// index.md an evaluator reads first (each page type and task, its files, its
// timings, and any overflow, stray scroll box, console error or policy
// violation), and draw a contact sheet per page type and task under sheets/:
// its first screens at the three widths, light above dark, on one image, so
// an evaluator sees every page type at every width in both themes in a few
// images, and opens the tiles for detail.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { chromium } from "@playwright/test";

import { THEMES, VIEWPORTS } from "./pages.ts";
import { BASE_URL, runDirectory, write, type CaptureRecord } from "./support.ts";

/** The height each first screen is drawn at on a contact sheet. */
const SHEET_ROW = 460;

function escape(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

/** The contact sheet's HTML: one row per theme, one column per width. */
function sheetPage(title: string, rows: { theme: string; images: { label: string; file: string; width: number; height: number }[] }[]): string {
  const cells = rows
    .map(
      (row) =>
        `<div class="row">${row.images
          .map(
            (image) =>
              `<figure><img src="../${escape(image.file)}" width="${String(Math.round((image.width * SHEET_ROW) / image.height))}" height="${String(SHEET_ROW)}" alt=""><figcaption>${escape(image.label)} · ${escape(row.theme)}</figcaption></figure>`,
          )
          .join("")}</div>`,
    )
    .join("");
  return `<!doctype html><meta charset="utf-8"><style>
body{margin:0;padding:12px;background:#888;font:14px system-ui,sans-serif;color:#111;width:max-content}
h1{font-size:16px;margin:0 0 8px}.row{display:flex;gap:12px;margin-bottom:12px}
figure{margin:0}img{display:block;border:1px solid #333}figcaption{padding-top:2px}
</style><h1>${escape(title)}</h1>${cells}`;
}

async function sheets(records: readonly CaptureRecord[]): Promise<string[]> {
  const groups = new Map<string, CaptureRecord[]>();
  for (const record of records) {
    const key = `${record.kind}-${record.id}`;
    groups.set(key, [...(groups.get(key) ?? []), record]);
  }
  const browser = await chromium.launch();
  const written: string[] = [];
  try {
    const page = await browser.newPage({ deviceScaleFactor: 1 });
    for (const [key, group] of groups) {
      const rows = THEMES.map((theme) => ({
        theme,
        images: VIEWPORTS.flatMap((viewport) => {
          const record = group.find((entry) => entry.viewport === viewport.name && entry.theme === theme);
          // A page's first screen; a task's last state.
          const file = record?.files.filter((name) => name.endsWith(".png") && !name.includes(".tile-") && !name.endsWith(".full.png")).at(record.kind === "page" ? 0 : -1);
          return file ? [{ label: viewport.name, file, width: viewport.width, height: viewport.height }] : [];
        }),
      })).filter((row) => row.images.length > 0);
      if (rows.length === 0) continue;
      const first = group[0];
      const html = write(`sheets/${key}.html`, sheetPage(`${first?.label ?? key} (${first?.path ?? ""})`, rows));
      await page.goto(pathToFileURL(join(runDirectory(), html)).href);
      await page.waitForLoadState("load");
      written.push(write(`sheets/${key}.png`, await page.screenshot({ fullPage: true })));
    }
  } finally {
    await browser.close();
  }
  return written;
}

export default async function teardown(): Promise<void> {
  const folder = join(runDirectory(), "records");
  if (!existsSync(folder)) return;
  const records = readdirSync(folder)
    .filter((name) => name.endsWith(".json"))
    .sort()
    .map((name) => JSON.parse(readFileSync(join(folder, name), "utf8")) as CaptureRecord);
  write("index.json", `${JSON.stringify({ site: BASE_URL, run: process.env.DOGFOOD_RUN, records }, null, 2)}\n`);
  const drawn = await sheets(records);
  const lines = [
    `# Dogfooding harness run ${process.env.DOGFOOD_RUN ?? ""}`,
    "",
    `Site: ${BASE_URL}. Files are relative to this folder.`,
    "",
    "Start with the contact sheets: each shows a page type's (or a task's) first screen at",
    "390, 820 and 1440 wide, light above dark.",
    "",
    ...drawn.map((file) => `- ${file}`),
    "",
    "Each page capture also has the whole page (`.full.png`), viewport-high tiles",
    "(`.tile-NN.png`, for reading a long page) and the accessibility tree (`.aria.yml`).",
    "",
    "| Kind | Id | Path | Viewport | Theme | Status | LCP ms | CLS | KB | Problems | Files |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
  ];
  for (const record of records) {
    const measures = record.measures;
    const problems = [
      ...(measures?.overflowX ? ["horizontal overflow"] : []),
      ...(measures?.strayScroll.length ? [`stray scroll: ${measures.strayScroll.join(", ")}`] : []),
      ...record.errors.map((error) => `console: ${error.slice(0, 120)}`),
      ...record.violations.map((violation) => `CSP ${violation.directive}`),
    ];
    lines.push(
      `| ${record.kind} | ${record.id} | ${record.path} | ${record.viewport} | ${record.theme} | ${String(record.status)} | ` +
        `${String(measures?.timings.lcp ?? "")} | ${String(measures?.timings.cls ?? "")} | ` +
        `${String(Math.round((measures?.transfer.bytes ?? 0) / 1024))} | ${problems.join("; ").replaceAll("|", "\\|") || "none"} | ` +
        `${record.files.filter((file) => !file.includes(".tile-")).join("<br>")} |`,
    );
  }
  write("index.md", `${lines.join("\n")}\n`);
}
