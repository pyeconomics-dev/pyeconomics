// web/src/lib/security-txt.ts
// /.well-known/security.txt (RFC 9116; ADR-0013 decision 20; Phase 5 Step 16):
// where to report a vulnerability, written by scripts/indexing.ts into every
// build that is served as a site (production, staging, local), and left out of
// the app wheel's build, which a user's own machine serves (decision 16) and
// whose wheel check refuses a hidden directory. Its fields are the ones below,
// and nowhere else: never put a security.txt in public/.
//
// Contact is GitHub's private vulnerability reporting, the route SECURITY.md
// names, and Policy is SECURITY.md itself. Expires is fixed here, under a year
// ahead as RFC 9116 section 2.5.5 recommends, and moved by hand: the unit test
// fails when fewer than 30 days remain (renewal: docs/operations/production.md
// section 13). Nothing is signed: the file is served only over HTTPS from the
// origin it names.

import { ORIGIN } from "./paths.ts";

/** Where security.txt is served. */
export const SECURITY_TXT_PATH = "/.well-known/security.txt";

/** GitHub's private vulnerability reporting: SECURITY.md's route. */
export const VULNERABILITY_REPORTING = "https://github.com/pyeconomics-dev/pyeconomics/security/advisories/new";

/** The security policy, SECURITY.md on main. */
export const SECURITY_POLICY = "https://github.com/pyeconomics-dev/pyeconomics/blob/main/SECURITY.md";

/**
 * When the file expires: under a year from its last renewal (2026-11-12).
 * Renew it at least 30 days before, by moving this date and nothing else.
 */
export const SECURITY_TXT_EXPIRES = "2027-11-01T00:00:00.000Z";

/**
 * Whether a build of `flavour` (SITE_FLAVOUR) carries security.txt: every
 * build but the app wheel's, which a user's own computer serves.
 */
export function carriesSecurityTxt(flavour: string | undefined = process.env.SITE_FLAVOUR): boolean {
  return flavour !== "app";
}

/** The days left before expiry below which the unit test fails. */
export const RENEWAL_DAYS = 30;

/** One field of the file, in the order it is written. */
export interface SecurityField {
  name: string;
  value: string;
}

/** The fields, in RFC 9116's order of importance. */
export const SECURITY_FIELDS: readonly SecurityField[] = [
  { name: "Contact", value: VULNERABILITY_REPORTING },
  { name: "Expires", value: SECURITY_TXT_EXPIRES },
  { name: "Policy", value: SECURITY_POLICY },
  { name: "Preferred-Languages", value: "en" },
  { name: "Canonical", value: `${ORIGIN}${SECURITY_TXT_PATH}` },
];

/** The file's text: a comment naming its source, then one field a line. */
export function securityTxt(fields: readonly SecurityField[] = SECURITY_FIELDS): string {
  const lines = [
    "# Report a vulnerability privately through GitHub; never in a public issue.",
    "# Written by web/scripts/indexing.ts from web/src/lib/security-txt.ts.",
    ...fields.map((field) => `${field.name}: ${field.value}`),
  ];
  return `${lines.join("\n")}\n`;
}

/** A parsed file: each field name, lower-cased, with its values in order. */
export type ParsedSecurityTxt = Map<string, string[]>;

/**
 * Parse a security.txt as RFC 9116 section 4 reads it: comments and blank
 * lines skipped, `Name: value` lines, names case-insensitive.
 *
 * Raises an Error for a line that is neither.
 */
export function parseSecurityTxt(text: string): ParsedSecurityTxt {
  const fields: ParsedSecurityTxt = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (line === "" || line.startsWith("#")) continue;
    const match = /^([A-Za-z0-9-]+): (.+)$/.exec(line);
    if (match === null) throw new Error(`security.txt: ${JSON.stringify(line)} is not a field`);
    const name = (match[1] ?? "").toLowerCase();
    fields.set(name, [...(fields.get(name) ?? []), match[2] ?? ""]);
  }
  return fields;
}

/**
 * What is wrong with a security.txt on `today`: RFC 9116's required fields
 * (one Expires at most, at least one Contact), every Contact and Policy URI
 * on https: (or mailto: for a Contact), an Expires in its ISO 8601 form that
 * is under a year ahead, and at least `RENEWAL_DAYS` days left.
 */
export function securityTxtProblems(text: string, today: Date): string[] {
  const problems: string[] = [];
  let fields: ParsedSecurityTxt;
  try {
    fields = parseSecurityTxt(text);
  } catch (error) {
    return [(error as Error).message];
  }
  const contacts = fields.get("contact") ?? [];
  if (contacts.length === 0) problems.push("no Contact field");
  for (const contact of contacts) {
    if (!/^(https:\/\/|mailto:)/.test(contact)) problems.push(`Contact ${contact} is not an https: or mailto: URI`);
  }
  for (const policy of fields.get("policy") ?? []) {
    if (!policy.startsWith("https://")) problems.push(`Policy ${policy} is not an https: URI`);
  }
  const expires = fields.get("expires") ?? [];
  if (expires.length !== 1) {
    problems.push(`${String(expires.length)} Expires fields; RFC 9116 requires exactly one`);
    return problems;
  }
  const value = expires[0] ?? "";
  const when = new Date(value);
  const iso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
  if (!iso || Number.isNaN(when.getTime())) {
    problems.push(`Expires ${value} is not an ISO 8601 date and time`);
    return problems;
  }
  const days = (when.getTime() - today.getTime()) / 86_400_000;
  if (days > 366) problems.push(`Expires ${value} is more than a year away`);
  if (days < RENEWAL_DAYS) {
    problems.push(
      `Expires ${value} is ${days < 0 ? "past" : `${String(Math.floor(days))} days away`}: renew it (web/src/lib/security-txt.ts)`,
    );
  }
  return problems;
}
