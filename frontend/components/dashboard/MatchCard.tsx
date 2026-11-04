import Link from "next/link";

import { formatDate, formatOutcome, teamAccent, teamInitials } from "@/lib/format";
import type { MatchSummary } from "@/types/api";

type MatchCardProps = {
  match: MatchSummary;
  compact?: boolean;
};

export function MatchCard({ match, compact = false }: MatchCardProps) {
  const outcome = formatOutcome(match.outcome);
  const [home, away] = match.teams;

  return (
    <Link
      href={`/matches/${match.source_match_id}`}
      className={`block min-w-[260px] rounded-[24px] border border-white/10 bg-[var(--surface)] p-5 transition hover:-translate-y-0.5 hover:border-white/25 ${
        compact ? "snap-start" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="rounded-full border border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/60">
          Historical sample
        </span>
        <span className="text-xs text-muted">{match.match_type}</span>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <TeamMark name={home ?? "Team"} />
        <p className="font-display text-lg uppercase leading-tight">
          {home ?? "Team"} <span className="text-muted">vs</span> {away ?? "Team"}
        </p>
      </div>
      <p className="mt-3 text-sm text-muted">
        {formatDate(match.dates[0])}
        {match.event_name ? ` · ${match.event_name}` : ""}
      </p>
      {match.venue ? <p className="mt-1 text-sm text-white/70">{match.venue}</p> : null}
      {outcome ? (
        <p className="mt-3 text-sm text-[var(--electric)]">{outcome}</p>
      ) : (
        <p className="mt-3 text-sm text-muted">Result not in source metadata</p>
      )}
    </Link>
  );
}

function TeamMark({ name }: { name: string }) {
  return (
    <span
      className="grid h-10 w-10 shrink-0 place-items-center rounded-full font-display text-xs text-black"
      style={{ background: teamAccent(name) }}
    >
      {teamInitials(name)}
    </span>
  );
}
