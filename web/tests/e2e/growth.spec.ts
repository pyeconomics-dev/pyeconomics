// web/tests/e2e/growth.spec.ts
// Gate G2's instruments in the browser (Phase 5 Step 15; ADR-0013 decisions
// 13 and 14).
//
// The sign-up forms: each posts, by navigation, straight to the email
// processor's endpoint, with the address, the list, the source and (on the
// waitlist) the tier; the browser's whole network log holds no other request
// that carries the address, and no fetch or XHR at all. The processor's
// answer is stood in for by page.route, so nothing leaves the machine.
//
// The analytics network log, Step 9's privacy test rerun with analytics on:
// a local build carries no tracker (production builds only), so the test
// loads the vendored tracker itself, the very file production serves, with
// the production tag's attributes but a same-origin collector the test
// records. A visitor runs a calculator with a value of their own, downloads
// the result, searches, picks a Pro tier and joins the waitlist; every
// payload the tracker sends then holds only allowlisted events and
// properties, no URL query or fragment, and none of the value, the query or
// the address.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { Page } from "@playwright/test";

import { TRACKER_PATH, TRACKER_SOURCE, trackerAttributes } from "@/lib/analytics";
import { checkEvent } from "@/lib/events";
import { SIGNUP_ACTION } from "@/lib/signup";

import { expect, test } from "./support.ts";

const ADDRESS = "growth-test-4f1c@example.org";
const TRACKER = readFileSync(fileURLToPath(new URL(`../../${TRACKER_SOURCE}`, import.meta.url)));
const WEBSITE_ID = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0";

interface Submission {
  method: string;
  contentType: string;
  fields: [string, string][];
}

/** Stand in for the processor: record each form post and answer a plain page. */
async function processor(page: Page): Promise<Submission[]> {
  const posts: Submission[] = [];
  await page.route(`${SIGNUP_ACTION}**`, async (route) => {
    const request = route.request();
    posts.push({
      method: request.method(),
      contentType: request.headers()["content-type"] ?? "",
      fields: [...new URLSearchParams(request.postData() ?? "")],
    });
    await route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>Confirm</title><p>Check your email.</p>" });
  });
  return posts;
}

const CASES = [
  { path: "/newsletter/", form: "#newsletter", list: "newsletter", source: "newsletter-page", tier: null },
  { path: "/", form: "#footer-signup", list: "newsletter", source: "footer", tier: null },
  { path: "/pro/", form: "#waitlist", list: "waitlist", source: "pro-page", tier: "commercial" },
] as const;

for (const entry of CASES) {
  test(`${entry.path}'s ${entry.list} form posts the address straight to the processor, and nothing else carries it`, async ({
    page,
    network,
    watch,
  }) => {
    const posts = await processor(page);
    await page.goto(entry.path);
    const form = page.locator(entry.form);
    await expect(form).toHaveAttribute("method", "post");
    await expect(form).toHaveAttribute("action", SIGNUP_ACTION);
    await form.getByLabel("Email address").fill(ADDRESS);
    if (entry.tier) await form.getByLabel("Commercial", { exact: true }).check();
    await form.getByRole("button", { name: entry.list === "waitlist" ? "Join the waitlist" : "Subscribe" }).click();
    await expect(page.getByText("Check your email.")).toBeVisible();

    expect(posts).toHaveLength(1);
    expect(posts[0]?.method).toBe("POST");
    expect(posts[0]?.contentType).toBe("application/x-www-form-urlencoded");
    expect(posts[0]?.fields).toEqual([
      ["email", ADDRESS],
      ["embed", "1"],
      ["metadata__list", entry.list],
      ["metadata__source", entry.source],
      ...(entry.tier ? [["metadata__tier", entry.tier]] : []),
    ]);
    // The address went out once, in the form's own navigation; no script sent it.
    const carrying = network.requests.filter((request) =>
      [request.url, request.body?.toString("utf8") ?? ""].some((part) => part.includes(ADDRESS) || part.includes(encodeURIComponent(ADDRESS))),
    );
    expect(carrying.map((request) => `${request.method} ${request.url}`)).toEqual([`POST ${SIGNUP_ACTION}`]);
    expect(watch.violations).toEqual([]);
    expect(watch.errors).toEqual([]);
  });
}

test("a Pro tier's 'Notify me' chooses that tier in the waitlist and records it on the submit", async ({ page, watch }) => {
  await page.goto("/pro/");
  await page.getByRole("link", { name: "Notify me about Team" }).click();
  const form = page.locator("#waitlist");
  await expect(form.getByLabel("Team", { exact: true })).toBeChecked();
  await expect(form.getByLabel("Email address")).toBeFocused();
  const submit = form.getByRole("button", { name: "Join the waitlist" });
  await expect(submit).toHaveAttribute("data-umami-event-tier", "team");
  await form.getByLabel("Personal", { exact: true }).check();
  await expect(submit).toHaveAttribute("data-umami-event-tier", "personal");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

interface Sent {
  type: string;
  payload: { name?: string; data?: Record<string, unknown>; url?: string; referrer?: string; website?: string; hostname?: string };
}

/** Load the vendored tracker as production's tag does, posting to a collector the test records. */
async function withTracker(page: Page): Promise<Sent[]> {
  const sent: Sent[] = [];
  await page.route(`**${TRACKER_PATH}`, (route) => route.fulfill({ status: 200, contentType: "text/javascript", body: TRACKER }));
  await page.route("**/__collector/api/send", async (route) => {
    sent.push(JSON.parse(route.request().postData() ?? "{}") as Sent);
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  await page.addInitScript(
    ({ attributes }) => {
      // Only on the site's own pages, never on the processor's stand-in.
      if (location.hostname !== "127.0.0.1") return;
      document.addEventListener("DOMContentLoaded", () => {
        const script = document.createElement("script");
        for (const [name, value] of Object.entries(attributes)) script.setAttribute(name, value);
        // This machine's host stands in for the production host the tag names.
        script.setAttribute("data-domains", location.hostname);
        script.setAttribute("data-host-url", `${location.origin}/__collector`);
        document.head.append(script);
      });
    },
    { attributes: trackerAttributes(WEBSITE_ID) },
  );
  return sent;
}

test("with analytics on, every request holds only allowlisted events: no input, value, query or address", async ({
  page,
  api,
  network,
  watch,
}) => {
  const sent = await withTracker(page);
  await processor(page);
  const value = "0.0612345";
  const query = "zqxv-private-query";

  // A calculator run with the visitor's own value, then a download.
  await page.goto("/models/fixed-income/duration/");
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
  await section.getByLabel("Coupon Rate", { exact: false }).first().fill(value);
  await section.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused();
  const download = page.waitForEvent("download");
  await section.getByRole("button", { name: "CSV", exact: true }).click();
  await download;
  await expect.poll(() => sent.filter((entry) => entry.payload.name === "download").length).toBe(1);

  // A search, with a query in the address.
  await page.goto(`/search/?q=${query}`);
  await expect(page.locator("[data-search-status]")).toContainText(query);
  await expect.poll(() => sent.filter((entry) => entry.payload.name === "search").length).toBe(1);

  // A Pro tier's click, then the waitlist with an address.
  await page.goto("/pro/#pro-prices");
  const here = new URL(page.url()).origin;
  await page.getByRole("link", { name: "Notify me about Commercial" }).click();
  await expect.poll(() => sent.filter((entry) => entry.payload.name === "pro_preview_click").length).toBe(1);
  await page.locator("#waitlist").getByLabel("Email address").fill(ADDRESS);
  await page.locator("#waitlist").getByRole("button", { name: "Join the waitlist" }).click();
  await expect(page.getByText("Check your email.")).toBeVisible();

  const names = sent.map((entry) => entry.payload.name ?? "(page view)");
  for (const expected of ["(page view)", "calculator_run", "download", "search", "pro_preview_click", "waitlist_submit"]) {
    expect(names, expected).toContain(expected);
  }
  for (const entry of sent) {
    expect(entry.type).toBe("event");
    expect(entry.payload.website).toBe(WEBSITE_ID);
    if (entry.payload.name !== undefined) {
      expect(checkEvent(entry.payload.name, entry.payload.data ?? {}), JSON.stringify(entry.payload)).not.toBeNull();
    } else {
      expect(entry.payload.data).toBeUndefined();
    }
    for (const field of [entry.payload.url, entry.payload.referrer]) {
      expect(field ?? "", JSON.stringify(entry.payload)).not.toMatch(/[?#]/);
    }
  }
  expect(sent.find((entry) => entry.payload.name === "calculator_run")?.payload.data).toEqual({ model: "fixed_income.duration" });
  expect(sent.find((entry) => entry.payload.name === "download")?.payload.data).toEqual({ model: "fixed_income.duration", format: "csv" });
  expect(sent.find((entry) => entry.payload.name === "pro_preview_click")?.payload.data).toEqual({ tier: "commercial" });
  expect(sent.find((entry) => entry.payload.name === "waitlist_submit")?.payload.data).toEqual({ list: "waitlist", tier: "commercial" });

  // Nothing the visitor typed or got back reached the collector.
  const everything = JSON.stringify(sent);
  for (const forbidden of [value, query, ADDRESS, encodeURIComponent(ADDRESS), "coupon_rate", "macaulay"]) {
    expect(everything, forbidden).not.toContain(forbidden);
  }
  // Every request went to this origin, the processor's stand-in or a blob of the browser's own.
  const elsewhere = network.requests
    .map((request) => request.url)
    .filter((url) => !url.startsWith(here) && !url.startsWith(SIGNUP_ACTION) && !url.startsWith("blob:"));
  expect(elsewhere).toEqual([]);
  expect(api.requests.length).toBeGreaterThan(0);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
