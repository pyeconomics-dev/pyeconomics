// web/src/lib/profiles.ts
// A data profile's name as a reader's words (Phase 5 Step 18's round 2: the
// live-data notice and the profile picker listed `us_sep`, `ea` and `gb`). A
// profile is one set of bindings a model declares: the same model on another
// country's series, or on another source's. Its id is what the API, the
// command line and `pyeconomics.bind` take, so the id stays beside a name that
// does not spell it. Pure: the model page and the calculator both read it.

/**
 * The names of profiles whose ids are codes: a country or an area, a factor
 * set, a source. Every other profile is its id written as words.
 * tests/unit/models.test.ts fails on a name here that no model's bindings use.
 */
export const PROFILE_NAMES: ReadonlyMap<string, string> = new Map(
  Object.entries({
    ca: "Canada",
    de: "Germany",
    ea: "Euro area",
    ff5: "Fama-French five factors",
    fr: "France",
    gb: "United Kingdom",
    it: "Italy",
    jp: "Japan",
    us_cpi: "US CPI inflation",
    us_output_gap: "US output gap",
    us_sep: "US FOMC projections",
    us_spf: "US forecasters' survey",
  }),
);

/** The countries and areas a concept's id begins with. */
export const REGIONS: ReadonlyMap<string, string> = new Map(
  Object.entries({
    ca: "Canada",
    de: "Germany",
    ea: "Euro area",
    fr: "France",
    gb: "United Kingdom",
    it: "Italy",
    jp: "Japan",
    us: "United States",
  }),
);

/**
 * The one country or area a profile's series belong to, read from their
 * concepts' ids (`us.inflation.cpi.yoy` is the United States'), or null where
 * they span several or name none.
 */
export function profileRegion(concepts: readonly string[]): string | null {
  const found = new Set(concepts.map((id) => REGIONS.get(id.split(".").at(0) ?? "") ?? ""));
  const [only = ""] = found;
  return found.size === 1 && only !== "" ? only : null;
}

/** A profile's name alone: "Euro area" for `ea`, "Default" for `default`. */
export function profileName(id: string): string {
  const words = PROFILE_NAMES.get(id) ?? id.replaceAll("_", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * A profile as a page names it: its name, with its id beside a name that does
 * not spell it ("Euro area (ea)"). A profile whose name says nothing of where
 * its data is from says so when its series are one country's: "Default (United
 * States data)" (round 3: nothing said that the default profile reads US data).
 */
export function profileLabel(id: string, region: string | null = null): string {
  const name = profileName(id);
  const plain = (text: string) => text.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (region !== null && !PROFILE_NAMES.has(id)) return `${name} (${region} data)`;
  return plain(name) === plain(id) ? name : `${name} (${id})`;
}
