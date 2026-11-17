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

/** A profile's name alone: "Euro area" for `ea`, "Default" for `default`. */
export function profileName(id: string): string {
  const words = PROFILE_NAMES.get(id) ?? id.replaceAll("_", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** A profile as a page names it: its name, with its id beside a name that does not spell it ("Euro area (ea)"). */
export function profileLabel(id: string): string {
  const name = profileName(id);
  const plain = (text: string) => text.toLowerCase().replace(/[^a-z0-9]/g, "");
  return plain(name) === plain(id) ? name : `${name} (${id})`;
}
