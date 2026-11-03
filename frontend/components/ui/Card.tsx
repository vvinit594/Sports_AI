import type { HTMLAttributes, ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  selected?: boolean;
  locked?: boolean;
} & HTMLAttributes<HTMLDivElement>;

export function Card({
  children,
  selected,
  locked,
  className = "",
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-[var(--radius-lg)] border bg-[var(--surface)] p-5 shadow-[var(--shadow-card)] transition ${
        selected
          ? "border-[var(--red)] shadow-[0_0_0_1px_var(--red),0_0_28px_var(--glow)]"
          : "border-white/10"
      } ${locked ? "opacity-70" : ""} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
