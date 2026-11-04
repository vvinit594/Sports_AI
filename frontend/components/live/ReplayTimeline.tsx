"use client";

import { classifyDelivery, deliveryLabel, deliveryMarkerClass } from "@/lib/replay";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function ReplayTimeline() {
  const { states, sequence, seek, moments } = useLiveIntelligence();
  const momentSequences = new Set(moments.map((item) => item.sequence));

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-xl uppercase">Delivery timeline</h3>
        <Legend />
      </div>
      <div className="mt-4 -mx-1 overflow-x-auto pb-2">
        <div className="flex min-w-max gap-1 px-1">
          {states.map((state) => {
            const kind = classifyDelivery(state.last_delivery);
            const active = state.sequence === sequence;
            const hasMoment = momentSequences.has(state.sequence);
            return (
              <button
                key={state.sequence}
                type="button"
                title={`Seq ${state.sequence} · ${deliveryLabel(kind, state.last_delivery)}`}
                aria-current={active ? "true" : undefined}
                aria-label={`Sequence ${state.sequence}, ${deliveryLabel(kind, state.last_delivery)}`}
                onClick={() => seek(state.sequence)}
                className={`relative h-7 w-2.5 shrink-0 rounded-full ${deliveryMarkerClass(kind)} ${
                  active ? "ring-2 ring-white" : ""
                }`}
              >
                {hasMoment ? (
                  <span className="absolute -top-1 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[var(--gold)]" />
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Legend() {
  const items = [
    ["Dot", "bg-white/20"],
    ["Runs", "bg-white/55"],
    ["Four", "bg-[var(--electric)]"],
    ["Six", "bg-[var(--gold)]"],
    ["Wicket", "bg-[var(--red)]"],
    ["Extra", "border border-dashed border-white/50"],
  ];
  return (
    <ul className="flex flex-wrap gap-3 text-[10px] uppercase tracking-[0.12em] text-muted">
      {items.map(([label, className]) => (
        <li key={label} className="flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${className}`} />
          {label}
        </li>
      ))}
    </ul>
  );
}
