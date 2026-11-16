// web/src/components/calculator/CopyCommand.tsx
// A command a visitor may copy (issue #320): the command as text, which can be
// selected as it is, and a button that copies it and says what happened, to
// everyone, screen readers included, for two seconds: copied, or, where the
// browser refuses the clipboard, that the text can be selected instead.
import { useEffect, useState } from "react";

import { buttonVariants } from "@/components/ui/button";

type Copy = "idle" | "copied" | "failed";

export default function CopyCommand({ command }: { command: string }) {
  const [state, setState] = useState<Copy>("idle");

  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 2000);
    return () => clearTimeout(timer);
  }, [state]);

  const copy = () => {
    navigator.clipboard.writeText(command).then(
      () => setState("copied"),
      () => setState("failed"),
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-2" data-command={command}>
      <code className="max-w-full rounded-md border bg-muted px-2 py-1 text-xs break-all">{command}</code>
      <button
        type="button"
        className={buttonVariants({ variant: "outline", size: "xs" })}
        aria-label={`Copy the command ${command}`}
        onClick={copy}
      >
        {state === "copied" ? "Copied" : "Copy"}
      </button>
      <span role="status" className="text-xs">
        {state === "copied" ? <span className="sr-only">Copied to the clipboard.</span> : null}
        {state === "failed" ? "The browser would not copy it: select the command and copy it." : null}
      </span>
    </div>
  );
}
