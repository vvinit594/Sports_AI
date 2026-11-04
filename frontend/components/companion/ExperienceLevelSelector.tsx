"use client";

import type { AudienceLevel } from "@/types/api";
import { audienceVisibleLabel } from "@/lib/personalization";

const LEVELS: AudienceLevel[] = ["beginner", "casual", "advanced"];

type ExperienceLevelSelectorProps = {
  value: AudienceLevel;
  onChange: (level: AudienceLevel) => void;
  note?: string;
};

export function ExperienceLevelSelector({
  value,
  onChange,
  note = "Temporary for this chat. It does not change your saved profile.",
}: ExperienceLevelSelectorProps) {
  return (
    <fieldset>
      <legend className="text-xs uppercase tracking-[0.16em] text-muted">
        Explanation style
      </legend>
      <p className="mt-1 text-[11px] text-muted">{note}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {LEVELS.map((level) => {
          const active = level === value;
          return (
            <button
              key={level}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(level)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] ${
                active
                  ? "bg-[var(--red)] text-white"
                  : "border border-white/15 text-white/70 hover:text-white"
              }`}
            >
              {audienceVisibleLabel(level)}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
