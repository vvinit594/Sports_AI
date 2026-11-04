"use client";

import { ExperienceLevelSelector } from "@/components/companion/ExperienceLevelSelector";
import { Button } from "@/components/ui/Button";
import { formatDate, formatInningsScore, formatOutcome } from "@/lib/format";
import { audienceVisibleLabel } from "@/lib/personalization";
import { useCompanion } from "@/hooks/useCompanion";

type MatchContextPanelProps = {
  onChangeMatch: () => void;
};

export function MatchContextPanel({ onChangeMatch }: MatchContextPanelProps) {
  const {
    active,
    matchDetail,
    matchState,
    matchLoading,
    matchError,
    setAudienceLevel,
    setSelectedMatch,
    profileAudience,
  } = useCompanion();

  const selectedId = active?.selectedMatchId;
  const outcome = matchDetail ? formatOutcome(matchDetail.outcome) : null;
  const latest = formatInningsScore(matchState);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-[var(--ink-2)] p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--gold)]">Match context</p>
      <h2 className="mt-1 font-display text-2xl uppercase">Intelligence lens</h2>

      {!selectedId ? (
        <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-sm text-white/80">
            No match selected. Choose a historical match to explore its intelligence.
          </p>
          <div className="mt-4">
            <Button fullWidth onClick={onChangeMatch}>
              Change match
            </Button>
          </div>
        </div>
      ) : matchLoading ? (
        <p className="mt-6 text-sm text-muted">Loading reconstructed match…</p>
      ) : matchError ? (
        <p className="mt-6 text-sm text-red-300" role="alert">
          {matchError}
        </p>
      ) : matchDetail ? (
        <div className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/50">
            Historical sample
          </p>
          <p className="font-display text-xl uppercase">
            {matchDetail.teams.join(" vs ")}
          </p>
          <p className="text-sm text-muted">
            {formatDate(matchDetail.dates[0])}
            {matchDetail.event_name ? ` · ${matchDetail.event_name}` : ""}
          </p>
          {matchDetail.venue ? (
            <p className="text-sm text-white/75">{matchDetail.venue}</p>
          ) : null}
          {outcome ? <p className="text-sm text-[var(--electric)]">{outcome}</p> : null}
          {latest ? (
            <p className="text-sm">Latest reconstructed innings: {latest}</p>
          ) : null}
          {matchState?.target != null ? (
            <p className="text-sm text-white/75">Target {matchState.target}</p>
          ) : null}
          <p className="text-xs text-muted">
            Source id {matchDetail.source_match_id} · not live
          </p>
        </div>
      ) : null}

      {selectedId ? (
        <div className="mt-3 flex gap-2">
          <Button variant="outline" onClick={onChangeMatch}>
            Change match
          </Button>
          <Button variant="ghost" onClick={() => setSelectedMatch(null)}>
            Clear
          </Button>
        </div>
      ) : null}

      <div className="mt-8">
        {active ? (
          <ExperienceLevelSelector
            value={active.audienceLevel}
            onChange={setAudienceLevel}
          />
        ) : null}
        <p className="mt-3 text-xs text-muted">
          Saved profile default: {audienceVisibleLabel(profileAudience)}. This
          control only changes the current conversation.
        </p>
      </div>
    </div>
  );
}
