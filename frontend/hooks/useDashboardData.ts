"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createExplanation,
  getMatch,
  getMatchState,
  getMoments,
  isPulseApiError,
  listMatches,
} from "@/lib/api";
import { selectFeaturedMatch, sortMatches } from "@/lib/featured-match";
import { toAudienceLevel } from "@/lib/personalization";
import type {
  ExplanationResponse,
  MatchDetail,
  MatchState,
  MatchSummary,
  MomentView,
  MomentsResponse,
} from "@/types/api";
import type { ExperienceLevel } from "@/types/onboarding";

export type LoadState = "idle" | "loading" | "ready" | "empty" | "error";

export type DashboardData = {
  catalogState: LoadState;
  catalogError: string | null;
  matches: MatchSummary[];
  featured: MatchSummary | null;
  featuredDetail: MatchDetail | null;
  featuredState: MatchState | null;
  featuredMoments: MomentsResponse | null;
  featuredExplanation: ExplanationResponse | null;
  explanationError: string | null;
  trending: MomentView[];
  momentsUnavailableReason: string | null;
  momentsLoaded: boolean;
  evaluationLimitation: string | null;
};

const EMPTY: DashboardData = {
  catalogState: "idle",
  catalogError: null,
  matches: [],
  featured: null,
  featuredDetail: null,
  featuredState: null,
  featuredMoments: null,
  featuredExplanation: null,
  explanationError: null,
  trending: [],
  momentsUnavailableReason: null,
  momentsLoaded: false,
  evaluationLimitation: null,
};

function errorMessage(error: unknown): string {
  if (isPulseApiError(error)) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong loading cricket intelligence.";
}

export function useDashboardData(
  favouriteTeam: string | null,
  level: ExperienceLevel | null,
  enabled = true,
): DashboardData {
  const [data, setData] = useState<DashboardData>({
    ...EMPTY,
    catalogState: "loading",
  });

  useEffect(() => {
    if (!enabled) {
      setData({ ...EMPTY, catalogState: "loading" });
      return;
    }

    let cancelled = false;

    async function load() {
      setData({ ...EMPTY, catalogState: "loading" });
      try {
        const catalog = await listMatches();
        const matches = sortMatches(catalog.matches);
        if (cancelled) {
          return;
        }
        if (matches.length === 0) {
          setData({ ...EMPTY, catalogState: "empty" });
          return;
        }
        const featured = selectFeaturedMatch(matches, favouriteTeam);
        if (!featured) {
          setData({ ...EMPTY, catalogState: "empty", matches });
          return;
        }

        const [detailResult, stateResult, featuredMomentsResult, momentResults] =
          await Promise.all([
            getMatch(featured.source_match_id).catch(() => null),
            getMatchState(featured.source_match_id).catch(() => null),
            getMoments(featured.source_match_id).catch(() => null),
            Promise.all(
              matches.map(async (match) => {
                try {
                  return await getMoments(match.source_match_id);
                } catch {
                  return null;
                }
              }),
            ),
          ]);

        if (cancelled) {
          return;
        }

        const availableMomentSets = momentResults.filter(
          (item): item is MomentsResponse => item?.available === true,
        );
        const unavailable = momentResults.find(
          (item) => item && item.available === false,
        );
        const trending = availableMomentSets
          .flatMap((item) => item.moments)
          .sort(
            (left, right) =>
              Math.abs(right.probability_change) - Math.abs(left.probability_change),
          )
          .slice(0, 8);

        let explanation: ExplanationResponse | null = null;
        let explanationError: string | null = null;
        try {
          const sequence =
            featuredMomentsResult?.available && featuredMomentsResult.moments[0]
              ? featuredMomentsResult.moments[0].sequence
              : undefined;
          explanation = await createExplanation(
            featured.source_match_id,
            toAudienceLevel(level),
            sequence,
          );
        } catch (error) {
          explanationError = errorMessage(error);
        }

        if (cancelled) {
          return;
        }

        setData({
          catalogState: "ready",
          catalogError: null,
          matches,
          featured,
          featuredDetail: detailResult,
          featuredState: stateResult?.state ?? null,
          featuredMoments: featuredMomentsResult,
          featuredExplanation: explanation,
          explanationError,
          trending,
          momentsUnavailableReason: availableMomentSets.length
            ? null
            : unavailable?.unavailable_reason ?? null,
          momentsLoaded: true,
          evaluationLimitation:
            availableMomentSets.find((item) => item.model?.evaluation_limitation)
              ?.model?.evaluation_limitation ??
            featuredMomentsResult?.model?.evaluation_limitation ??
            null,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setData({
          ...EMPTY,
          catalogState: "error",
          catalogError: errorMessage(error),
        });
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [enabled, favouriteTeam, level]);

  return useMemo(() => data, [data]);
}
