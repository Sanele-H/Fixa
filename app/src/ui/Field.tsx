import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";

type FieldLabelProps = {
  label: string;
  hint?: string;
};

/** A labelled text input. The label is always visible; placeholders are only examples. */
export function TextField({ label, hint, ...inputProps }: FieldLabelProps & InputHTMLAttributes<HTMLInputElement>) {
  const inputId = useId();
  const hintId = `${inputId}-hint`;
  return (
    <div className="field">
      <label className="field__label" htmlFor={inputId}>
        {label}
      </label>
      <input id={inputId} className="field__input" aria-describedby={hint ? hintId : undefined} {...inputProps} />
      {hint && (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      )}
    </div>
  );
}

/** A labelled multi-line text box, for job descriptions and messages. */
export function TextArea({ label, hint, ...textareaProps }: FieldLabelProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const textareaId = useId();
  const hintId = `${textareaId}-hint`;
  return (
    <div className="field">
      <label className="field__label" htmlFor={textareaId}>
        {label}
      </label>
      <textarea
        id={textareaId}
        className="field__textarea"
        aria-describedby={hint ? hintId : undefined}
        {...textareaProps}
      />
      {hint && (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      )}
    </div>
  );
}
