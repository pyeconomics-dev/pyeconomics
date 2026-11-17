// web/src/components/calculator/FieldError.tsx
// A field's errors under it, in the form's own type size (Phase 5 Step 18's
// round 3: the theme's were set smaller than the text around them, and a red
// label was the only strong cue). The element keeps the id RJSF's fields name
// in aria-describedby, so a screen reader still reads the error with its field.
import type { FieldErrorProps } from "@rjsf/utils";
import { errorId } from "@rjsf/utils";

export default function FieldError({ errors = [], fieldPathId }: FieldErrorProps) {
  if (errors.length === 0) return null;
  return (
    <div className="flex flex-col gap-1" id={errorId(fieldPathId)} data-field-error="">
      {errors.map((error) => (
        // One field's errors are distinct sentences, so each is its own key.
        <span key={String(error)} className="text-sm font-medium text-destructive">
          {error}
        </span>
      ))}
    </div>
  );
}
