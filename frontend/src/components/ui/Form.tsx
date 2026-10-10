// Labelled form controls. Every input on the site uses these so forms look
// the same everywhere.

import { useId } from "react";
import type { Choice } from "@/lib/types";

const controlClass =
  "block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 " +
  "placeholder:text-zinc-400 focus:border-emerald-600 focus:outline-none focus:ring-2 " +
  "focus:ring-emerald-600/20 disabled:bg-zinc-100 disabled:text-zinc-500";

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  children: React.ReactNode;
}

/** A label above a control, with an optional hint below it. */
export function Field({ label, htmlFor, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-zinc-700">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-zinc-500">{hint}</p>}
    </div>
  );
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

/** Text input with a label and an optional hint. */
export function Input({ label, hint, className = "", ...rest }: InputProps) {
  const id = useId();
  return (
    <Field label={label} htmlFor={id} hint={hint}>
      <input id={id} className={`${controlClass} ${className}`} {...rest} />
    </Field>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

/** Multi-line text input with a label and an optional hint. */
export function Textarea({ label, hint, className = "", rows = 3, ...rest }: TextareaProps) {
  const id = useId();
  return (
    <Field label={label} htmlFor={id} hint={hint}>
      <textarea id={id} rows={rows} className={`${controlClass} ${className}`} {...rest} />
    </Field>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: Choice[];
  placeholder?: string;
  hint?: string;
}

/** Dropdown with a label, an optional empty first option and an optional hint. */
export function Select({ label, options, placeholder, hint, className = "", ...rest }: SelectProps) {
  const id = useId();
  return (
    <Field label={label} htmlFor={id} hint={hint}>
      <select id={id} className={`${controlClass} ${className}`} {...rest}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

export { controlClass };
