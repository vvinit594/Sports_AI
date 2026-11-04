"use client";

import { useEffect } from "react";

import { AskPulseIQ } from "@/components/dashboard/AskPulseIQ";
import { CricketIQ } from "@/components/dashboard/CricketIQ";
import { FeaturedMatch } from "@/components/dashboard/FeaturedMatch";
import { InsightGrid } from "@/components/dashboard/InsightGrid";
import { MatchCarousel } from "@/components/dashboard/MatchCarousel";
import { PersonalizedHeader } from "@/components/dashboard/PersonalizedHeader";
import { SectionSkeleton, StatusPanel } from "@/components/dashboard/StatusPanel";
import { TrendingMoments } from "@/components/dashboard/TrendingMoments";
import { useDashboardData } from "@/hooks/useDashboardData";
import { useOnboarding } from "@/hooks/useOnboarding";
import { useProgress } from "@/hooks/useProgress";

export function InsightsDashboard() {
  const { state: profile, hydrated } = useOnboarding();
  const { markVisit } = useProgress();
  const data = useDashboardData(
    profile.favouriteTeam,
    profile.selectedLevel,
    hydrated,
  );

  useEffect(() => {
    if (hydrated) {
      markVisit();
    }
  }, [hydrated, markVisit]);

  if (!hydrated || data.catalogState === "loading" || data.catalogState === "idle") {
    return (
      <div className="space-y-6">
        <SectionSkeleton label="personalized header" />
        <SectionSkeleton label="featured match" />
        <SectionSkeleton label="insights" />
      </div>
    );
  }

  if (data.catalogState === "error") {
    return (
      <>
        <PersonalizedHeader profile={profile} />
        <StatusPanel
          tone="error"
          title="Match catalog unavailable"
          body={
            data.catalogError ??
            "The PulseIQ API did not return historical matches. Start FastAPI on port 8000."
          }
        />
        <CricketIQ />
      </>
    );
  }

  if (data.catalogState === "empty" || !data.featured) {
    return (
      <>
        <PersonalizedHeader profile={profile} />
        <StatusPanel
          title="No historical matches loaded"
          body="The catalog directory is empty or could not be scanned. PulseIQ will not invent a fixture list."
        />
        <CricketIQ />
      </>
    );
  }

  const insightMoment = data.featuredMoments?.moments[0] ?? null;
  const askMoment = insightMoment ?? data.trending[0] ?? null;

  return (
    <div>
      <PersonalizedHeader profile={profile} />
      <FeaturedMatch
        match={data.featured}
        detail={data.featuredDetail}
        state={data.featuredState}
      />
      <InsightGrid
        level={profile.selectedLevel}
        featured={data.featured}
        state={data.featuredState}
        moment={insightMoment}
        momentsUnavailableReason={data.momentsUnavailableReason}
        explanation={data.featuredExplanation}
        explanationError={data.explanationError}
      />
      <MatchCarousel matches={data.matches} />
      <TrendingMoments
        level={profile.selectedLevel}
        moments={data.trending}
        matches={data.matches}
        unavailableReason={data.momentsUnavailableReason}
        loaded={data.momentsLoaded}
        evaluationLimitation={data.evaluationLimitation}
      />
      <CricketIQ />
      <AskPulseIQ
        level={profile.selectedLevel}
        featured={data.featured}
        moment={askMoment}
      />
    </div>
  );
}
