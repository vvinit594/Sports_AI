export type LocalProgress = {
  exploredMatchIds: string[];
  completedTopicIds: string[];
  readMomentKeys: string[];
  askedPulseIQ: boolean;
  visitDates: string[];
};

export const PROGRESS_STORAGE_KEY = "pulseiq.progress.v1";

export const DEFAULT_PROGRESS: LocalProgress = {
  exploredMatchIds: [],
  completedTopicIds: [],
  readMomentKeys: [],
  askedPulseIQ: false,
  visitDates: [],
};

export function todayKey(now = new Date()): string {
  return now.toISOString().slice(0, 10);
}

export function loadProgress(): LocalProgress {
  if (typeof window === "undefined") {
    return DEFAULT_PROGRESS;
  }
  try {
    const raw = window.localStorage.getItem(PROGRESS_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_PROGRESS;
    }
    return sanitizeProgress(JSON.parse(raw));
  } catch {
    return DEFAULT_PROGRESS;
  }
}

export function saveProgress(progress: LocalProgress): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      PROGRESS_STORAGE_KEY,
      JSON.stringify(sanitizeProgress(progress)),
    );
  } catch {
    // Ignore quota / private-mode failures.
  }
}

export function sanitizeProgress(value: unknown): LocalProgress {
  if (!value || typeof value !== "object") {
    return DEFAULT_PROGRESS;
  }
  const record = value as Record<string, unknown>;
  return {
    exploredMatchIds: readStringList(record.exploredMatchIds),
    completedTopicIds: readStringList(record.completedTopicIds),
    readMomentKeys: readStringList(record.readMomentKeys),
    askedPulseIQ: record.askedPulseIQ === true,
    visitDates: readStringList(record.visitDates).filter((item) =>
      /^\d{4}-\d{2}-\d{2}$/.test(item),
    ),
  };
}

export function learningStreak(visitDates: string[], today = todayKey()): number {
  const unique = [...new Set(visitDates)].sort();
  if (unique.length === 0) {
    return 0;
  }
  let streak = 0;
  const cursor = new Date(`${today}T00:00:00Z`);
  const hasToday = unique.includes(today);
  if (!hasToday) {
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  while (unique.includes(cursor.toISOString().slice(0, 10))) {
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}

function readStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const unique: string[] = [];
  for (const item of value) {
    if (typeof item === "string" && item.trim() && !unique.includes(item)) {
      unique.push(item);
    }
  }
  return unique;
}
