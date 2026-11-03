"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

type LevelCardProps = {
  title: string;
  description: string;
  icon: ReactNode;
  selected: boolean;
  onSelect: () => void;
};

export function LevelCard({
  title,
  description,
  icon,
  selected,
  onSelect,
}: LevelCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      whileHover={reduceMotion ? undefined : { y: -5 }}
      whileTap={reduceMotion ? undefined : { scale: 0.98 }}
      className={`w-full rounded-[28px] border p-6 text-left transition ${
        selected
          ? "border-[var(--red)] bg-[var(--surface)] shadow-[0_0_0_1px_var(--red),0_0_30px_var(--glow)]"
          : "border-white/10 bg-[var(--surface)] hover:border-white/30"
      }`}
    >
      <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-white/5 text-[var(--gold)]">
        {icon}
      </div>
      <h3 className="font-display text-2xl uppercase">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-muted">{description}</p>
    </motion.button>
  );
}
