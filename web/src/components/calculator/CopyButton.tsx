// web/src/components/calculator/CopyButton.tsx
// The one copy control (Phase 5 Step 18: round 0 found a copy that failed
// without a word). It copies its text and says what happened, to everyone,
// screen readers included, for a few seconds: copied, or, where the browser
// refuses the clipboard, that the text can be selected instead. Every island
// that copies uses it, and tests/e2e/copy.spec.ts refuses the clipboard on
// each to see the message.
import { useEffect, useState } from "react";

import { buttonVariants } from "@/components/ui/button";

type Copy = "idle" | "copied" | "failed";

/** How long the outcome stays on screen, in milliseconds. */
const SHOWN_FOR = 4000;

export interface CopyButtonProps {
  /** What is copied, read when the button is pressed. */
  text: string | (() => string);
  /** The button's words, such as "Copy" or "Copy JSON". */
  label: string;
  /** A longer name for a button whose label alone does not say what it copies. */
  ariaLabel?: string;
  size?: "xs" | "sm";
}

export default function CopyButton({ text, label, ariaLabel, size = "sm" }: CopyButtonProps) {
  const [state, setState] = useState<Copy>("idle");

  useEffect(() => {
    if (state === "idle") return undefined;
    const timer = setTimeout(() => setState("idle"), SHOWN_FOR);
    return () => clearTimeout(timer);
  }, [state]);

  const copy = () => {
    const value = typeof text === "function" ? text() : text;
    // A browser without the clipboard API (an insecure origin) refuses too.
    const written: Promise<void> =
      typeof navigator.clipboard?.writeText === "function"
        ? navigator.clipboard.writeText(value)
        : Promise.reject(new Error("no clipboard"));
    written.then(
      () => setState("copied"),
      () => setState("failed"),
    );
  };

  return (
    <span className="inline-flex flex-wrap items-center gap-2" data-copy={state}>
      <button type="button" className={buttonVariants({ variant: "outline", size })} aria-label={ariaLabel} onClick={copy}>
        {state === "copied" ? "Copied" : label}
      </button>
      {/* A live region without the status role: a form's one status line stays the only one. */}
      <span aria-live="polite" className="text-xs" data-copy-message="">
        {state === "copied" ? <span className="sr-only">Copied to the clipboard.</span> : null}
        {state === "failed" ? "The browser would not copy it: select the text and copy it." : null}
      </span>
    </span>
  );
}
