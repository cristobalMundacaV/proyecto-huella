import { useId } from "react";

function Field({ label, helper, error, required, children, inputId }) {
  const messageId = `${inputId}-message`;
  return <label htmlFor={inputId} className="block text-sm">
    {label && <span className={`mb-1.5 block font-bold ${error ? "text-[var(--status-danger)]" : "text-[var(--text-secondary)]"}`}>{label}{required && <span aria-hidden="true"> *</span>}{required && <span className="sr-only"> (obligatorio)</span>}</span>}
    {children(messageId)}
    {error ? <span id={messageId} className="mt-1.5 block text-xs font-medium text-[var(--status-danger)]" role="alert">{error}</span> : helper && <span id={messageId} className="mt-1.5 block text-xs leading-5 text-[var(--text-muted)]">{helper}</span>}
  </label>;
}

const baseControl = "block min-h-11 w-full rounded-[var(--radius-md)] border bg-[var(--bg-surface)] px-3 py-2.5 text-sm text-[var(--text-primary)] shadow-sm transition placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-not-allowed disabled:bg-[var(--bg-surface-subtle)] disabled:text-[var(--text-muted)] disabled:opacity-70";

function useControlProps({ id, error, helper, className = "", ...props }) {
  const generatedId = useId();
  const inputId = id || generatedId;
  return { inputId, props: { id: inputId, "aria-invalid": error ? "true" : undefined, "aria-describedby": error || helper ? `${inputId}-message` : undefined, className: `${baseControl} ${error ? "border-[var(--status-danger)]" : "border-[var(--border-default)]"} ${className}`, ...props } };
}

export function Input({ label, helper, error, required, ...inputProps }) { const { inputId, props } = useControlProps({ ...inputProps, error, helper }); return <Field {...{ label, helper, error, required, inputId }}>{() => <input {...props} required={required} />}</Field>; }
export function Textarea({ label, helper, error, required, ...inputProps }) { const { inputId, props } = useControlProps({ ...inputProps, error, helper }); return <Field {...{ label, helper, error, required, inputId }}>{() => <textarea {...props} required={required} className={`${props.className} min-h-24 resize-y`} />}</Field>; }
export function Select({ label, helper, error, required, children, ...inputProps }) { const { inputId, props } = useControlProps({ ...inputProps, error, helper }); return <Field {...{ label, helper, error, required, inputId }}>{() => <select {...props} required={required}>{children}</select>}</Field>; }
export function SearchInput(props) { return <Input type="search" {...props} />; }
export function FilterBar({ children }) { return <div className="flex flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 sm:flex-row sm:flex-wrap sm:items-end">{children}</div>; }
