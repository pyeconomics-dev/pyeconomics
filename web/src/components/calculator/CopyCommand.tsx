// web/src/components/calculator/CopyCommand.tsx
// A command a visitor may copy (issue #320): the command as text, which can be
// selected as it is, and the site's copy button (CopyButton.tsx), which says
// what happened: copied, or, where the browser refuses the clipboard, that the
// text can be selected instead.
import CopyButton from "@/components/calculator/CopyButton";

export default function CopyCommand({ command }: { command: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2" data-command={command}>
      <code className="max-w-full rounded-md border bg-muted px-2 py-1 text-xs break-all">{command}</code>
      <CopyButton text={command} label="Copy" ariaLabel={`Copy the command ${command}`} size="xs" />
    </div>
  );
}
