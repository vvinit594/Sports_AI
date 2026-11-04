"use client";

import { LiveIntelligenceProvider, useLiveIntelligence } from "@/hooks/useLiveIntelligence";
import { AchievementNotification } from "@/components/live/AchievementNotification";
import { LiveMatchSelector } from "@/components/live/LiveMatchSelector";
import { MatchAnalyst } from "@/components/live/MatchAnalyst";
import { MatchScoreboard } from "@/components/live/MatchScoreboard";
import { MatchStatistics } from "@/components/live/MatchStatistics";
import { ReplayControls } from "@/components/live/ReplayControls";
import { ReplayTimeline } from "@/components/live/ReplayTimeline";
import { SignificantMoments } from "@/components/live/SignificantMoments";
import { WinProbabilityChart } from "@/components/live/WinProbabilityChart";

export function LiveIntelligencePage() {
  return (
    <LiveIntelligenceProvider>
      <LiveLayout />
    </LiveIntelligenceProvider>
  );
}

function LiveLayout() {
  const { selectedMatchId, hydrated } = useLiveIntelligence();

  return (
    <div className="space-y-6 pb-10">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
          Every ball. Every shift. Every insight.
        </p>
        <h1 className="mt-2 font-display text-4xl uppercase sm:text-6xl">
          Live Intelligence
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-white/70 sm:text-base">
          Replay reconstructed Cricsheet matches, inspect chase probability where the
          model supports it, and ask PulseIQ to explain a selected delivery. There is
          no live cricket feed in this milestone.
        </p>
      </header>

      <LiveMatchSelector />

      {!hydrated ? (
        <p className="text-sm text-muted">Restoring your last historical match…</p>
      ) : null}

      {hydrated && !selectedMatchId ? (
        <div className="rounded-[28px] border border-dashed border-white/15 bg-black/20 px-6 py-16 text-center">
          <p className="font-display text-3xl uppercase">Select a historical match</p>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted">
            Choose a reconstructed sample above to open the scoreboard, delivery replay,
            probability series and significant-moment timeline.
          </p>
        </div>
      ) : null}

      {selectedMatchId ? (
        <>
          <MatchScoreboard />
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(22rem,0.9fr)]">
            <div className="space-y-6">
              <ReplayControls />
              <ReplayTimeline />
              <WinProbabilityChart />
            </div>
            <div className="space-y-6">
              <SignificantMoments />
              <MatchAnalyst />
            </div>
          </div>
          <MatchStatistics />
        </>
      ) : null}

      <AchievementNotification />
    </div>
  );
}
