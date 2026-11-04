"use client";

import Link from "next/link";

import { Card } from "@/components/ui/Card";
import {
  formatMomentType,
  formatProbability,
  formatProbabilityDelta,
  momentScoreline,
} from "@/lib/format";
import { momentCopy } from "@/lib/personalization";
import type { MatchSummary, MomentView } from "@/types/api";
import type { ExperienceLevel } from "@/types/onboarding";
import { useProgress } from "@/hooks/useProgress";

type TrendingMomentsProps = {
  level: ExperienceLevel | null;
  moments: MomentView[];
  matches: MatchSummary[];
  unavailableReason: string | null;
  loaded: boolean;
  evaluationLimitation: string | null;
};

export function TrendingMoments({
  level,
  moments,
  matches,
  unavailableReason,
  loaded,
  evaluationLimitation,
}: TrendingMomentsProps) {
  const { markMomentRead } = useProgress();
  const copy = momentCopy(level);
  const byId = new Map(matches.map((match) => [match.source_match_id, match]));

  return (
    <section className="mt-12">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Historical moments
      </p>
      <h2 className="mt-2 text-3xl font-bold uppercase">Interesting moments</h2>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        Flagged by the existing significant-moment detector on completed sample
        matches. These are not live trending events.
        {evaluationLimitation ? ` ${evaluationLimitation}` : ""}
      </p>
      {!loaded ? (
        <p className="mt-6 text-sm text-muted">Checking detected moments…</p>
      ) : moments.length === 0 ? (
        <p className="mt-6 rounded-[24px] border border-white/10 bg-[var(--surface)] p-5 text-sm text-muted">
          {unavailableReason === "model_artifact_missing"
            ? copy.unavailable
            : copy.empty}
        </p>
      ) : (
        <div className="mt-6 flex snap-x gap-4 overflow-x-auto pb-3 lg:grid lg:grid-cols-2 lg:overflow-visible">
          {moments.map((moment) => {
            const match = byId.get(moment.source_match_id);
            const title = match ? match.teams.join(" vs ") : moment.source_match_id;
            return (
              <Link
                key={`${moment.source_match_id}-${moment.sequence}-${moment.moment_type}`}
                href={`/matches/${moment.source_match_id}`}
                className="min-w-[280px] snap-start"
                onClick={() => markMomentRead(moment.source_match_id, moment.sequence)}
              >
                <Card className="h-full hover:border-white/25">
                  <p className="text-xs uppercase tracking-[0.16em] text-[var(--red)]">
                    {formatMomentType(moment.moment_type)}
                  </p>
                  <h3 className="mt-2 font-display text-xl uppercase">{title}</h3>
                  <p className="mt-2 text-sm text-muted">Delivery sequence {moment.sequence}</p>
                  {momentScoreline(moment) ? (
                    <p className="mt-2 text-sm">{momentScoreline(moment)}</p>
                  ) : null}
                  <p className="mt-3 text-sm text-white/75">
                    {moment.reasons[0] ?? "Detected from reconstructed chase state."}
                  </p>
                  {formatProbabilityDelta(moment.probability_change) ? (
                    <p className="mt-3 text-sm text-[var(--electric)]">
                      {formatProbability(moment.probability_before)} →{" "}
                      {formatProbability(moment.probability_after)} (
                      {formatProbabilityDelta(moment.probability_change)})
                    </p>
                  ) : null}
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
