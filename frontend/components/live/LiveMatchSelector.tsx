"use client";

import { useMemo, useState } from "react";

import { StatusPanel } from "@/components/dashboard/StatusPanel";
import { Button } from "@/components/ui/Button";
import { formatDate, formatOutcome, teamAccent, teamInitials } from "@/lib/format";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";
import type { MatchSummary } from "@/types/api";

export function LiveMatchSelector() {
  const {
    matches,
    catalogStatus,
    catalogError,
    selectedMatchId,
    selectMatch,
  } = useLiveIntelligence();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(!selectedMatchId);

  const selected = matches.find((item) => item.source_match_id === selectedMatchId) ?? null;
  const filtered = useMemo(() => filterMatches(matches, query), [matches, query]);

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--gold)]">
            Historical replay
          </p>
          <h2 className="mt-1 font-display text-2xl uppercase">Choose a reconstructed match</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            PulseIQ replays Cricsheet sample states. This is not a live feed and not a
            simulated scoreboard.
          </p>
        </div>
        {selected ? (
          <Button variant="outline" onClick={() => setOpen((value) => !value)}>
            {open ? "Hide catalog" : "Change match"}
          </Button>
        ) : null}
      </div>

      {selected ? (
        <div className="mt-5 rounded-2xl border border-[var(--red)]/40 bg-black/30 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/50">
            Selected historical sample
          </p>
          <p className="mt-1 font-display text-xl uppercase">
            {selected.teams.join(" vs ")}
          </p>
          <p className="mt-1 text-sm text-muted">
            {formatDate(selected.dates[0])}
            {selected.event_name ? ` · ${selected.event_name}` : ""}
            {selected.venue ? ` · ${selected.venue}` : ""}
            {` · ${selected.match_type}`}
          </p>
          {formatOutcome(selected.outcome) ? (
            <p className="mt-2 text-sm text-[var(--electric)]">
              {formatOutcome(selected.outcome)}
            </p>
          ) : null}
        </div>
      ) : null}

      {open || !selected ? (
        <div className="mt-5">
          <label htmlFor="live-match-search" className="sr-only">
            Search historical matches
          </label>
          <input
            id="live-match-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search teams, venue, tournament…"
            className="h-11 w-full rounded-2xl border border-white/15 bg-black/40 px-4 text-sm outline-none focus:border-[var(--gold)]"
          />
          <div className="mt-4 max-h-[22rem] overflow-y-auto pr-1">
            {catalogStatus === "loading" ? (
              <p className="text-sm text-muted">Loading historical matches…</p>
            ) : null}
            {catalogStatus === "error" ? (
              <StatusPanel
                tone="error"
                title="Catalog unavailable"
                body={catalogError ?? "The match list could not be loaded."}
              />
            ) : null}
            {catalogStatus === "empty" ? (
              <StatusPanel
                title="No historical matches"
                body="The FastAPI catalog is empty. Load Cricsheet samples before opening Live Intelligence."
              />
            ) : null}
            {catalogStatus === "ready" && filtered.length === 0 ? (
              <p className="text-sm text-muted">No matches match that search.</p>
            ) : null}
            {catalogStatus === "ready" ? (
              <ul className="grid gap-3 md:grid-cols-2">
                {filtered.map((match) => (
                  <li key={match.source_match_id}>
                    <MatchOption
                      match={match}
                      selected={match.source_match_id === selectedMatchId}
                      onSelect={() => {
                        selectMatch(match.source_match_id);
                        setOpen(false);
                      }}
                    />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function MatchOption({
  match,
  selected,
  onSelect,
}: {
  match: MatchSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const outcome = formatOutcome(match.outcome);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        selected
          ? "border-[var(--red)] bg-[var(--red)]/10"
          : "border-white/10 bg-black/25 hover:border-white/25"
      }`}
    >
      <div className="flex items-center gap-3">
        {match.teams.slice(0, 2).map((team) => (
          <span
            key={team}
            className="grid h-9 w-9 place-items-center rounded-full text-[10px] font-bold"
            style={{ background: `${teamAccent(team)}33`, color: teamAccent(team) }}
          >
            {teamInitials(team)}
          </span>
        ))}
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/45">
          Historical sample · {match.match_type}
        </span>
      </div>
      <p className="mt-3 font-medium">{match.teams.join(" vs ")}</p>
      <p className="mt-1 text-xs text-muted">
        {formatDate(match.dates[0])}
        {match.event_name ? ` · ${match.event_name}` : ""}
      </p>
      {match.venue ? <p className="mt-1 text-xs text-white/70">{match.venue}</p> : null}
      {outcome ? <p className="mt-2 text-xs text-[var(--electric)]">{outcome}</p> : null}
    </button>
  );
}

function filterMatches(matches: MatchSummary[], query: string): MatchSummary[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return matches;
  }
  return matches.filter((match) =>
    [
      ...match.teams,
      match.event_name ?? "",
      match.venue ?? "",
      match.city ?? "",
      match.match_type,
      match.source_match_id,
      formatOutcome(match.outcome) ?? "",
    ]
      .join(" ")
      .toLowerCase()
      .includes(needle),
  );
}
