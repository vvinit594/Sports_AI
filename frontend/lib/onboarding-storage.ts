import {
  AVATARS,
  DEFAULT_ONBOARDING_STATE,
  FAVOURITE_TEAMS,
  type ExperienceLevel,
  type OnboardingState,
  type OnboardingStep,
  type SportId,
} from "@/types/onboarding";

export const ONBOARDING_STORAGE_KEY = "pulseiq.onboarding.v1";

const SPORTS: SportId[] = ["cricket", "football", "basketball"];
const LEVELS: ExperienceLevel[] = ["beginner", "intermediate", "advanced"];
const STEPS: OnboardingStep[] = [1, 2, 3];
const AVATAR_IDS = new Set<string>(AVATARS.map((item) => item.id));
const TEAM_NAMES = new Set<string>(FAVOURITE_TEAMS);

export function loadOnboardingState(): OnboardingState {
  if (typeof window === "undefined") {
    return DEFAULT_ONBOARDING_STATE;
  }
  try {
    const raw = window.localStorage.getItem(ONBOARDING_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_ONBOARDING_STATE;
    }
    const parsed: unknown = JSON.parse(raw);
    return sanitizeOnboardingState(parsed);
  } catch {
    return DEFAULT_ONBOARDING_STATE;
  }
}

export function saveOnboardingState(state: OnboardingState): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      ONBOARDING_STORAGE_KEY,
      JSON.stringify(sanitizeOnboardingState(state)),
    );
  } catch {
    // Private browsing or quota errors should not break the flow.
  }
}

export function sanitizeOnboardingState(value: unknown): OnboardingState {
  if (!value || typeof value !== "object") {
    return DEFAULT_ONBOARDING_STATE;
  }
  const record = value as Record<string, unknown>;
  const selectedSport = isSport(record.selectedSport)
    ? record.selectedSport
    : null;
  const selectedLevel = isLevel(record.selectedLevel)
    ? record.selectedLevel
    : null;
  const currentStep = isStep(record.currentStep) ? record.currentStep : 1;
  const avatar =
    typeof record.avatar === "string" && AVATAR_IDS.has(record.avatar)
      ? record.avatar
      : null;
  const favouriteTeam =
    typeof record.favouriteTeam === "string" && TEAM_NAMES.has(record.favouriteTeam)
      ? record.favouriteTeam
      : null;

  return {
    selectedSport,
    selectedLevel,
    displayName: readString(record.displayName).slice(0, 40),
    email: readString(record.email).slice(0, 120),
    avatar,
    favouriteTeam,
    currentStep,
    onboardingCompleted: record.onboardingCompleted === true,
  };
}

export function validateDisplayName(name: string): string | null {
  const trimmed = name.trim();
  if (trimmed.length < 2) {
    return "Enter a display name with at least 2 characters.";
  }
  if (trimmed.length > 40) {
    return "Keep your display name under 40 characters.";
  }
  return null;
}

export function validateEmail(email: string): string | null {
  const trimmed = email.trim();
  if (!trimmed) {
    return null;
  }
  const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
  return ok ? null : "Enter a valid email or leave it blank.";
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function isSport(value: unknown): value is SportId {
  return typeof value === "string" && SPORTS.includes(value as SportId);
}

function isLevel(value: unknown): value is ExperienceLevel {
  return typeof value === "string" && LEVELS.includes(value as ExperienceLevel);
}

function isStep(value: unknown): value is OnboardingStep {
  return typeof value === "number" && STEPS.includes(value as OnboardingStep);
}
