"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "outline";
type Size = "md" | "lg" | "xl";

type ButtonProps = {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

const variants: Record<Variant, string> = {
  primary:
    "bg-[var(--red)] text-white shadow-[0_10px_30px_var(--glow)] hover:bg-[var(--red-deep)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]",
  secondary:
    "bg-white text-ink hover:bg-zinc-100 hover:-translate-y-0.5 active:scale-[0.98]",
  ghost:
    "bg-transparent text-white hover:bg-white/10 active:scale-[0.98]",
  outline:
    "border border-white/20 bg-white/5 text-white hover:border-white/50 hover:-translate-y-0.5 active:scale-[0.98]",
};

const sizes: Record<Size, string> = {
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
  xl: "h-14 px-8 text-lg tracking-[0.18em]",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  fullWidth,
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-display font-semibold uppercase transition duration-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0 ${variants[variant]} ${sizes[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
