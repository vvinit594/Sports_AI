export type LiveAchievementId =
  | "momentum_hunter"
  | "match_detective"
  | "cricket_strategist"
  | "full_replay";

export type LiveStore = {
  selectedMatchId: string | null;
  achievements: LiveAchievementId[];
};

export const LIVE_STORAGE_KEY = "pulseiq.live.v1";

export const ACHIEVEMENT_COPY: Record<
  LiveAchievementId,
  { title: string; body: string }
> = {
  momentum_hunter: {
    title: "Momentum Hunter",
    body: "You opened a detected significant moment.",
  },
  match_detective: {
    title: "Match Detective",
    body: "You inspected multiple reconstructed deliveries.",
  },
  cricket_strategist: {
    title: "Cricket Strategist",
    body: "You explored the win-probability graph.",
  },
  full_replay: {
    title: "Full Replay",
    body: "You reached the end of this historical reconstruction.",
  },
};

const EMPTY: LiveStore = {
  selectedMatchId: null,
  achievements: [],
};

const ACHIEVEMENTS: LiveAchievementId[] = [
  "momentum_hunter",
  "match_detective",
  "cricket_strategist",
  "full_replay",
];

export function loadLiveStore(): LiveStore {
  if (typeof window === "undefined") {
    return EMPTY;
  }
  try {
    const raw = window.localStorage.getItem(LIVE_STORAGE_KEY);
    if (!raw) {
      return EMPTY;
    }
    return sanitizeLiveStore(JSON.parse(raw));
  } catch {
    return EMPTY;
  }
}

export function saveLiveStore(store: LiveStore): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      LIVE_STORAGE_KEY,
      JSON.stringify(sanitizeLiveStore(store)),
    );
  } catch {
    // Quota / private-mode failures must not break replay.
  }
}

export function sanitizeLiveStore(value: unknown): LiveStore {
  if (!value || typeof value !== "object") {
    return EMPTY;
  }
  const record = value as Record<string, unknown>;
  const selected =
    typeof record.selectedMatchId === "string" && record.selectedMatchId.trim()
      ? record.selectedMatchId
      : null;
  const achievements = Array.isArray(record.achievements)
    ? record.achievements.filter((item): item is LiveAchievementId =>
        ACHIEVEMENTS.includes(item as LiveAchievementId),
      )
    : [];
  return {
    selectedMatchId: selected,
    achievements: [...new Set(achievements)],
  };
}
