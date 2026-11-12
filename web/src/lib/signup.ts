// web/src/lib/signup.ts
// The newsletter and Pro waitlist forms (Phase 5 Step 15; ADR-0013 decision
// 14): plain HTML forms that post, by navigation and never by fetch, straight
// to the email processor's embed endpoint, with no key. The processor
// confirms every address by email (double opt-in) before it counts. No
// address reaches our API, Worker, logs or analytics: the forms' only
// recorded event is the submit, with its list and tier.
//
// The app wheel's build carries no form (csp.config.ts signupForms): its pages
// link to the public site's /newsletter/ and /pro/ instead.
import { EMAIL_PROCESSOR, FORMS } from "../../csp.config.ts";
import type { List, Tier } from "@/lib/events";

/** The processor account's username, which names its public form endpoint. */
export const PROCESSOR_USERNAME = "pyeconomics";

/** Where every sign-up form posts. */
export const SIGNUP_ACTION = `${EMAIL_PROCESSOR}/api/emails/embed-subscribe/${PROCESSOR_USERNAME}`;

/** The processor that holds the addresses, as the forms name it. */
export const PROCESSOR_NAME = "Buttondown";

/** Where a sign-up came from: a fixed slug, never a URL. */
export const SOURCES = ["footer", "newsletter-page", "pro-page"] as const;
export type Source = (typeof SOURCES)[number];

/** Every field a sign-up form sends, beside the address. */
export const HIDDEN_FIELDS = ["embed", "metadata__list", "metadata__source"] as const;

/** The waitlist's tier field (a choice the visitor makes). */
export const TIER_FIELD = "metadata__tier";

/** The privacy policy every form links (Phase 5 Step 16 writes it). */
export const PRIVACY_POLICY = "/legal/privacy/";

/** The public site's pages, which the app wheel's build links to. */
export const PUBLIC_NEWSLETTER = "https://pyeconomics.dev/newsletter/";
export const PUBLIC_PRO = "https://pyeconomics.dev/pro/";

/** The labels the Pro preview gives each tier. */
const TIER_LABELS: ReadonlyMap<Tier, string> = new Map([
  ["personal", "Personal"],
  ["commercial", "Commercial"],
  ["team", "Team"],
]);

/** A tier's label. */
export function tierLabel(tier: Tier): string {
  return TIER_LABELS.get(tier) ?? tier;
}

/** A form's hidden fields, in order. */
export function hiddenFields(list: List, source: Source): readonly (readonly [string, string])[] {
  return [
    ["embed", "1"],
    ["metadata__list", list],
    ["metadata__source", source],
  ];
}

/** Whether this build carries the forms (every build but the app wheel's). */
export const FORMS_ENABLED = FORMS;
