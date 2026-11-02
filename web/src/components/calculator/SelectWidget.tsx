// web/src/components/calculator/SelectWidget.tsx
// The calculator's dropdown: a native <select> in the shadcn/ui look, in place
// of the theme's command-palette select, so every option list (an enum field,
// a nullable field's two options and a family's calculation selector) works
// with the keyboard and a screen reader as browsers make it work. RJSF core's
// own SelectWidget, with the site's classes and without multiple selection,
// which no model's schema asks for. RJSF renders a oneOf's or an anyOf's
// option selector with no field template around it, so the widget labels
// those itself: a family's calculation selector with a visible label, a
// nullable field's (whose field label is already shown) with its name.
import {
  ariaDescribedByIds,
  enumOptionSelectedValue,
  enumOptionValueDecoder,
  enumOptionValueEncoder,
  getOptionValueFormat,
  type WidgetProps,
} from "@rjsf/utils";

const SELECT =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50 " +
  "aria-invalid:border-destructive";

export default function SelectWidget({
  schema,
  id,
  options,
  value,
  required,
  disabled,
  readonly,
  placeholder,
  htmlName,
  name,
  label,
  rawErrors,
  onChange,
  onBlur,
  onFocus,
}: WidgetProps) {
  const { enumOptions, enumDisabled, emptyValue } = options;
  const format = getOptionValueFormat(options);
  const decode = (text: string) => enumOptionValueDecoder(text, enumOptions, format, emptyValue);
  const selected = enumOptionSelectedValue(value, enumOptions, false, format, "");
  const calculation = name.endsWith("__oneof_select");
  const nullable = name.endsWith("__anyof_select");
  const select = (
    <select
      id={id}
      name={htmlName ?? id}
      className={SELECT}
      value={typeof selected === "string" ? selected : ""}
      required={required}
      disabled={disabled || readonly}
      aria-invalid={rawErrors && rawErrors.length > 0 ? true : undefined}
      aria-describedby={ariaDescribedByIds(id)}
      aria-label={nullable ? label : undefined}
      onChange={(event) => onChange(decode(event.target.value))}
      onBlur={(event) => onBlur(id, decode(event.target.value))}
      onFocus={(event) => onFocus(id, decode(event.target.value))}
    >
      {schema.default === undefined && <option value="">{placeholder ?? ""}</option>}
      {enumOptions?.map(({ value: option, label }, index) => (
        <option
          key={String(option)}
          value={enumOptionValueEncoder(option, index, format)}
          disabled={enumDisabled?.includes(option)}
        >
          {label}
        </option>
      ))}
    </select>
  );
  if (!calculation) return select;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {select}
    </div>
  );
}
