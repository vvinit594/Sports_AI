"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_PROGRESS,
  loadProgress,
  saveProgress,
  todayKey,
  type LocalProgress,
} from "@/lib/progress-storage";

type ProgressContextValue = {
  progress: LocalProgress;
  hydrated: boolean;
  markVisit: () => void;
  markMatchExplored: (matchId: string) => void;
  markMomentRead: (matchId: string, sequence: number) => void;
  markTopicCompleted: (topicId: string) => void;
  markAskedPulseIQ: () => void;
};

const ProgressContext = createContext<ProgressContextValue | null>(null);

export function ProgressProvider({ children }: { children: ReactNode }) {
  const [progress, setProgress] = useState<LocalProgress>(DEFAULT_PROGRESS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setProgress(loadProgress());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    saveProgress(progress);
  }, [hydrated, progress]);

  const markVisit = useCallback(() => {
    const today = todayKey();
    setProgress((current) =>
      current.visitDates.includes(today)
        ? current
        : { ...current, visitDates: [...current.visitDates, today] },
    );
  }, []);

  const markMatchExplored = useCallback((matchId: string) => {
    setProgress((current) =>
      current.exploredMatchIds.includes(matchId)
        ? current
        : { ...current, exploredMatchIds: [...current.exploredMatchIds, matchId] },
    );
  }, []);

  const markMomentRead = useCallback((matchId: string, sequence: number) => {
    const key = `${matchId}:${sequence}`;
    setProgress((current) =>
      current.readMomentKeys.includes(key)
        ? current
        : { ...current, readMomentKeys: [...current.readMomentKeys, key] },
    );
  }, []);

  const markTopicCompleted = useCallback((topicId: string) => {
    setProgress((current) =>
      current.completedTopicIds.includes(topicId)
        ? current
        : { ...current, completedTopicIds: [...current.completedTopicIds, topicId] },
    );
  }, []);

  const markAskedPulseIQ = useCallback(() => {
    setProgress((current) =>
      current.askedPulseIQ ? current : { ...current, askedPulseIQ: true },
    );
  }, []);

  const value = useMemo(
    () => ({
      progress,
      hydrated,
      markVisit,
      markMatchExplored,
      markMomentRead,
      markTopicCompleted,
      markAskedPulseIQ,
    }),
    [
      hydrated,
      markAskedPulseIQ,
      markMatchExplored,
      markMomentRead,
      markTopicCompleted,
      markVisit,
      progress,
    ],
  );

  return (
    <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>
  );
}

export function useProgress() {
  const context = useContext(ProgressContext);
  if (!context) {
    throw new Error("useProgress must be used within ProgressProvider");
  }
  return context;
}
