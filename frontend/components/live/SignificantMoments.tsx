"use client";

import { useState } from "react";

import { formatMomentType, formatProbability, formatProbabilityDelta, momentScoreline } from "@/lib/format";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function SignificantMoments() {
  const {
    moments,
    momentsAvailable,
    momentsReason,
    selectedMoment,
    selectMoment,
    sequence,
  } = useLiveIntelligence();
  const [open, setOpen] = useState(true);

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-4 md:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
            Significant moments
          </p>
          <h3 className="mt-1 font-display text-2xl uppercase">Detector timeline</h3>
        </div>
        <button
          type="button"
          className="text-sm text-white/60 xl:hidden"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide" : "Show"}
        </button>
      </div>
      <div className={open ? "block" : "hidden xl:block"}>

      {!momentsAvailable ? (
        <p className="mt-4 text-sm text-white/75" role="status">
          {momentsReason === "model_artifact_missing"
            ? "Moments require the loaded probability model. None can be invented here."
            : momentsReason ?? "Significant moments are unavailable for this match."}
        </p>
      ) : moments.length === 0 ? (
        <p className="mt-4 text-sm text-white/75">
          No significant moments were detected for this match.
        </p>
      ) : (
        <ul className="mt-4 grid gap-3 lg:grid-cols-2">
          {moments.map((moment) => {
            const active =
              selectedMoment?.sequence === moment.sequence &&
              selectedMoment.moment_type === moment.moment_type;
            const onSequence = moment.sequence === sequence;
            return (
              <li key={`${moment.moment_type}-${moment.sequence}`}>
                <button
                  type="button"
                  onClick={() => selectMoment(moment)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    active || onSequence
                      ? "border-[var(--red)] bg-[var(--red)]/10"
                      : "border-white/10 bg-black/25 hover:border-white/25"
                  }`}
                >
                  <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--gold)]">
                    {formatMomentType(moment.moment_type)} · seq {moment.sequence}
                  </p>
                  <p className="mt-2 text-sm">
                    {formatProbability(moment.probability_before)} →{" "}
                    {formatProbability(moment.probability_after)}{" "}
                    <span className="text-[var(--electric)]">
                      {formatProbabilityDelta(moment.probability_change)}
                    </span>
                  </p>
                  {momentScoreline(moment) ? (
                    <p className="mt-1 text-xs text-white/70">{momentScoreline(moment)}</p>
                  ) : null}
                  {moment.reasons[0] ? (
                    <p className="mt-2 text-sm text-white/80">{moment.reasons[0]}</p>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      </div>
    </section>
  );
}
