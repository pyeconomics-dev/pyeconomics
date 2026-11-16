// web/tests/dogfood/visit.ts
// The evaluators' browser (docs/design/dogfooding.md section 4): opens a page
// of the site under test in Chromium, scrollbars drawn, at a width and theme
// the evaluator chooses, follows the steps it is given, and saves screenshots
// to web/dogfood-out/<run>/visits/<name>/. It prints what it saved, the text
// it was asked to read, and any console error or policy violation; never a
// request header, so the Access token it may send stays unprinted.
//
//     node tests/dogfood/visit.ts --help
import { parseArgs } from "node:util";

import { chromium, type Locator, type Page } from "@playwright/test";

import { BASE_URL, LAUNCH, accessHeaders, measure, prepare, settled, write } from "./support.ts";

const HELP = `Usage: node tests/dogfood/visit.ts --path <page> [options]

Opens <page> on ${BASE_URL} in Chromium and follows --steps, a JSON array:
  {"goto": "/models/"}                       open another page of the site
  {"click": "Run"}                           click the button, link or disclosure with that name
                                             (exactly that name if one has it, else one containing it)
  {"click": {"role": "radio", "name": "Live data"}}   any ARIA role and name
  {"fill": {"label": "Coupon rate", "value": "0.04"}} type into a labelled field
  {"select": {"label": "Start from an example", "option": "par"}}
  {"press": "Tab"}                           a key, as Playwright names it
  {"type": "sharpe"}                         type into the focused element
  {"scroll": "bottom" | "top" | 1200 | {"to": "Calculator"}}  to a heading's text
  {"wait": 1000}                             milliseconds
  {"shot": "after-run"}                      screenshot of the window
  {"shot": "page", "full": true}             screenshot of the whole page
  {"read": "main"}                           print the visible text of a CSS selector
  {"aria": "main"}                           print the accessibility tree of a selector
A screenshot of the window is always saved at the end. From Git Bash, run it with
MSYS_NO_PATHCONV=1, or Git Bash rewrites --path /models/ into a Windows path.

Options:
  --path <page>     the first page, such as /models/ (required)
  --width <px>      390 (a phone, emulated as one), 820 or 1440 (default 1440)
  --height <px>     default 844 at 390, 1180 at 820, 900 otherwise
  --theme <scheme>  light or dark (default light)
  --steps <json>    the steps, as JSON text
  --name <name>     the folder for this visit's screenshots (default: visit)
  --run <name>      the run folder under web/dogfood-out/ (default: $DOGFOOD_RUN or adhoc)`;

type Step = Record<string, unknown>;

/**
 * What a click names: a button, a link or a disclosure's summary (which has no
 * ARIA role of its own, so no role finds it). The control whose name is
 * exactly the text wins over one that only contains it: "Run" is the Run
 * button, not the link "Run the calculator" above it (Phase 5 Step 18's round
 * 1, where both cost evaluators a wrong turn the site had not caused).
 */
async function by(page: Page, target: unknown): Promise<Locator> {
  if (typeof target === "string") {
    const named = (exact: boolean) =>
      page
        .getByRole("button", { name: target, exact })
        .or(page.getByRole("link", { name: target, exact }))
        .or(page.locator("summary").filter({ has: page.getByText(target, { exact }) }))
        .or(page.locator("summary").getByText(target, { exact }));
    const exact = named(true);
    return (await exact.count()) > 0 ? exact.first() : named(false).first();
  }
  const { role, name } = target as { role: Parameters<Page["getByRole"]>[0]; name?: string };
  return page.getByRole(role, name === undefined ? {} : { name }).first();
}

async function follow(page: Page, step: Step, shoot: (name: string, full: boolean) => Promise<void>): Promise<string | null> {
  if (typeof step.goto === "string") {
    await page.goto(step.goto, { waitUntil: "load" });
  } else if ("click" in step) {
    await (await by(page, step.click)).click();
  } else if ("fill" in step) {
    const { label, value } = step.fill as { label: string; value: string };
    await page.getByLabel(label).first().fill(value);
  } else if ("select" in step) {
    const { label, option } = step.select as { label: string; option: string };
    await page.getByLabel(label).first().selectOption({ label: option });
  } else if (typeof step.press === "string") {
    await page.keyboard.press(step.press);
  } else if (typeof step.type === "string") {
    await page.keyboard.type(step.type);
  } else if ("scroll" in step) {
    const where = step.scroll;
    if (where === "bottom") await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    else if (where === "top") await page.evaluate(() => window.scrollTo(0, 0));
    else if (typeof where === "number") await page.evaluate((y) => window.scrollTo(0, y), where);
    else await page.getByRole("heading", { name: (where as { to: string }).to }).first().scrollIntoViewIfNeeded();
  } else if (typeof step.wait === "number") {
    await page.waitForTimeout(step.wait);
  } else if (typeof step.shot === "string") {
    await shoot(step.shot, step.full === true);
  } else if (typeof step.read === "string") {
    return (await page.locator(step.read).first().innerText()).slice(0, 6000);
  } else if (typeof step.aria === "string") {
    return (await page.locator(step.aria).first().ariaSnapshot()).slice(0, 8000);
  } else {
    throw new Error(`unknown step ${JSON.stringify(step)}`);
  }
  await page.waitForTimeout(300);
  return null;
}

async function main(): Promise<number> {
  const { values } = parseArgs({
    options: {
      path: { type: "string" },
      width: { type: "string", default: "1440" },
      height: { type: "string" },
      theme: { type: "string", default: "light" },
      steps: { type: "string", default: "[]" },
      name: { type: "string", default: "visit" },
      run: { type: "string" },
      help: { type: "boolean", default: false },
    },
  });
  if (values.path !== undefined && /^[A-Za-z]:[\\/]/.test(values.path)) {
    // Git Bash rewrites an argument that starts with "/" into a Windows path.
    process.stderr.write("--path became a Windows path: from Git Bash, run with MSYS_NO_PATHCONV=1\n");
    return 2;
  }
  if (values.help || !values.path?.startsWith("/")) {
    process.stdout.write(`${HELP}\n`);
    return values.help ? 0 : 2;
  }
  if (values.run) process.env.DOGFOOD_RUN = values.run;
  if (!/^[\w-]+$/.test(values.name)) throw new Error("--name may hold letters, digits, '_' and '-' only");
  const width = Number(values.width);
  const phone = width <= 480;
  const height = Number(values.height ?? (phone ? 844 : width <= 900 ? 1180 : 900));
  const theme = values.theme === "dark" ? "dark" : "light";
  const steps = JSON.parse(values.steps) as Step[];

  const browser = await chromium.launch(LAUNCH);
  const context = await browser.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: accessHeaders(),
    viewport: { width, height },
    isMobile: phone,
    hasTouch: phone,
    deviceScaleFactor: 1,
    colorScheme: theme,
  });
  const page = await context.newPage();
  const watch = await prepare(page);
  const saved: string[] = [];
  let count = 0;
  const shoot = async (name: string, full: boolean) => {
    count += 1;
    const file = `visits/${values.name}/${String(count).padStart(2, "0")}-${name.replace(/[^\w-]/g, "_")}-${String(width)}-${theme}.png`;
    await settled(page);
    saved.push(write(file, await page.screenshot({ fullPage: full })));
  };
  const output: string[] = [];
  let failed = false;
  try {
    const response = await page.goto(values.path, { waitUntil: "load" });
    output.push(`opened ${values.path}: HTTP ${String(response?.status() ?? "none")}`);
    for (const step of steps) {
      const text = await follow(page, step, shoot);
      output.push(`step ${JSON.stringify(step)}: ok`);
      if (text !== null) output.push(text);
    }
  } catch (error) {
    failed = true;
    output.push(`step failed: ${error instanceof Error ? (error.message.split("\n")[0] ?? "") : String(error)}`);
  }
  await shoot("end", false);
  const measures = await measure(page).catch(() => null);
  const address = new URL(page.url());
  await browser.close();
  output.push(`final address: ${address.pathname}${address.search}`);
  output.push(`screenshots (under web/dogfood-out/${process.env.DOGFOOD_RUN ?? "adhoc"}/):`, ...saved.map((file) => `  ${file}`));
  if (measures) {
    output.push(
      `horizontal overflow: ${measures.overflowX ? "yes" : "no"}; boxes scrolling without a maximum height: ${measures.strayScroll.join(", ") || "none"}`,
    );
  }
  output.push(`console errors: ${watch.errors.length ? watch.errors.join(" | ") : "none"}`);
  output.push(`policy violations: ${watch.violations.length ? watch.violations.map((v) => v.directive).join(", ") : "none"}`);
  process.stdout.write(`${output.join("\n")}\n`);
  return failed ? 1 : 0;
}

process.exit(await main());
