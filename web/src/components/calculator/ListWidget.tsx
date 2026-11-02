// web/src/components/calculator/ListWidget.tsx
// The calculator's widget for an array input (src/lib/lists.ts): one text box
// that holds the whole list or matrix, read back into an array on every
// change. Its text is kept while the user types, so "1, 2," is not rewritten,
// and replaced only when the form's value changes from outside (an example).
import { ariaDescribedByIds, type WidgetProps } from "@rjsf/utils";
import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import { formatList, listHint, listShape, parseList } from "@/lib/lists";

const BOX =
  "min-h-24 w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-xs " +
  "outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 " +
  "aria-invalid:border-destructive disabled:opacity-50";

export default function ListWidget({ id, htmlName, value, schema, required, disabled, readonly, rawErrors, onChange, onBlur, onFocus }: WidgetProps) {
  const shape = useMemo(() => listShape(schema as Record<string, unknown>), [schema]);
  const [text, setText] = useState(() => formatList(value, shape));
  const sent = useRef<unknown>(value);

  useEffect(() => {
    if (value !== sent.current) {
      sent.current = value;
      setText(formatList(value, shape));
    }
  }, [value, shape]);

  const change = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
    const parsed = parseList(event.target.value, shape);
    sent.current = parsed;
    onChange(parsed);
  };
  const rows = Math.min(8, Math.max(2, text.split("\n").length));
  const hint = `${id}__list-hint`;

  return (
    <div className="flex flex-col gap-1">
      <textarea
        id={id}
        name={htmlName ?? id}
        className={BOX}
        value={text}
        rows={rows}
        required={required}
        disabled={disabled}
        readOnly={readonly}
        spellCheck={false}
        aria-invalid={rawErrors && rawErrors.length > 0 ? true : undefined}
        aria-describedby={`${ariaDescribedByIds(id)} ${hint}`}
        onChange={change}
        onBlur={(event) => onBlur(id, event.target.value)}
        onFocus={(event) => onFocus(id, event.target.value)}
      />
      <p id={hint} className="text-xs text-muted-foreground">
        {listHint(shape)}
      </p>
    </div>
  );
}
