"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";

import { StadiumBackdrop } from "@/components/atmosphere/StadiumBackdrop";
import { Button } from "@/components/ui/Button";
import {
  formatDate,
  formatInningsScore,
  formatOutcome,
  teamAccent,
  teamInitials,
} from "@/lib/format";
import type { MatchDetail, MatchState, MatchSummary } from "@/types/api";

type FeaturedMatchProps = {
  match: MatchSummary;
  detail: MatchDetail | null;
  state: MatchState | null;
};

export function FeaturedMatch({ match, detail, state }: FeaturedMatchProps) {
  const reduceMotion = useReducedMotion();
  const [home, away] = match.teams;
  const outcome = formatOutcome(match.outcome);
  const latestScore = formatInningsScore(state);

  return (
    <motion.section
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative isolate overflow-hidden rounded-[32px] border border-white/10"
    >
      <div className="stadium-hero absolute inset-0">
        <StadiumBackdrop />
      </div>
      <div className="relative z-10 grid gap-8 px-6 py-10 md:grid-cols-[1.2fr_0.8fr] md:px-10 md:py-14">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
            Featured match · Historical sample
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <Crest name={home ?? "Team"} />
            <h2 className="max-w-xl text-3xl font-bold uppercase leading-none sm:text-5xl">
              {home} <span className="text-white/40">vs</span> {away}
            </h2>
            <Crest name={away ?? "Team"} />
          </div>
          <p className="mt-4 text-white/75">
            {formatDate(match.dates[0])}
            {match.event_name ? ` · ${match.event_name}` : ""}
            {match.venue ? ` · ${match.venue}` : ""}
          </p>
          {detail?.season ? (
            <p className="mt-1 text-sm text-muted">Season {detail.season}</p>
          ) : null}
          <div className="mt-6 space-y-2">
            {outcome ? (
              <p className="text-lg text-[var(--electric)]">{outcome}</p>
            ) : (
              <p className="text-sm text-muted">Final result not listed in source metadata.</p>
            )}
            {latestScore ? (
              <p className="text-sm text-white/80">
                Latest reconstructed innings: {latestScore}
              </p>
            ) : null}
            <p className="text-xs uppercase tracking-[0.16em] text-white/45">
              Completed historical match · not live
            </p>
          </div>
          <Link href={`/matches/${match.source_match_id}`} className="mt-8 inline-block">
            <Button size="lg">Explore match intelligence</Button>
          </Link>
        </div>
        <aside className="rounded-[24px] border border-white/10 bg-black/40 p-5 backdrop-blur-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-muted">Source facts</p>
          <dl className="mt-4 space-y-3 text-sm">
            <Fact label="Format" value={match.match_type} />
            <Fact label="Deliveries in file" value={String(match.delivery_count)} />
            <Fact
              label="Toss"
              value={
                detail?.toss_winner
                  ? `${detail.toss_winner} (${detail.toss_decision ?? "decision unknown"})`
                  : "Not in this payload"
              }
            />
            <Fact
              label="Player of the match"
              value={detail?.player_of_match?.[0] ?? "Not in this payload"}
            />
          </dl>
        </aside>
      </div>
    </motion.section>
  );
}

function Crest({ name }: { name: string }) {
  return (
    <span
      className="grid h-14 w-14 place-items-center rounded-2xl font-display text-lg text-black"
      style={{ background: teamAccent(name) }}
    >
      {teamInitials(name)}
    </span>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
