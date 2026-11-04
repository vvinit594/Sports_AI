"use client";

import { motion, useReducedMotion } from "framer-motion";

import { formatDate, formatOutcome, teamAccent, teamInitials } from "@/lib/format";
import { formatRate, formatUnavailable } from "@/lib/replay";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function MatchScoreboard() {
  const { detail, currentState, replayStatus, replayError, retryReplay } =
    useLiveIntelligence();
  const reduceMotion = useReducedMotion();

  if (replayStatus === "loading") {
    return (
      <section className="rounded-[28px] border border-white/10 bg-black/30 p-8">
        <p className="text-sm text-muted">Loading reconstructed match state…</p>
      </section>
    );
  }

  if (replayStatus === "error") {
    return (
      <section className="rounded-[28px] border border-red-400/40 bg-red-950/20 p-8" role="alert">
        <p className="font-display text-2xl uppercase">Replay unavailable</p>
        <p className="mt-2 text-sm text-red-200">{replayError}</p>
        <button
          type="button"
          className="mt-4 text-sm text-[var(--gold)]"
          onClick={retryReplay}
        >
          Retry reconstruction
        </button>
      </section>
    );
  }

  if (!detail || !currentState) {
    return null;
  }

  const batting = currentState.batting_team;
  const bowling = currentState.bowling_team;
  const outcome = formatOutcome(detail.outcome);
  const status = currentState.match_complete
    ? currentState.match_completion_reason?.replaceAll("_", " ") ?? "Match complete"
    : currentState.innings_complete
      ? currentState.innings_completion_reason?.replaceAll("_", " ") ?? "Innings complete"
      : currentState.innings_phase?.replaceAll("_", " ") ?? "In progress";

  return (
    <section className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,59,74,0.12),rgba(12,16,24,0.95))]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4 md:px-8">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--gold)]">
            Historical replay · {detail.source_match_id}
          </p>
          <p className="mt-1 text-sm text-white/70">
            {formatDate(detail.dates[0])}
            {detail.event_name ? ` · ${detail.event_name}` : ""}
            {detail.venue ? ` · ${detail.venue}` : ""}
          </p>
        </div>
        <p className="rounded-full border border-white/15 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-white/70">
          {status}
        </p>
      </div>

      <div className="grid gap-6 px-5 py-6 md:grid-cols-[1fr_auto_1fr] md:items-center md:px-8">
        <TeamBlock
          label="Batting"
          name={batting}
          emphasis
        />
        <div className="text-center">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Score</p>
          <p className="font-display text-5xl leading-none sm:text-7xl">
            <AnimatedValue
              value={currentState.innings_runs}
              reduceMotion={Boolean(reduceMotion)}
            />
            <span className="text-white/35">/</span>
            <AnimatedValue
              value={currentState.innings_wickets}
              reduceMotion={Boolean(reduceMotion)}
            />
          </p>
          <p className="mt-2 text-lg text-white/80">
            {currentState.overs} ov
          </p>
        </div>
        <TeamBlock label="Bowling" name={bowling} />
      </div>

      <dl className="grid grid-cols-2 gap-px bg-white/10 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="CRR" value={formatRate(currentState.current_run_rate)} />
        <Stat label="Target" value={formatUnavailable(currentState.target)} />
        <Stat label="Runs left" value={formatUnavailable(currentState.runs_remaining)} />
        <Stat label="RRR" value={formatRate(currentState.required_run_rate)} />
        <Stat label="Wkts left" value={formatUnavailable(currentState.wickets_remaining)} />
        <Stat label="Balls left" value={formatUnavailable(currentState.balls_remaining)} />
      </dl>
      {outcome ? (
        <p className="px-5 py-3 text-sm text-[var(--electric)] md:px-8">
          Final recorded result: {outcome}
        </p>
      ) : null}
    </section>
  );
}

function TeamBlock({
  label,
  name,
  emphasis,
}: {
  label: string;
  name: string | null;
  emphasis?: boolean;
}) {
  return (
    <div className={emphasis ? "" : "md:text-right"}>
      <p className="text-[10px] uppercase tracking-[0.16em] text-muted">{label}</p>
      {name ? (
        <div className={`mt-2 flex items-center gap-3 ${emphasis ? "" : "md:justify-end"}`}>
          <span
            className="grid h-10 w-10 place-items-center rounded-full text-xs font-bold"
            style={{ background: `${teamAccent(name)}33`, color: teamAccent(name) }}
          >
            {teamInitials(name)}
          </span>
          <p className="font-display text-xl uppercase sm:text-2xl">{name}</p>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted">Unavailable in this state</p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[var(--ink)] px-4 py-3">
      <dt className="text-[10px] uppercase tracking-[0.14em] text-muted">{label}</dt>
      <dd className="mt-1 font-display text-xl">{value}</dd>
    </div>
  );
}

function AnimatedValue({
  value,
  reduceMotion,
}: {
  value: number;
  reduceMotion: boolean;
}) {
  return (
    <motion.span
      key={value}
      initial={reduceMotion ? false : { opacity: 0.45, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
    >
      {value}
    </motion.span>
  );
}
