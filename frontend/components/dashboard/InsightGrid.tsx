"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  formatMomentType,
  formatProbabilityDelta,
  momentScoreline,
} from "@/lib/format";
import { learnTopicFromState, momentCopy } from "@/lib/personalization";
import type { ExplanationResponse, MatchState, MatchSummary, MomentView } from "@/types/api";
import type { ExperienceLevel } from "@/types/onboarding";
import { useProgress } from "@/hooks/useProgress";

type InsightGridProps = {
  level: ExperienceLevel | null;
  featured: MatchSummary;
  state: MatchState | null;
  moment: MomentView | null;
  momentsUnavailableReason: string | null;
  explanation: ExplanationResponse | null;
  explanationError: string | null;
};

export function InsightGrid({
  level,
  featured,
  state,
  moment,
  momentsUnavailableReason,
  explanation,
  explanationError,
}: InsightGridProps) {
  const { markTopicCompleted, markMomentRead } = useProgress();
  const copy = momentCopy(level);
  const topic = learnTopicFromState(level, state);

  return (
    <section className="mt-12">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Picked for your game
      </p>
      <h2 className="mt-2 text-3xl font-bold uppercase">Personalized insights</h2>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="flex flex-col">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--red)]">Match moment</p>
          {moment ? (
            <>
              <h3 className="mt-3 font-display text-2xl uppercase">
                {formatMomentType(moment.moment_type)}
              </h3>
              <p className="mt-2 text-sm text-muted">{copy.kicker}</p>
              <p className="mt-3 text-sm">
                {featured.teams.join(" vs ")} · sequence {moment.sequence}
              </p>
              {momentScoreline(moment) ? (
                <p className="mt-1 text-sm text-white/80">{momentScoreline(moment)}</p>
              ) : null}
              {formatProbabilityDelta(moment.probability_change) ? (
                <p className="mt-2 text-sm text-[var(--electric)]">
                  Probability movement {formatProbabilityDelta(moment.probability_change)}
                </p>
              ) : null}
              <p className="mt-3 text-sm text-white/75">
                {moment.reasons[0] ?? "Detected from reconstructed chase state."}
              </p>
              <Link
                href={`/matches/${moment.source_match_id}`}
                className="mt-auto pt-6"
                onClick={() => markMomentRead(moment.source_match_id, moment.sequence)}
              >
                <Button variant="outline" fullWidth>
                  Explore moment
                </Button>
              </Link>
            </>
          ) : (
            <EmptyInsight
              title={momentsUnavailableReason ? "Moments unavailable" : "No moment yet"}
              body={
                momentsUnavailableReason === "model_artifact_missing"
                  ? copy.unavailable
                  : copy.empty
              }
            />
          )}
        </Card>

        <Card className="flex flex-col">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--gold)]">Learn the game</p>
          <h3 className="mt-3 font-display text-2xl uppercase">{topic.title}</h3>
          <p className="mt-2 text-sm text-muted">{topic.concept}</p>
          <p className="mt-3 text-sm text-white/80">{topic.body}</p>
          {topic.evidence ? (
            <p className="mt-3 rounded-2xl bg-white/5 p-3 text-sm text-white/70">
              {topic.evidence}
            </p>
          ) : null}
          <Link
            href="/data"
            className="mt-auto pt-6"
            onClick={() => markTopicCompleted(topic.id)}
          >
            <Button variant="outline" fullWidth>
              Learn more
            </Button>
          </Link>
        </Card>

        <Card className="flex flex-col">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--electric)]">AI breakdown</p>
          {explanation ? (
            <>
              <h3 className="mt-3 font-display text-2xl uppercase">Why this state mattered</h3>
              <p className="mt-2 text-sm text-muted">
                Grounded explanation from reconstructed evidence · {explanation.model_provider}
              </p>
              <p className="mt-3 text-sm text-white/85">{explanation.summary}</p>
              <p className="mt-2 text-sm text-white/70">{explanation.why_it_matters}</p>
              <Link href={`/matches/${explanation.source_match_id}`} className="mt-auto pt-6">
                <Button variant="outline" fullWidth>
                  Read analysis
                </Button>
              </Link>
            </>
          ) : (
            <EmptyInsight
              title="Explanation unavailable"
              body={
                explanationError ??
                "The grounded explanation API did not return a breakdown for this match."
              }
            />
          )}
        </Card>
      </div>
    </section>
  );
}

function EmptyInsight({ title, body }: { title: string; body: string }) {
  return (
    <>
      <h3 className="mt-3 font-display text-2xl uppercase">{title}</h3>
      <p className="mt-3 text-sm text-muted">{body}</p>
    </>
  );
}
