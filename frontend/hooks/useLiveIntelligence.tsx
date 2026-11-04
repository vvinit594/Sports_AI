"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  createExplanation,
  getMatch,
  getMatchState,
  getMoments,
  getWinProbability,
  isPulseApiError,
  listMatches,
} from "@/lib/api";
import { sortMatches } from "@/lib/featured-match";
import {
  ACHIEVEMENT_COPY,
  loadLiveStore,
  saveLiveStore,
  type LiveAchievementId,
} from "@/lib/live-storage";
import { toAudienceLevel } from "@/lib/personalization";
import {
  PLAYBACK_INTERVAL_MS,
  adjacentSequence,
  nearestSequence,
  orderedSequences,
  type PlaybackSpeed,
} from "@/lib/replay";
import { useOnboarding } from "@/hooks/useOnboarding";
import type {
  AudienceLevel,
  ExplanationResponse,
  MatchDetail,
  MatchState,
  MatchSummary,
  ModelMetadataView,
  MomentsResponse,
  MomentView,
  ProbabilityPredictionView,
  WinProbabilityResponse,
} from "@/types/api";

type CatalogStatus = "idle" | "loading" | "ready" | "empty" | "error";
type ReplayStatus = "idle" | "loading" | "ready" | "error";

export type AchievementToast = {
  id: LiveAchievementId;
  title: string;
  body: string;
};

type LiveContextValue = {
  hydrated: boolean;
  catalogStatus: CatalogStatus;
  catalogError: string | null;
  matches: MatchSummary[];
  selectedMatchId: string | null;
  selectMatch: (matchId: string | null) => void;
  detail: MatchDetail | null;
  states: MatchState[];
  sequences: number[];
  sequence: number;
  currentState: MatchState | null;
  replayStatus: ReplayStatus;
  replayError: string | null;
  playing: boolean;
  speed: PlaybackSpeed;
  setSpeed: (speed: PlaybackSpeed) => void;
  play: () => void;
  pause: () => void;
  next: () => void;
  previous: () => void;
  restart: () => void;
  seek: (sequence: number) => void;
  retryReplay: () => void;
  winAvailable: boolean;
  winReason: string | null;
  predictions: ProbabilityPredictionView[];
  predictionAtSequence: ProbabilityPredictionView | null;
  winModel: ModelMetadataView | null;
  selectGraphSequence: (sequence: number) => void;
  momentsAvailable: boolean;
  momentsReason: string | null;
  moments: MomentView[];
  selectedMoment: MomentView | null;
  selectMoment: (moment: MomentView) => void;
  audience: AudienceLevel;
  setAudience: (level: AudienceLevel) => void;
  profileAudience: AudienceLevel;
  explaining: boolean;
  explanation: ExplanationResponse | null;
  explainError: string | null;
  explain: () => Promise<void>;
  achievements: LiveAchievementId[];
  toast: AchievementToast | null;
  dismissToast: () => void;
};

const LiveContext = createContext<LiveContextValue | null>(null);

const DETECTIVE_THRESHOLD = 12;

export function LiveIntelligenceProvider({ children }: { children: ReactNode }) {
  const { state: profile, hydrated: profileHydrated } = useOnboarding();
  const profileAudience = toAudienceLevel(profile.selectedLevel);

  const [hydrated, setHydrated] = useState(false);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [achievements, setAchievements] = useState<LiveAchievementId[]>([]);
  const [toast, setToast] = useState<AchievementToast | null>(null);

  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus>("idle");
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [matches, setMatches] = useState<MatchSummary[]>([]);

  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [states, setStates] = useState<MatchState[]>([]);
  const [sequence, setSequence] = useState(0);
  const [replayStatus, setReplayStatus] = useState<ReplayStatus>("idle");
  const [replayError, setReplayError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);

  const [winAvailable, setWinAvailable] = useState(false);
  const [winReason, setWinReason] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<ProbabilityPredictionView[]>([]);
  const [winModel, setWinModel] = useState<ModelMetadataView | null>(null);

  const [momentsAvailable, setMomentsAvailable] = useState(false);
  const [momentsReason, setMomentsReason] = useState<string | null>(null);
  const [moments, setMoments] = useState<MomentView[]>([]);
  const [selectedMoment, setSelectedMoment] = useState<MomentView | null>(null);

  const [audience, setAudience] = useState<AudienceLevel>(profileAudience);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);

  const exploredRef = useRef<Set<number>>(new Set());
  const sequenceRef = useRef(0);
  const playingRef = useRef(false);

  useEffect(() => {
    const stored = loadLiveStore();
    setSelectedMatchId(stored.selectedMatchId);
    setAchievements(stored.achievements);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (profileHydrated) {
      setAudience(profileAudience);
    }
  }, [profileHydrated, profileAudience]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    saveLiveStore({ selectedMatchId, achievements });
  }, [hydrated, selectedMatchId, achievements]);

  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      setCatalogStatus("loading");
      try {
        const response = await listMatches();
        if (cancelled) {
          return;
        }
        const ordered = sortMatches(response.matches);
        setMatches(ordered);
        setCatalogStatus(ordered.length ? "ready" : "empty");
      } catch (error) {
        if (cancelled) {
          return;
        }
        setCatalogError(
          isPulseApiError(error)
            ? error.message
            : "Could not load the historical match catalog.",
        );
        setCatalogStatus("error");
      }
    }
    void loadCatalog();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    sequenceRef.current = sequence;
  }, [sequence]);

  useEffect(() => {
    playingRef.current = playing;
  }, [playing]);

  useEffect(() => {
    if (!selectedMatchId) {
      setDetail(null);
      setStates([]);
      setSequence(0);
      setPlaying(false);
      setReplayStatus("idle");
      setReplayError(null);
      setPredictions([]);
      setWinAvailable(false);
      setWinReason(null);
      setWinModel(null);
      setMoments([]);
      setMomentsAvailable(false);
      setMomentsReason(null);
      setSelectedMoment(null);
      setExplanation(null);
      setExplainError(null);
      exploredRef.current = new Set();
      return;
    }

    let cancelled = false;
    async function loadMatch(matchId: string) {
      setReplayStatus("loading");
      setReplayError(null);
      setPlaying(false);
      setExplanation(null);
      setExplainError(null);
      setSelectedMoment(null);
      exploredRef.current = new Set();
      try {
        const [match, reconstructed, probability, momentResponse] = await Promise.all([
          getMatch(matchId),
          getMatchState(matchId, undefined, { full: true }),
          getWinProbability(matchId).catch((error) => error),
          getMoments(matchId).catch((error) => error),
        ]);
        if (cancelled) {
          return;
        }
        const fullStates =
          reconstructed.states && reconstructed.states.length > 0
            ? reconstructed.states
            : [reconstructed.state];
        const start = fullStates[0]?.sequence ?? 0;
        setDetail(match);
        setStates(fullStates);
        setSequence(start);
        sequenceRef.current = start;
        setReplayStatus("ready");

        if (isPulseApiError(probability) || !isWinProbabilityResponse(probability)) {
          setWinAvailable(false);
          setWinReason(
            isPulseApiError(probability)
              ? probability.message
              : "Win probability could not be loaded.",
          );
          setPredictions([]);
          setWinModel(null);
        } else {
          setWinAvailable(probability.available);
          setWinReason(probability.unavailable_reason);
          setPredictions(probability.predictions);
          setWinModel(probability.model);
        }

        if (isPulseApiError(momentResponse) || !isMomentsResponse(momentResponse)) {
          setMomentsAvailable(false);
          setMomentsReason(
            isPulseApiError(momentResponse)
              ? momentResponse.message
              : "Significant moments could not be loaded.",
          );
          setMoments([]);
        } else {
          setMomentsAvailable(momentResponse.available);
          setMomentsReason(momentResponse.unavailable_reason);
          setMoments(momentResponse.moments);
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setReplayStatus("error");
        setReplayError(
          isPulseApiError(error)
            ? error.message
            : "This historical reconstruction could not be loaded.",
        );
        setDetail(null);
        setStates([]);
      }
    }
    void loadMatch(selectedMatchId);
    return () => {
      cancelled = true;
    };
  }, [selectedMatchId, reloadToken]);

  const sequences = useMemo(() => orderedSequences(states), [states]);
  const currentState = useMemo(
    () => states.find((item) => item.sequence === sequence) ?? states[0] ?? null,
    [states, sequence],
  );
  const predictionAtSequence = useMemo(
    () => predictions.find((item) => item.sequence === sequence) ?? null,
    [predictions, sequence],
  );

  const unlock = useCallback((id: LiveAchievementId) => {
    setAchievements((current) => {
      if (current.includes(id)) {
        return current;
      }
      const copy = ACHIEVEMENT_COPY[id];
      setToast({ id, title: copy.title, body: copy.body });
      return [...current, id];
    });
  }, []);

  const noteExploration = useCallback(
    (nextSequence: number, latest: number | undefined) => {
      exploredRef.current.add(nextSequence);
      if (exploredRef.current.size >= DETECTIVE_THRESHOLD) {
        unlock("match_detective");
      }
      if (latest != null && nextSequence === latest) {
        unlock("full_replay");
      }
    },
    [unlock],
  );

  const seek = useCallback(
    (nextSequence: number) => {
      const supported = nearestSequence(sequences, nextSequence);
      if (supported == null) {
        return;
      }
      setSequence(supported);
      setExplanation(null);
      setExplainError(null);
      noteExploration(supported, sequences[sequences.length - 1]);
      const moment = moments.find((item) => item.sequence === supported) ?? null;
      setSelectedMoment(moment);
    },
    [moments, noteExploration, sequences],
  );

  const play = useCallback(() => {
    const last = sequences[sequences.length - 1];
    if (last == null || sequence === last) {
      return;
    }
    setPlaying(true);
  }, [sequence, sequences]);

  const pause = useCallback(() => {
    setPlaying(false);
  }, []);

  const next = useCallback(() => {
    const upcoming = adjacentSequence(sequences, sequence, 1);
    if (upcoming != null) {
      seek(upcoming);
    }
  }, [seek, sequence, sequences]);

  const previous = useCallback(() => {
    const prior = adjacentSequence(sequences, sequence, -1);
    if (prior != null) {
      seek(prior);
    }
  }, [seek, sequence, sequences]);

  const restart = useCallback(() => {
    setPlaying(false);
    const first = sequences[0];
    if (first != null) {
      seek(first);
    }
  }, [seek, sequences]);

  useEffect(() => {
    if (!playing || sequences.length === 0) {
      return;
    }
    const last = sequences[sequences.length - 1];
    const timer = window.setInterval(() => {
      const current = sequenceRef.current;
      const upcoming = adjacentSequence(sequences, current, 1);
      if (upcoming == null || current === last) {
        playingRef.current = false;
        setPlaying(false);
        if (last != null) {
          seek(last);
        }
        return;
      }
      seek(upcoming);
    }, PLAYBACK_INTERVAL_MS[speed]);
    return () => window.clearInterval(timer);
  }, [playing, sequences, seek, speed]);

  const selectMatch = useCallback((matchId: string | null) => {
    setSelectedMatchId(matchId);
    setAudience(profileAudience);
  }, [profileAudience]);

  const selectMoment = useCallback(
    (moment: MomentView) => {
      unlock("momentum_hunter");
      seek(moment.sequence);
      setSelectedMoment(moment);
    },
    [seek, unlock],
  );

  const selectGraphSequence = useCallback(
    (nextSequence: number) => {
      unlock("cricket_strategist");
      seek(nextSequence);
    },
    [seek, unlock],
  );

  const explain = useCallback(async () => {
    if (!selectedMatchId || explaining) {
      return;
    }
    if (!sequences.includes(sequence)) {
      setExplainError("Select a reconstructed delivery before requesting an explanation.");
      return;
    }
    setExplaining(true);
    setExplainError(null);
    try {
      const response = await createExplanation(selectedMatchId, audience, sequence);
      setExplanation(response);
    } catch (error) {
      setExplanation(null);
      setExplainError(
        isPulseApiError(error)
          ? error.message
          : "PulseIQ could not explain this reconstructed moment.",
      );
    } finally {
      setExplaining(false);
    }
  }, [audience, explaining, selectedMatchId, sequence, sequences]);

  const value = useMemo<LiveContextValue>(
    () => ({
      hydrated,
      catalogStatus,
      catalogError,
      matches,
      selectedMatchId,
      selectMatch,
      detail,
      states,
      sequences,
      sequence,
      currentState,
      replayStatus,
      replayError,
      playing,
      speed,
      setSpeed,
      play,
      pause,
      next,
      previous,
      restart,
      seek,
      retryReplay: () => setReloadToken((token) => token + 1),
      winAvailable,
      winReason,
      predictions,
      predictionAtSequence,
      winModel,
      selectGraphSequence,
      momentsAvailable,
      momentsReason,
      moments,
      selectedMoment,
      selectMoment,
      audience,
      setAudience,
      profileAudience,
      explaining,
      explanation,
      explainError,
      explain,
      achievements,
      toast,
      dismissToast: () => setToast(null),
    }),
    [
      achievements,
      audience,
      catalogError,
      catalogStatus,
      currentState,
      detail,
      explain,
      explainError,
      explaining,
      explanation,
      hydrated,
      matches,
      moments,
      momentsAvailable,
      momentsReason,
      next,
      pause,
      play,
      playing,
      predictionAtSequence,
      predictions,
      previous,
      profileAudience,
      restart,
      replayError,
      replayStatus,
      seek,
      selectGraphSequence,
      selectMatch,
      selectMoment,
      selectedMatchId,
      selectedMoment,
      sequence,
      sequences,
      speed,
      states,
      toast,
      winAvailable,
      winModel,
      winReason,
    ],
  );

  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export function useLiveIntelligence() {
  const context = useContext(LiveContext);
  if (!context) {
    throw new Error("useLiveIntelligence must be used within LiveIntelligenceProvider");
  }
  return context;
}

function isWinProbabilityResponse(value: unknown): value is WinProbabilityResponse {
  return Boolean(
    value &&
      typeof value === "object" &&
      "available" in value &&
      "predictions" in value,
  );
}

function isMomentsResponse(value: unknown): value is MomentsResponse {
  return Boolean(
    value &&
      typeof value === "object" &&
      "available" in value &&
      "moments" in value,
  );
}
