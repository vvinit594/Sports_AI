"use client";

import { useMemo, useState } from "react";

import { StatusPanel } from "@/components/dashboard/StatusPanel";
import { formatDate, formatOutcome, teamAccent, teamInitials } from "@/lib/format";
import { useCompanion } from "@/hooks/useCompanion";
import type { MatchSummary } from "@/types/api";

type MatchSelectorProps = {
  open: boolean;
  onClose: () => void;
};

export function MatchSelector({ open, onClose }: MatchSelectorProps) {
  const { matches, catalogStatus, catalogError, setSelectedMatch, active } =
    useCompanion();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return matches;
    }
    return matches.filter((match) => {
      const haystack = [
        ...match.teams,
        match.event_name ?? "",
        match.venue ?? "",
        match.source_match_id,
        formatOutcome(match.outcome) ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [matches, query]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 md:items-center">
      <div
        role="dialog"
        aria-labelledby="match-selector-title"
        className="flex max-h-[85svh] w-full max-w-3xl flex-col rounded-[28px] border border-white/10 bg-[var(--ink)]"
      >
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
              Historical catalog
            </p>
            <h2 id="match-selector-title" className="font-display text-2xl uppercase">
              Choose a match
            </h2>
          </div>
          <button type="button" className="text-sm text-white/70" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="px-5 py-3">
          <label htmlFor="match-search" className="sr-only">
            Search matches
          </label>
          <input
            id="match-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search teams, venue, tournament…"
            className="h-11 w-full rounded-2xl border border-white/15 bg-black/40 px-4 text-sm"
          />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
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
              title="No matches"
              body="The API returned an empty historical list."
            />
          ) : null}
          {catalogStatus === "ready" && filtered.length === 0 ? (
            <p className="text-sm text-muted">No matches match that search.</p>
          ) : null}
          <ul className="space-y-2">
            {filtered.map((match) => (
              <li key={match.source_match_id}>
                <SelectorCard
                  match={match}
                  selected={active?.selectedMatchId === match.source_match_id}
                  onSelect={() => {
                    setSelectedMatch(match.source_match_id);
                    onClose();
                  }}
                />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function SelectorCard({
  match,
  selected,
  onSelect,
}: {
  match: MatchSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const outcome = formatOutcome(match.outcome);
  const [home, away] = match.teams;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left ${
        selected ? "border-[var(--red)] bg-[var(--red)]/10" : "border-white/10 bg-[var(--surface)]"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/50">
          Historical sample
        </span>
        <span className="text-xs text-muted">{match.match_type}</span>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <span
          className="grid h-9 w-9 place-items-center rounded-full text-xs font-display text-black"
          style={{ background: teamAccent(home ?? "Team") }}
        >
          {teamInitials(home ?? "Team")}
        </span>
        <p className="font-display text-lg uppercase">
          {home} <span className="text-muted">vs</span> {away}
        </p>
      </div>
      <p className="mt-2 text-sm text-muted">
        {formatDate(match.dates[0])}
        {match.event_name ? ` · ${match.event_name}` : ""}
      </p>
      {match.venue ? <p className="text-sm text-white/70">{match.venue}</p> : null}
      {outcome ? <p className="mt-2 text-sm text-[var(--electric)]">{outcome}</p> : null}
    </button>
  );
}
