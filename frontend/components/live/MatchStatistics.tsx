"use client";

import { useMemo, useState } from "react";

import { classifyDelivery, deliveryLabel, formatRate, formatUnavailable } from "@/lib/replay";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function MatchStatistics() {
  const { currentState, states, sequence, detail } = useLiveIntelligence();
  const [open, setOpen] = useState(false);
  const recent = useMemo(() => {
    return states
      .filter((item) => item.sequence <= sequence && item.last_delivery)
      .slice(-8)
      .reverse();
  }, [sequence, states]);

  if (!currentState || !detail) {
    return null;
  }

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)]">
      <button
        type="button"
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span>
          <span className="block text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
            Match statistics
          </span>
          <span className="font-display text-xl uppercase">Reconstructed snapshot</span>
        </span>
        <span className="text-sm text-white/60">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="space-y-5 border-t border-white/10 px-5 py-5">
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
            <Stat label="Innings" value={formatUnavailable(currentState.innings_number)} />
            <Stat
              label="Score"
              value={`${currentState.innings_runs}/${currentState.innings_wickets}`}
            />
            <Stat label="Overs" value={currentState.overs} />
            <Stat label="CRR" value={formatRate(currentState.current_run_rate)} />
            <Stat label="RRR" value={formatRate(currentState.required_run_rate)} />
            <Stat label="Target" value={formatUnavailable(currentState.target)} />
            <Stat label="Runs left" value={formatUnavailable(currentState.runs_remaining)} />
            <Stat label="Wkts left" value={formatUnavailable(currentState.wickets_remaining)} />
            <Stat label="Balls left" value={formatUnavailable(currentState.balls_remaining)} />
            <Stat
              label="Legal balls"
              value={formatUnavailable(currentState.legal_balls)}
            />
            <Stat
              label="Deliveries applied"
              value={formatUnavailable(currentState.total_deliveries)}
            />
            <Stat label="Format" value={detail.match_type} />
          </dl>
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-muted">This delivery</p>
            {currentState.last_delivery ? (
              <p className="mt-1 text-sm">
                {currentState.last_delivery.batter} vs {currentState.last_delivery.bowler}
                {currentState.last_delivery.non_striker
                  ? ` · non-striker ${currentState.last_delivery.non_striker}`
                  : ""}
              </p>
            ) : (
              <p className="mt-1 text-sm text-muted">
                Sequence 0 has no applied delivery. Batter and bowler figures are not invented.
              </p>
            )}
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-muted">Recent deliveries</p>
            {recent.length === 0 ? (
              <p className="mt-1 text-sm text-muted">No deliveries have been applied yet.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {recent.map((item) => {
                  const delivery = item.last_delivery;
                  const kind = classifyDelivery(delivery);
                  return (
                    <li key={item.sequence} className="flex justify-between gap-3">
                      <span>
                        Seq {item.sequence}
                        {delivery ? ` · ${delivery.batter}` : ""}
                      </span>
                      <span className="text-white/70">
                        {deliveryLabel(kind, delivery)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 px-3 py-2">
      <dt className="text-[10px] uppercase tracking-[0.12em] text-muted">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}
