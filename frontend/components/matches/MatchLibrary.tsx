"use client";

import { useEffect, useState } from "react";

import { MatchCard } from "@/components/dashboard/MatchCard";
import { SectionSkeleton, StatusPanel } from "@/components/dashboard/StatusPanel";
import { isPulseApiError, listMatches } from "@/lib/api";
import { sortMatches } from "@/lib/featured-match";
import type { MatchSummary } from "@/types/api";

export function MatchLibrary() {
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">(
    "loading",
  );
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await listMatches();
        if (cancelled) {
          return;
        }
        const ordered = sortMatches(response.matches);
        setMatches(ordered);
        setState(ordered.length ? "ready" : "empty");
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setError(
          isPulseApiError(caught)
            ? caught.message
            : "Could not load the historical match library.",
        );
        setState("error");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Match library
      </p>
      <h1 className="mt-3 text-4xl font-bold uppercase sm:text-6xl">
        Historical matches
      </h1>
      <p className="mt-3 max-w-2xl text-white/75">
        Every Cricsheet sample currently loaded by the PulseIQ API. These fixtures
        are completed historical matches, not a live schedule.
      </p>
      {state === "loading" ? <div className="mt-8"><SectionSkeleton label="match library" /></div> : null}
      {state === "error" ? (
        <div className="mt-8">
          <StatusPanel
            tone="error"
            title="Library unavailable"
            body={error ?? "The match catalog could not be reached."}
          />
        </div>
      ) : null}
      {state === "empty" ? (
        <div className="mt-8">
          <StatusPanel
            title="No matches in the catalog"
            body="The API returned an empty historical list. PulseIQ will not invent fixtures."
          />
        </div>
      ) : null}
      {state === "ready" ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {matches.map((match) => (
            <MatchCard key={match.source_match_id} match={match} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
