"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createExplanation,
  getMatch,
  getMatchState,
  getMoments,
  isPulseApiError,
  listMatches,
  peekCachedMatches,
} from "@/lib/api";
import { selectFeaturedMatch, sortMatches } from "@/lib/featured-match";
import { toAudienceLevel } from "@/lib/personalization";
import { TRENDING_MOMENT_CONCURRENCY, mapWithConcurrency } from "@/lib/request-cache";
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
export type ExplanationState = "idle" | "loading" | "ready" | "error";

export type DashboardSnapshot = {
  catalogState: LoadState;
  catalogError: string | null;
  matches: MatchSummary[];
  featured: MatchSummary | null;
  featuredDetail: MatchDetail | null;
  featuredState: MatchState | null;
  featuredMoments: MomentsResponse | null;
  featuredMomentsLoaded: boolean;
  featuredExplanation: ExplanationResponse | null;
  explanationState: ExplanationState;
  explanationError: string | null;
  trending: MomentView[];
  momentsUnavailableReason: string | null;
  momentsLoaded: boolean;
  momentsLoading: boolean;
  evaluationLimitation: string | null;
};

export type DashboardData = DashboardSnapshot & {
  ensureTrending: () => void;
};

const EMPTY: DashboardSnapshot = {
  catalogState: "idle",
  catalogError: null,
  matches: [],
  featured: null,
  featuredDetail: null,
  featuredState: null,
  featuredMoments: null,
  featuredMomentsLoaded: false,
  featuredExplanation: null,
  explanationState: "idle",
  explanationError: null,
  trending: [],
  momentsUnavailableReason: null,
  momentsLoaded: false,
  momentsLoading: false,
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

function collectTrending(sets: Array<MomentsResponse | null>): {
  trending: MomentView[];
  unavailableReason: string | null;
  evaluationLimitation: string | null;
} {
  const available = sets.filter(
    (item): item is MomentsResponse => item?.available === true,
  );
  const unavailable = sets.find((item) => item && item.available === false);
  return {
    trending: available
      .flatMap((item) => item.moments)
      .sort(
        (left, right) =>
          Math.abs(right.probability_change) - Math.abs(left.probability_change),
      )
      .slice(0, 8),
    unavailableReason: available.length
      ? null
      : (unavailable?.unavailable_reason ?? null),
    evaluationLimitation:
      available.find((item) => item.model?.evaluation_limitation)?.model
        ?.evaluation_limitation ??
      unavailable?.model?.evaluation_limitation ??
      null,
  };
}

function snapshotFromCatalog(
  favouriteTeam: string | null,
  catalogState: LoadState = "loading",
): DashboardSnapshot {
  const cached = peekCachedMatches();
  if (!cached) {
    return { ...EMPTY, catalogState };
  }
  const matches = sortMatches(cached.matches);
  if (matches.length === 0) {
    return { ...EMPTY, catalogState: "empty" };
  }
  const featured = selectFeaturedMatch(matches, favouriteTeam);
  if (!featured) {
    return { ...EMPTY, catalogState: "empty", matches };
  }
  return {
    ...EMPTY,
    catalogState: "ready",
    matches,
    featured,
  };
}

export function useDashboardData(
  favouriteTeam: string | null,
  level: ExperienceLevel | null,
  enabled = true,
): DashboardData {
  const [data, setData] = useState<DashboardSnapshot>(() =>
    enabled
      ? snapshotFromCatalog(favouriteTeam)
      : { ...EMPTY, catalogState: "loading" },
  );
  const generationRef = useRef(0);
  const matchesRef = useRef<MatchSummary[]>(data.matches);
  const featuredRef = useRef<MatchSummary | null>(data.featured);
  const featuredMomentsRef = useRef<MomentsResponse | null>(null);
  const restMomentsRef = useRef<Array<MomentsResponse | null>>([]);
  const trendingStartedRef = useRef(false);
  const trendingWantedRef = useRef(false);
  const restLoadedRef = useRef(false);

  const isCurrent = useCallback((generation: number) => {
    return generationRef.current === generation;
  }, []);

  const patch = useCallback((generation: number, partial: Partial<DashboardSnapshot>) => {
    if (!isCurrent(generation)) {
      return;
    }
    setData((current) => ({ ...current, ...partial }));
  }, [isCurrent]);

  const publishTrending = useCallback(
    (generation: number) => {
      if (!isCurrent(generation)) {
        return;
      }
      const collected = collectTrending([
        featuredMomentsRef.current,
        ...restMomentsRef.current,
      ]);
      patch(generation, {
        trending: collected.trending,
        momentsUnavailableReason: collected.unavailableReason,
        evaluationLimitation:
          collected.evaluationLimitation ??
          featuredMomentsRef.current?.model?.evaluation_limitation ??
          null,
        momentsLoaded: restLoadedRef.current,
        momentsLoading: trendingStartedRef.current && !restLoadedRef.current,
      });
    },
    [isCurrent, patch],
  );

  const loadExplanation = useCallback(
    async (
      generation: number,
      matchId: string,
      experienceLevel: ExperienceLevel | null,
      moments: MomentsResponse | null,
    ) => {
      if (!isCurrent(generation)) {
        return;
      }
      patch(generation, {
        explanationState: "loading",
        explanationError: null,
        featuredExplanation: null,
      });
      try {
        const sequence =
          moments?.available && moments.moments[0]
            ? moments.moments[0].sequence
            : undefined;
        const explanation = await createExplanation(
          matchId,
          toAudienceLevel(experienceLevel),
          sequence,
        );
        patch(generation, {
          explanationState: "ready",
          featuredExplanation: explanation,
          explanationError: null,
        });
      } catch (error) {
        patch(generation, {
          explanationState: "error",
          featuredExplanation: null,
          explanationError: errorMessage(error),
        });
      }
    },
    [isCurrent, patch],
  );

  const loadTrending = useCallback(
    async (generation: number) => {
      if (!isCurrent(generation) || trendingStartedRef.current) {
        return;
      }
      const matches = matchesRef.current;
      const featured = featuredRef.current;
      if (!matches.length || !featured) {
        return;
      }
      trendingStartedRef.current = true;
      restLoadedRef.current = false;
      patch(generation, { momentsLoading: true, momentsLoaded: false });

      const remaining = matches.filter(
        (match) => match.source_match_id !== featured.source_match_id,
      );
      const rest = await mapWithConcurrency(
        remaining,
        TRENDING_MOMENT_CONCURRENCY,
        async (match) => {
          if (!isCurrent(generation)) {
            return null;
          }
          try {
            return await getMoments(match.source_match_id);
          } catch {
            return null;
          }
        },
      );
      if (!isCurrent(generation)) {
        return;
      }
      restMomentsRef.current = rest;
      restLoadedRef.current = true;
      publishTrending(generation);
    },
    [isCurrent, patch, publishTrending],
  );

  const ensureTrending = useCallback(() => {
    trendingWantedRef.current = true;
    void loadTrending(generationRef.current);
  }, [loadTrending]);

  useEffect(() => {
    if (!enabled) {
      setData({ ...EMPTY, catalogState: "loading" });
      return;
    }

    const generation = generationRef.current + 1;
    generationRef.current = generation;
    trendingStartedRef.current = false;
    restLoadedRef.current = false;
    restMomentsRef.current = [];
    featuredMomentsRef.current = null;

    setData((current) => {
      if (current.catalogState === "ready" && current.matches.length > 0) {
        const featured = selectFeaturedMatch(current.matches, favouriteTeam);
        matchesRef.current = current.matches;
        featuredRef.current = featured;
        return {
          ...current,
          featured,
          featuredDetail: null,
          featuredState: null,
          featuredMoments: null,
          featuredMomentsLoaded: false,
          featuredExplanation: null,
          explanationState: "loading",
          explanationError: null,
          trending: [],
          momentsLoaded: false,
          momentsLoading: false,
          momentsUnavailableReason: null,
        };
      }
      const fromCache = snapshotFromCatalog(favouriteTeam);
      matchesRef.current = fromCache.matches;
      featuredRef.current = fromCache.featured;
      return fromCache.catalogState === "ready"
        ? { ...fromCache, explanationState: "loading" }
        : { ...EMPTY, catalogState: "loading" };
    });

    let cancelled = false;

    async function loadPrimary() {
      try {
        const catalog = await listMatches();
        if (cancelled || !isCurrent(generation)) {
          return;
        }
        const matches = sortMatches(catalog.matches);
        matchesRef.current = matches;
        if (matches.length === 0) {
          setData({ ...EMPTY, catalogState: "empty" });
          return;
        }
        const featured = selectFeaturedMatch(matches, favouriteTeam);
        featuredRef.current = featured;
        if (!featured) {
          setData({ ...EMPTY, catalogState: "empty", matches });
          return;
        }

        patch(generation, {
          catalogState: "ready",
          catalogError: null,
          matches,
          featured,
          explanationState: "loading",
        });

        if (trendingWantedRef.current) {
          void loadTrending(generation);
        }

        const [detailResult, stateResult, featuredMomentsResult] = await Promise.all([
          getMatch(featured.source_match_id).catch(() => null),
          getMatchState(featured.source_match_id).catch(() => null),
          getMoments(featured.source_match_id).catch(() => null),
        ]);
        if (cancelled || !isCurrent(generation)) {
          return;
        }

        featuredMomentsRef.current = featuredMomentsResult;
        patch(generation, {
          featuredDetail: detailResult,
          featuredState: stateResult?.state ?? null,
          featuredMoments: featuredMomentsResult,
          featuredMomentsLoaded: true,
          evaluationLimitation:
            featuredMomentsResult?.model?.evaluation_limitation ?? null,
          momentsUnavailableReason:
            featuredMomentsResult?.available === false
              ? featuredMomentsResult.unavailable_reason
              : null,
        });
        if (trendingStartedRef.current) {
          publishTrending(generation);
        }

        void loadExplanation(
          generation,
          featured.source_match_id,
          level,
          featuredMomentsResult,
        );

        if (trendingWantedRef.current) {
          void loadTrending(generation);
        }
      } catch (error) {
        if (cancelled || !isCurrent(generation)) {
          return;
        }
        setData({
          ...EMPTY,
          catalogState: "error",
          catalogError: errorMessage(error),
        });
      }
    }

    void loadPrimary();
    return () => {
      cancelled = true;
    };
  }, [
    enabled,
    favouriteTeam,
    isCurrent,
    level,
    loadExplanation,
    loadTrending,
    patch,
    publishTrending,
  ]);

  return useMemo(
    () => ({
      ...data,
      ensureTrending,
    }),
    [data, ensureTrending],
  );
}
