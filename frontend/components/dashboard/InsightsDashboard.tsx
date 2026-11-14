"use client";

import { useEffect, useState } from "react";

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
  const [slowCatalog, setSlowCatalog] = useState(false);

  useEffect(() => {
    if (hydrated) {
      markVisit();
    }
  }, [hydrated, markVisit]);

  useEffect(() => {
    if (data.catalogState !== "loading" && data.catalogState !== "idle") {
      setSlowCatalog(false);
      return;
    }
    const timer = window.setTimeout(() => setSlowCatalog(true), 3000);
    return () => window.clearTimeout(timer);
  }, [data.catalogState]);

  if (!hydrated) {
    return (
      <div className="space-y-6">
        <SectionSkeleton label="personalized header" />
        <SectionSkeleton label="featured match" />
      </div>
    );
  }

  const catalogPending =
    data.catalogState === "loading" || data.catalogState === "idle";
  const catalogReady = data.catalogState === "ready" && data.featured;

  const insightMoment = data.featuredMoments?.moments[0] ?? null;
  const askMoment = insightMoment ?? data.trending[0] ?? null;

  return (
    <div>
      <PersonalizedHeader profile={profile} />

      {catalogPending ? (
        <div className="space-y-4">
          <SectionSkeleton label="featured match" />
          {slowCatalog ? (
            <p className="text-sm text-muted" role="status">
              Connecting to PulseIQ intelligence…
            </p>
          ) : null}
          <SectionSkeleton label="insights" />
        </div>
      ) : null}

      {data.catalogState === "error" ? (
        <StatusPanel
          tone="error"
          title="Match catalog unavailable"
          body={
            data.catalogError ??
            "The PulseIQ API did not return historical matches. Start FastAPI on port 8000."
          }
        />
      ) : null}

      {data.catalogState === "empty" || (data.catalogState === "ready" && !data.featured) ? (
        <StatusPanel
          title="No historical matches loaded"
          body="The catalog directory is empty or could not be scanned. PulseIQ will not invent a fixture list."
        />
      ) : null}

      {catalogReady && data.featured ? (
        <>
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
            featuredMomentsLoaded={data.featuredMomentsLoaded}
            momentsUnavailableReason={data.momentsUnavailableReason}
            explanation={data.featuredExplanation}
            explanationState={data.explanationState}
            explanationError={data.explanationError}
          />
          <MatchCarousel matches={data.matches} />
          <TrendingMoments
            level={profile.selectedLevel}
            moments={data.trending}
            matches={data.matches}
            unavailableReason={data.momentsUnavailableReason}
            loaded={data.momentsLoaded}
            loading={data.momentsLoading}
            evaluationLimitation={data.evaluationLimitation}
            onApproach={data.ensureTrending}
          />
        </>
      ) : null}

      {!catalogPending ? <CricketIQ /> : null}
      {catalogReady && data.featured ? (
        <AskPulseIQ
          level={profile.selectedLevel}
          featured={data.featured}
          moment={askMoment}
        />
      ) : null}
    </div>
  );
}
