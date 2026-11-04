"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SectionSkeleton, StatusPanel } from "@/components/dashboard/StatusPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { getMatch, getMatchState, isPulseApiError } from "@/lib/api";
import {
  formatDate,
  formatInningsScore,
  formatOutcome,
  teamAccent,
  teamInitials,
} from "@/lib/format";
import { useProgress } from "@/hooks/useProgress";
import type { MatchDetail, MatchState } from "@/types/api";

type MatchDestinationProps = {
  matchId: string;
};

export function MatchDestination({ matchId }: MatchDestinationProps) {
  const { markMatchExplored } = useProgress();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [state, setState] = useState<MatchState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setStatus("loading");
      try {
        const [match, reconstructed] = await Promise.all([
          getMatch(matchId),
          getMatchState(matchId).catch(() => null),
        ]);
        if (cancelled) {
          return;
        }
        setDetail(match);
        setState(reconstructed?.state ?? null);
        setStatus("ready");
        markMatchExplored(matchId);
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setError(
          isPulseApiError(caught)
            ? caught.message
            : "This match could not be loaded from the catalog.",
        );
        setStatus("error");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [matchId, markMatchExplored]);

  if (status === "loading") {
    return <SectionSkeleton label="match" />;
  }

  if (status === "error" || !detail) {
    return (
      <StatusPanel
        tone="error"
        title="Match not found"
        body={error ?? "The catalog does not include this match id."}
      />
    );
  }

  const [home, away] = detail.teams;
  const outcome = formatOutcome(detail.outcome);
  const latest = formatInningsScore(state);

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Historical match · {detail.source_match_id}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Mark name={home ?? "Team"} />
        <h1 className="text-4xl font-bold uppercase sm:text-6xl">
          {home} <span className="text-white/40">vs</span> {away}
        </h1>
      </div>
      <p className="mt-4 text-white/75">
        {formatDate(detail.dates[0])}
        {detail.event_name ? ` · ${detail.event_name}` : ""}
        {detail.venue ? ` · ${detail.venue}` : ""}
      </p>
      {outcome ? <p className="mt-3 text-lg text-[var(--electric)]">{outcome}</p> : null}

      <Card className="mt-8">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          Reconstructed snapshot
        </p>
        {latest ? (
          <p className="mt-3 text-lg">{latest}</p>
        ) : (
          <p className="mt-3 text-sm text-muted">
            Latest innings score is not in this payload.
          </p>
        )}
        {state?.target != null ? (
          <p className="mt-2 text-sm text-white/75">Target {state.target}</p>
        ) : null}
        {state?.required_run_rate != null &&
        state.required_run_rate > 0 &&
        !state.match_complete ? (
          <p className="mt-1 text-sm text-white/75">
            Required run rate {state.required_run_rate.toFixed(2)}
          </p>
        ) : null}
        <p className="mt-4 text-sm text-muted">
          This page identifies the catalogued match so you can open the right
          sample. The full Match Intelligence dashboard — ball-by-ball charts and
          live companion layout — is a later milestone. Nothing here is a live
          feed.
        </p>
      </Card>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/home">
          <Button>Back to insights</Button>
        </Link>
        <Link href="/matches">
          <Button variant="outline">All matches</Button>
        </Link>
      </div>
    </div>
  );
}

function Mark({ name }: { name: string }) {
  return (
    <span
      className="grid h-12 w-12 place-items-center rounded-2xl font-display text-black"
      style={{ background: teamAccent(name) }}
    >
      {teamInitials(name)}
    </span>
  );
}
