// web/tests/dogfood/tasks.spec.ts
// The scripted interaction states the evaluators read beside the page captures
// (docs/design/dogfooding.md section 5): a calculator before and after a run, a
// run with a chart, a family's second example, the form's error state, the
// explorer's chart, a search, the domains menu on a phone, and the notice of a
// model whose data the hosted site may not serve. Each at a phone's and a
// desktop's width in both themes. Every state is saved before a step that
// fails, and the failure is recorded and then fails the test.
import { expect, test, type Locator, type Page } from "@playwright/test";

import { THEMES, VIEWPORTS } from "./pages.ts";
import { choose, measure, prepare, settled, write, writeRecord } from "./support.ts";

interface Task {
  id: string;
  path: string;
  label: string;
  /** Phone only (the domains menu is a desktop row). */
  phoneOnly?: boolean;
  run: (page: Page, shot: (name: string, target?: Locator) => Promise<void>) => Promise<void>;
}

async function calculator(page: Page): Promise<Locator> {
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await page.locator('[data-calculator][data-ready="true"]').waitFor({ timeout: 30_000 });
  return section;
}

async function runAndWait(section: Locator): Promise<void> {
  await section.getByRole("button", { name: "Run", exact: true }).click();
  await section
    .getByRole("heading", { name: /^(Result|The run failed)$/ })
    .waitFor({ timeout: 30_000 });
}

const TASKS: readonly Task[] = [
  {
    id: "calculator-run",
    path: "/models/performance/risk-adjusted/",
    label: "A calculator before and after a run",
    run: async (page, shot) => {
      const section = await calculator(page);
      await shot("before");
      await runAndWait(section);
      await shot("after", section.locator("[data-outcome]"));
    },
  },
  {
    id: "chart-run",
    path: "/models/econometrics/ols/",
    label: "A run that draws a chart",
    run: async (page, shot) => {
      const section = await calculator(page);
      await runAndWait(section);
      await section.locator("figure [role='img'] .main-svg").first().waitFor({ timeout: 30_000 });
      await shot("after", section.locator("figure").first());
    },
  },
  {
    id: "family-example",
    path: "/models/fixed-income/duration/",
    label: "A family's second example",
    run: async (page, shot) => {
      const section = await calculator(page);
      const picker = section.getByLabel("Start from an example");
      if ((await picker.count()) > 0) await choose(page, picker, { index: 1 });
      await shot("second-example");
    },
  },
  {
    id: "form-error",
    path: "/models/corporate/leverage/",
    label: "The form's error state",
    run: async (page, shot) => {
      const section = await calculator(page);
      await section.locator("form input[type='number']").first().fill("");
      await section.getByRole("button", { name: "Run", exact: true }).click();
      await page.waitForTimeout(500);
      await shot("error");
    },
  },
  {
    id: "explorer",
    path: "/data/us/unemployment/rate/",
    label: "The data explorer's chart",
    run: async (page, shot) => {
      const explorer = page.locator("[data-hydrated]").first();
      await explorer.scrollIntoViewIfNeeded();
      await page.locator('[data-hydrated="true"]').first().waitFor({ timeout: 30_000 });
      await shot("before", explorer);
      await explorer.getByRole("button", { name: "Draw the chart" }).click();
      await explorer.locator("[role='img'] .main-svg").first().waitFor({ timeout: 30_000 });
      await shot("after", explorer);
    },
  },
  {
    id: "search",
    path: "/search/?q=sharpe",
    label: "A search for 'sharpe'",
    run: async (page, shot) => {
      await page.getByRole("main").getByRole("link").first().waitFor({ timeout: 30_000 });
      await page.waitForTimeout(500);
      await shot("results");
    },
  },
  {
    id: "domains-menu",
    path: "/",
    label: "The domains menu on a phone",
    phoneOnly: true,
    run: async (page, shot) => {
      await page.locator("[data-domains-menu] summary").click();
      await shot("open");
    },
  },
  {
    id: "library-only",
    path: "/models/equity/cape/",
    label: "A model whose data the hosted site may not serve",
    run: async (page, shot) => {
      const section = await calculator(page);
      await shot("notice", page.locator("[data-library-only]"));
      const live = section.getByRole("radio", { name: /Live data/ });
      if ((await live.count()) > 0 && (await live.isEnabled())) {
        await live.check();
        await shot("live-chosen", section.locator("[data-live]"));
      }
    },
  },
];

const SIZES = VIEWPORTS.filter((viewport) => viewport.name !== "820x1180");

for (const task of TASKS) {
  for (const viewport of SIZES.filter((size) => size.phone || !task.phoneOnly)) {
    for (const theme of THEMES) {
      test(`tasks ${task.id} ${viewport.name} ${theme}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
          isMobile: viewport.phone,
          hasTouch: viewport.phone,
          deviceScaleFactor: 1,
          colorScheme: theme,
        });
        const page = await context.newPage();
        const watch = await prepare(page);
        const files: string[] = [];
        const shot = async (name: string, target?: Locator) => {
          const stem = `tasks/${task.id}/${viewport.name}-${theme}-${name}.png`;
          // What a visitor sees once the page has stopped moving.
          await settled(page);
          // A target's own box, or the window as the visitor sees it.
          files.push(write(stem, target ? await target.screenshot() : await page.screenshot()));
        };
        const response = await page.goto(task.path, { waitUntil: "load" });
        let failure: unknown = null;
        try {
          await task.run(page, shot);
        } catch (error) {
          failure = error;
          await shot("failed").catch(() => undefined);
          watch.errors.push(`task step failed: ${error instanceof Error ? error.message.split("\n")[0] ?? "" : String(error)}`);
        }
        writeRecord({
          kind: "task",
          id: task.id,
          path: task.path,
          label: task.label,
          viewport: viewport.name,
          theme,
          status: response?.status() ?? null,
          files,
          measures: await measure(page),
          violations: watch.violations,
          errors: watch.errors,
        });
        await context.close();
        expect(failure).toBeNull();
      });
    }
  }
}
