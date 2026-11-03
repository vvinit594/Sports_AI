"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Lock } from "lucide-react";
import type { ReactNode } from "react";

type SportCardProps = {
  title: string;
  description: string;
  visual: ReactNode;
  selected?: boolean;
  locked?: boolean;
  onSelect?: () => void;
};

export function SportCard({
  title,
  description,
  visual,
  selected,
  locked,
  onSelect,
}: SportCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      aria-pressed={locked ? undefined : Boolean(selected)}
      aria-disabled={locked || undefined}
      onClick={onSelect}
      whileHover={locked || reduceMotion ? undefined : { y: -6 }}
      whileTap={locked || reduceMotion ? undefined : { scale: 0.98 }}
      className={`group relative min-h-[260px] w-full overflow-hidden rounded-[28px] border p-5 text-left transition ${
        selected
          ? "border-[var(--red)] shadow-[0_0_0_1px_var(--red),0_0_34px_var(--glow)]"
          : "border-white/10"
      } ${locked ? "cursor-not-allowed bg-[#10131a]" : "bg-[var(--surface)]"}`}
    >
      <div className="mb-6 h-28 overflow-hidden rounded-2xl">{visual}</div>
      <h3 className="font-display text-3xl uppercase">{title}</h3>
      <p className="mt-2 text-sm text-muted">{description}</p>
      {locked ? (
        <span className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/40 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white/70">
          <Lock size={13} aria-hidden />
          Coming soon
        </span>
      ) : null}
      {selected ? (
        <span className="absolute right-4 top-4 rounded-full bg-[var(--red)] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em]">
          Selected
        </span>
      ) : null}
    </motion.button>
  );
}
