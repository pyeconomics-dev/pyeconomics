// web/src/lib/events.ts
// The site's analytics events (Phase 5 Step 15; ADR-0013 decision 13): the
// one allowlist of custom event names and the properties each may carry, and
// the only code that hands an event to the tracker. A property is a model id,
// a download format, a Pro tier or a sign-up list, each checked against its
// own closed set or pattern, so no event can carry an input, a value, a search
// query, an email address or a result. An event or property outside the
// allowlist is dropped, never sent.
//
// Islands call track(); a static element that records a click (a form's
// submit button, the Pro page's "notify me" links) carries the attributes
// eventAttributes() writes, which Umami's tracker reads itself, so a page
// needs no script for them. Both pass the same check. Without the tracker
// (every build but production's: decisions 13 and 16) track() does nothing.

/** A property's closed set of values, or the pattern its values match. */
type Rule = readonly string[] | RegExp;

/** A model id: `<domain>.<name>`, lower snake case (ADR-0003). */
export const MODEL_ID = /^[a-z][a-z0-9_]{0,40}\.[a-z][a-z0-9_]{0,60}$/;

/** Every download format the calculators and the explorer offer. */
export const FORMATS = ["json", "csv", "xlsx", "parquet", "arrow", "bundle"] as const;

/** The Pro preview's tiers (ROADMAP §5; ADR-0013 decision 19). */
export const TIERS = ["personal", "commercial", "team"] as const;
export type Tier = (typeof TIERS)[number];

/** The two lists the email processor keeps (decision 14). */
export const LISTS = ["newsletter", "waitlist"] as const;
export type List = (typeof LISTS)[number];

/** Each property the allowlist knows, and what its values may be. */
export const PROPERTIES: Readonly<Record<string, Rule>> = {
  model: MODEL_ID,
  format: FORMATS,
  tier: TIERS,
  list: LISTS,
};

/**
 * The allowlist: each custom event and the properties it may carry. `search`
 * carries none: never the query.
 */
export const EVENTS = {
  calculator_run: ["model"],
  download: ["model", "format"],
  pro_preview_click: ["tier"],
  newsletter_submit: ["list"],
  waitlist_submit: ["list", "tier"],
  search: [],
} as const satisfies Readonly<Record<string, readonly (keyof typeof PROPERTIES)[]>>;

export type EventName = keyof typeof EVENTS;
export type EventProperties = Readonly<Record<string, string>>;

const RULES = new Map(Object.entries(PROPERTIES));

function allowedValue(rule: Rule, value: string): boolean {
  return Array.isArray(rule) ? rule.includes(value) : (rule as RegExp).test(value);
}

/**
 * The event's properties if every one is allowed for it, else null. A
 * property that is not a string, not on the event's list or not one of its
 * rule's values makes the whole event invalid, so nothing is sent partly.
 */
export function checkEvent(name: string, properties: Readonly<Record<string, unknown>> = {}): EventProperties | null {
  if (!Object.hasOwn(EVENTS, name)) return null;
  const allowed: readonly string[] = EVENTS[name as EventName];
  const checked = new Map<string, string>();
  for (const [key, value] of Object.entries(properties)) {
    const rule = RULES.get(key);
    if (!allowed.includes(key) || rule === undefined || typeof value !== "string" || !allowedValue(rule, value)) {
      return null;
    }
    checked.set(key, value);
  }
  return Object.fromEntries(checked);
}

/** Umami's tracker, when the page loaded it. */
interface Tracker {
  track: (name: string, data?: EventProperties) => unknown;
}

function tracker(): Tracker | undefined {
  if (typeof window === "undefined") return undefined;
  const found = (window as unknown as { umami?: Partial<Tracker> }).umami;
  return typeof found?.track === "function" ? (found as Tracker) : undefined;
}

/**
 * Hand one allowlisted event to the tracker. Returns whether it was sent; a
 * page without the tracker, an event the allowlist refuses or a tracker that
 * throws sends nothing and never breaks the island.
 */
export function track(name: EventName, properties: Readonly<Record<string, string>> = {}): boolean {
  const checked = checkEvent(name, properties);
  const found = tracker();
  if (checked === null || found === undefined) return false;
  try {
    void found.track(name, Object.keys(checked).length > 0 ? checked : undefined);
    return true;
  } catch {
    return false;
  }
}

const once = new Set<string>();

/** track(), at most once per page view: the first search, not every keystroke. */
export function trackOnce(name: EventName, properties: Readonly<Record<string, string>> = {}): boolean {
  if (once.has(name)) return false;
  const sent = track(name, properties);
  if (sent) once.add(name);
  return sent;
}

/**
 * The attributes Umami's tracker reads from an element to record a click on
 * it (`data-umami-event` and one `data-umami-event-<property>` each). Throws
 * at build time on an event the allowlist refuses, so no page can ship one.
 */
export function eventAttributes(name: EventName, properties: Readonly<Record<string, string>> = {}): Record<string, string> {
  const checked = checkEvent(name, properties);
  if (checked === null) throw new Error(`the analytics allowlist refuses ${name} ${JSON.stringify(properties)}`);
  const attributes: Record<string, string> = { "data-umami-event": name };
  for (const [key, value] of Object.entries(checked)) attributes[`data-umami-event-${key}`] = value;
  return attributes;
}
