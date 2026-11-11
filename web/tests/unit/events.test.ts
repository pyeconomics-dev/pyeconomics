// web/tests/unit/events.test.ts
// The analytics allowlist (Phase 5 Step 15; ADR-0013 decision 13): exactly
// six events, each with its own properties, every property value from a
// closed set or a model id's pattern, so no event can carry an input, a
// value, a search query, an email address or a result. track() sends only
// what passes, and never breaks an island.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EVENTS, FORMATS, LISTS, PROPERTIES, TIERS, checkEvent, eventAttributes, track, trackOnce } from "@/lib/events";
import { RUN_FORMATS } from "@/lib/run-request";
import { SERIES_FORMATS } from "@/lib/explorer";
import { registryData } from "@/lib/site-data";

/** What a visitor could type or a run could return: none may ever be sent. */
const FORBIDDEN_VALUES = [
  "someone@example.com",
  "0.05",
  "1000",
  "bond pricing",
  "?q=garch",
  "https://pyeconomics.dev/search/?q=x",
  '{"rate":0.05}',
  "61.391325354075946",
  "",
  "fixed_income.bond_pricing ",
  "Fixed_Income.Bond_Pricing",
  "<script>",
];

describe("the allowlist", () => {
  it("names exactly the six events of the step, with their properties", () => {
    expect(EVENTS).toEqual({
      calculator_run: ["model"],
      download: ["model", "format"],
      pro_preview_click: ["tier"],
      newsletter_submit: ["list"],
      waitlist_submit: ["list", "tier"],
      search: [],
    });
    expect(Object.keys(PROPERTIES).sort()).toEqual(["format", "list", "model", "tier"]);
    expect(TIERS).toEqual(["personal", "commercial", "team"]);
    expect(LISTS).toEqual(["newsletter", "waitlist"]);
  });

  it("knows every download format the calculators and the explorer offer, and no other", () => {
    expect(new Set(FORMATS)).toEqual(new Set([...RUN_FORMATS, ...SERIES_FORMATS]));
  });

  it("accepts every model id the registry holds", () => {
    for (const model of registryData.models) {
      expect(checkEvent("calculator_run", { model: model.id }), model.id).toEqual({ model: model.id });
    }
  });

  it("accepts each event with allowed values, and a subset of its properties", () => {
    expect(checkEvent("download", { model: "fixed_income.bond_pricing", format: "csv" })).toEqual({
      model: "fixed_income.bond_pricing",
      format: "csv",
    });
    expect(checkEvent("download", { format: "parquet" })).toEqual({ format: "parquet" });
    expect(checkEvent("pro_preview_click", { tier: "team" })).toEqual({ tier: "team" });
    expect(checkEvent("waitlist_submit", { list: "waitlist", tier: "commercial" })).toEqual({ list: "waitlist", tier: "commercial" });
    expect(checkEvent("newsletter_submit", { list: "newsletter" })).toEqual({ list: "newsletter" });
    expect(checkEvent("search")).toEqual({});
  });

  it("refuses an event it does not list, or one named after an object's own keys", () => {
    for (const name of ["pageview", "identify", "signup", "constructor", "__proto__", "toString", "hasOwnProperty"]) {
      expect(checkEvent(name, {}), name).toBeNull();
    }
  });

  it("refuses a property the event does not carry, even one another event does", () => {
    expect(checkEvent("search", { query: "garch" })).toBeNull();
    expect(checkEvent("search", { model: "macro.policy_rule" })).toBeNull();
    expect(checkEvent("calculator_run", { model: "macro.policy_rule", inputs: "{}" })).toBeNull();
    expect(checkEvent("newsletter_submit", { list: "newsletter", email: "someone@example.com" })).toBeNull();
    expect(checkEvent("pro_preview_click", { tier: "team", value: "149" })).toBeNull();
  });

  it("refuses any value that is not one of the property's own", () => {
    for (const [name, properties] of Object.entries(EVENTS)) {
      for (const property of properties) {
        for (const value of FORBIDDEN_VALUES) {
          expect(checkEvent(name, { [property]: value }), `${name}.${property}=${value}`).toBeNull();
        }
      }
    }
  });

  it("refuses a value that is not a string", () => {
    for (const value of [5, 0.05, true, null, ["csv"], { format: "csv" }]) {
      expect(checkEvent("download", { format: value }), JSON.stringify(value)).toBeNull();
    }
  });
});

describe("track", () => {
  const calls: unknown[][] = [];

  beforeEach(() => {
    calls.length = 0;
    vi.stubGlobal("window", { umami: { track: (...args: unknown[]) => calls.push(args) } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hands an allowed event to the tracker, with no data for an event without properties", () => {
    expect(track("download", { model: "foundations.time_value", format: "xlsx" })).toBe(true);
    expect(track("search")).toBe(true);
    expect(calls).toEqual([["download", { model: "foundations.time_value", format: "xlsx" }], ["search", undefined]]);
  });

  it("sends nothing for an event the allowlist refuses", () => {
    expect(track("download", { format: "pdf" })).toBe(false);
    expect(track("search", { query: "garch" })).toBe(false);
    expect(track("newsletter_submit", { list: "newsletter", email: "someone@example.com" })).toBe(false);
    expect(calls).toEqual([]);
  });

  it("does nothing without the tracker, and survives one that throws", () => {
    vi.stubGlobal("window", {});
    expect(track("search")).toBe(false);
    vi.stubGlobal("window", {
      umami: {
        track: () => {
          throw new Error("blocked");
        },
      },
    });
    expect(track("search")).toBe(false);
  });

  it("sends the first search of a page view only", () => {
    expect(trackOnce("search")).toBe(true);
    expect(trackOnce("search")).toBe(false);
    expect(calls).toEqual([["search", undefined]]);
  });
});

describe("eventAttributes", () => {
  it("writes the attributes Umami's tracker reads from a clicked element", () => {
    expect(eventAttributes("pro_preview_click", { tier: "personal" })).toEqual({
      "data-umami-event": "pro_preview_click",
      "data-umami-event-tier": "personal",
    });
    expect(eventAttributes("newsletter_submit", { list: "newsletter" })).toEqual({
      "data-umami-event": "newsletter_submit",
      "data-umami-event-list": "newsletter",
    });
  });

  it("refuses, at build time, an event the allowlist refuses", () => {
    expect(() => eventAttributes("pro_preview_click", { tier: "enterprise" })).toThrow(/allowlist refuses/);
    expect(() => eventAttributes("newsletter_submit", { email: "someone@example.com" })).toThrow(/allowlist refuses/);
  });
});
