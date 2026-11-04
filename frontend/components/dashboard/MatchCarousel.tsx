import Link from "next/link";

import { MatchCard } from "@/components/dashboard/MatchCard";
import { Button } from "@/components/ui/Button";
import type { MatchSummary } from "@/types/api";

type MatchCarouselProps = {
  matches: MatchSummary[];
};

export function MatchCarousel({ matches }: MatchCarouselProps) {
  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
            Historical catalog
          </p>
          <h2 className="mt-2 text-3xl font-bold uppercase">Explore historical matches</h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Every match currently loaded from the Cricsheet sample directory, not a
            curated shortlist.
          </p>
        </div>
        <Link href="/matches">
          <Button variant="outline">View all matches</Button>
        </Link>
      </div>
      <div className="mt-6 flex snap-x gap-4 overflow-x-auto pb-3 md:grid md:grid-cols-2 md:overflow-visible lg:grid-cols-3">
        {matches.map((match) => (
          <MatchCard key={match.source_match_id} match={match} compact />
        ))}
      </div>
    </section>
  );
}
