// web/tests/unit/legal.test.ts
// The legal and trust pages' sources (Phase 5 Step 16; ADR-0013 decision 20):
// - the data flows the privacy policy is generated from are complete: every
//   origin the Content Security Policy lets a page reach (connect-src,
//   form-action) belongs to a flow, every flow's origin is one the policy
//   allows, and every processor ADR-0013 and the step name is listed
//   (tests/web/test_data_flows.py holds the service's own hosts and logs);
// - security.txt carries RFC 9116's fields, names the private vulnerability
//   reporting route and SECURITY.md, expires under a year ahead, and fails
//   this test when fewer than 30 days remain;
// - the required-notices table is ROADMAP §5's, row for row;
// - the hypothetical-results legend follows the registry's tags, and every
//   model that names Monte Carlo or a backtest carries one of those tags;
// - the licence page lists every package of the production dependency tree.
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { ALLOWED, ALLOWED_PATTERNS, DIRECTIVES } from "../../csp.config.ts";
import {
  CFTC_STATEMENT,
  DATA_FLOWS,
  HYPOTHETICAL_LEGEND,
  REQUIRED_NOTICES,
  SIMULATED_TAGS,
  parseDataFlows,
  simulates,
  simulatesFutures,
} from "@/lib/legal";
import { BUILD_OUTPUT, licenceCounts, packageName, packageUrl, shippedLicences } from "@/lib/licences";
import {
  RENEWAL_DAYS,
  SECURITY_FIELDS,
  SECURITY_POLICY,
  VULNERABILITY_REPORTING,
  carriesSecurityTxt,
  parseSecurityTxt,
  securityTxt,
  securityTxtProblems,
} from "@/lib/security-txt";
import { parseModels } from "@/lib/registry-schema";
import { registryData } from "@/lib/site-data";

const MODELS = parseModels(registryData);

const KEYWORDS = new Set(["'self'", "'none'", "data:", "blob:"]);
const ROADMAP = join(process.cwd(), "..", "docs", "roadmap", "ROADMAP.md");

/** The directives that let a page reach another origin: their sources (allowed and this build's) and patterns. */
const REACHED: [string, readonly string[], readonly RegExp[]][] = [
  [
    "connect-src",
    [...(ALLOWED["connect-src"] ?? []), ...(DIRECTIVES["connect-src"] ?? [])],
    ALLOWED_PATTERNS["connect-src"] ?? [],
  ],
  [
    "form-action",
    [...(ALLOWED["form-action"] ?? []), ...(DIRECTIVES["form-action"] ?? [])],
    ALLOWED_PATTERNS["form-action"] ?? [],
  ],
];

/** Every origin some flow names, with a pattern's variable part filled in. */
function flowOrigins(): string[] {
  return DATA_FLOWS.flows.flatMap((flow) => flow.origins.map((origin) => origin.replace(/<[a-z]+>/g, "1234567")));
}

describe("the data flows", () => {
  it("name every origin the policy lets a page reach", () => {
    const named = new Set(flowOrigins());
    for (const [directive, sources, patterns] of REACHED) {
      for (const source of sources) {
        if (KEYWORDS.has(source)) continue;
        expect(named, `${directive} ${source} has no flow in data-flows.json`).toContain(source);
      }
      for (const pattern of patterns) {
        expect(
          [...named].some((origin) => pattern.test(origin)),
          `${directive} ${String(pattern)} has no flow in data-flows.json`,
        ).toBe(true);
      }
    }
  });

  it("name no origin the policy does not allow", () => {
    const allowed = new Set([...(ALLOWED["connect-src"] ?? []), ...(ALLOWED["form-action"] ?? [])]);
    const patterns = REACHED.flatMap(([, , found]) => found);
    for (const origin of flowOrigins()) {
      expect(allowed.has(origin) || patterns.some((pattern) => pattern.test(origin)), origin).toBe(true);
    }
  });

  it("list every processor ADR-0013 and the step name", () => {
    const names = DATA_FLOWS.processors.map((processor) => processor.name).join("\n");
    for (const vendor of [
      "Cloudflare",
      "Google Cloud",
      "Upstash",
      "Umami",
      "Buttondown",
      "Sentry",
      "Grafana",
      "Better Stack",
      "GitHub",
      "Read the Docs",
    ]) {
      expect(names, vendor).toContain(vendor);
    }
  });

  it("say that request logs are excluded and that the calculator posts its inputs", () => {
    const text = JSON.stringify(DATA_FLOWS);
    expect(text).toContain("request logs");
    expect(text).toContain("excluded");
    expect(text).toContain("POST");
  });

  it("refuse a flow naming an unlisted processor, a repeated flow and an idle processor", () => {
    const document = structuredClone(DATA_FLOWS) as unknown as { flows: { id: string; processor: string | null }[] };
    const first = document.flows[0];
    if (first) document.flows.push({ ...first }, { ...first, id: "other", processor: "nobody" });
    expect(() => parseDataFlows(document)).toThrow(/listed twice[\s\S]*names no listed processor nobody/);
    const idle = structuredClone(DATA_FLOWS);
    const [processor] = idle.processors;
    if (processor) idle.processors.push({ ...processor, id: "idle" });
    expect(() => parseDataFlows(idle)).toThrow(/processor idle handles no flow/);
  });
});

describe("security.txt", () => {
  const text = securityTxt();
  const fields = parseSecurityTxt(text);

  it("carries RFC 9116's fields: the private reporting route, SECURITY.md, and the canonical address", () => {
    expect(fields.get("contact")).toEqual([VULNERABILITY_REPORTING]);
    expect(fields.get("policy")).toEqual([SECURITY_POLICY]);
    expect(SECURITY_POLICY.endsWith("/SECURITY.md")).toBe(true);
    expect(fields.get("canonical")).toEqual(["https://pyeconomics.dev/.well-known/security.txt"]);
    expect(fields.get("preferred-languages")).toEqual(["en"]);
    expect(SECURITY_FIELDS.map((field) => field.name)).toContain("Expires");
  });

  it(`expires under a year from now, with at least ${String(RENEWAL_DAYS)} days left: renew it if this fails`, () => {
    expect(securityTxtProblems(text, new Date())).toEqual([]);
  });

  it("names what is wrong with a bad file", () => {
    const today = new Date("2026-11-12T00:00:00Z");
    expect(securityTxtProblems("Expires: 2027-01-01T00:00:00Z\n", today)).toEqual(["no Contact field"]);
    expect(securityTxtProblems("Contact: http://x\nExpires: 2027-01-01T00:00:00Z\n", today)).toEqual([
      "Contact http://x is not an https: or mailto: URI",
    ]);
    expect(securityTxtProblems("Contact: mailto:a@b.c\nExpires: 2028-01-01T00:00:00Z\n", today)).toEqual([
      "Expires 2028-01-01T00:00:00Z is more than a year away",
    ]);
    expect(securityTxtProblems("Contact: mailto:a@b.c\nExpires: 2026-11-20T00:00:00Z\n", today)).toEqual([
      "Expires 2026-11-20T00:00:00Z is 8 days away: renew it (web/src/lib/security-txt.ts)",
    ]);
    expect(securityTxtProblems("Contact: mailto:a@b.c\nExpires: 2026-11-01T00:00:00Z\n", today)[0]).toMatch(/is past/);
    expect(securityTxtProblems("Contact: mailto:a@b.c\n", today)).toEqual([
      "0 Expires fields; RFC 9116 requires exactly one",
    ]);
    expect(securityTxtProblems("Contact: mailto:a@b.c\nExpires: soon\n", today)).toEqual([
      "Expires soon is not an ISO 8601 date and time",
    ]);
    expect(securityTxtProblems("not a field\n", today)[0]).toMatch(/is not a field/);
  });

  it("is written into every build but the app wheel's", () => {
    expect(carriesSecurityTxt(undefined)).toBe(true);
    expect(carriesSecurityTxt("production")).toBe(true);
    expect(carriesSecurityTxt("staging")).toBe(true);
    expect(carriesSecurityTxt("app")).toBe(false);
  });
});

describe("the required notices", () => {
  it("are ROADMAP §5's table, row for row", () => {
    const roadmap = readFileSync(ROADMAP, "utf8").replaceAll("\r\n", "\n");
    const section = roadmap.split("#### Required notices")[1]?.split("\n####")[0] ?? "";
    const rows = section
      .split("\n")
      .filter((line) => line.startsWith("|") && !/^\|[-\s|]+\|$/.test(line))
      .slice(1)
      .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));
    expect(rows.map(([source, notice]) => ({ source, notice }))).toEqual([...REQUIRED_NOTICES]);
  });
});

describe("the hypothetical-results legend", () => {
  it("is FINRA Rule 2214's legend made the model's, and the CFTC's statement for futures", () => {
    expect(HYPOTHETICAL_LEGEND).toMatch(/^IMPORTANT: The projections or other information generated by /);
    expect(CFTC_STATEMENT).toMatch(
      /^These results are based on simulated or hypothetical performance results that have certain inherent limitations\./,
    );
  });

  it("follows the registry's tags, and marks the Monte Carlo, historical-simulation and backtest families", () => {
    const marked = MODELS.filter(simulates).map((model) => model.id);
    expect(marked).toEqual(
      MODELS.filter((model) => model.tags.some((tag) => SIMULATED_TAGS.includes(tag))).map((model) => model.id),
    );
    for (const model of MODELS) {
      const named = /monte carlo|backtest|historical simulation/i.test(`${model.title} ${model.summary}`);
      if (named) expect(simulates(model), `${model.id} names a simulation but has no simulated tag`).toBe(true);
    }
    expect(marked).toEqual(expect.arrayContaining(["foundations.simulation", "risk.value_at_risk", "risk.var_backtest"]));
  });

  it("adds the CFTC statement only to a simulated model tagged with futures", () => {
    expect(simulatesFutures({ tags: ["monte carlo", "futures"] })).toBe(true);
    expect(simulatesFutures({ tags: ["futures"] })).toBe(false);
    expect(simulatesFutures({ tags: ["monte carlo"] })).toBe(false);
  });
});

describe("the licence page's packages", () => {
  const lock = JSON.parse(readFileSync(join(process.cwd(), "package-lock.json"), "utf8")) as {
    packages: Record<string, { dev?: boolean; link?: boolean; version?: string }>;
  };
  const shipped = shippedLicences();

  it("are every package of the production tree and the build output, each with its licence text", () => {
    const production = Object.entries(lock.packages)
      .filter(([path, entry]) => path !== "" && entry.dev !== true && entry.link !== true)
      .map(([path, entry]) => `${packageName(path)}@${entry.version ?? ""}`);
    const listed = shipped.map((entry) => `${entry.name}@${entry.version}`);
    expect(listed).toEqual(expect.arrayContaining(production));
    for (const name of BUILD_OUTPUT) expect(shipped.some((entry) => entry.name === name)).toBe(true);
    // A package that ships no licence file (or a platform binary another
    // platform installs) is listed with the licence its metadata declares.
    for (const entry of shipped.filter((item) => item.text === null)) expect(entry.licence, entry.name).not.toBe("");
    expect(shipped.find((entry) => entry.name === "pagefind")?.text).toMatch(/^LICENSE\n\n[\s\S]*MIT/);
    expect(shipped.filter((entry) => entry.text !== null).length).toBeGreaterThan(shipped.length * 0.9);
    expect(licenceCounts(shipped).reduce((sum, [, count]) => sum + count, 0)).toBe(shipped.length);
  });

  it("add the vendored tracker only to a build that serves it", () => {
    expect(shipped.some((entry) => entry.name.startsWith("umami"))).toBe(false);
    const withTracker = shippedLicences(process.cwd(), true).find((entry) => entry.name.startsWith("umami"));
    expect(withTracker?.licence).toBe("MIT");
    expect(withTracker?.text).toMatch(/MIT License|Permission is hereby granted/);
  });

  it("link a package's source only on https", () => {
    expect(packageUrl({ repository: { url: "git+https://github.com/a/b.git" } })).toBe("https://github.com/a/b");
    expect(packageUrl({ repository: "github:a/b" })).toBe("https://github.com/a/b");
    expect(packageUrl({ repository: "a/b" })).toBe("https://github.com/a/b");
    expect(packageUrl({ homepage: "javascript:alert(1)" })).toBeNull();
    expect(packageUrl({})).toBeNull();
  });
});
