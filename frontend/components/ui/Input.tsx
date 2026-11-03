"use client";

import type { InputHTMLAttributes } from "react";

type Props = {
  label: string;
  hint?: string;
  error?: string | null;
  optional?: boolean;
} & InputHTMLAttributes<HTMLInputElement>;

export function Input({
  label,
  hint,
  error,
  optional,
  id,
  className = "",
  ...props
}: Props) {
  const inputId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");

  return (
    <label className="block space-y-2" htmlFor={inputId}>
      <span className="flex items-baseline justify-between gap-3 text-sm font-medium">
        <span>{label}</span>
        {optional ? <span className="text-xs text-muted">Optional</span> : null}
      </span>
      <input
        id={inputId}
        className={`h-12 w-full rounded-2xl border bg-black/30 px-4 text-white outline-none transition placeholder:text-white/30 focus:border-[var(--gold)] ${
          error ? "border-red-400" : "border-white/15"
        } ${className}`}
        {...props}
      />
      {error ? <span className="text-sm text-red-300">{error}</span> : null}
      {!error && hint ? <span className="text-xs text-muted">{hint}</span> : null}
    </label>
  );
}
