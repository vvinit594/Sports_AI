export type SportId = "cricket" | "football" | "basketball";

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";

export type OnboardingStep = 1 | 2 | 3;

export type OnboardingState = {
  selectedSport: SportId | null;
  selectedLevel: ExperienceLevel | null;
  displayName: string;
  email: string;
  avatar: string | null;
  favouriteTeam: string | null;
  currentStep: OnboardingStep;
  onboardingCompleted: boolean;
};

export const DEFAULT_ONBOARDING_STATE: OnboardingState = {
  selectedSport: null,
  selectedLevel: null,
  displayName: "",
  email: "",
  avatar: null,
  favouriteTeam: null,
  currentStep: 1,
  onboardingCompleted: false,
};

export const AVAILABLE_SPORTS: SportId[] = ["cricket"];

export const FAVOURITE_TEAMS = [
  "India",
  "Australia",
  "England",
  "South Africa",
  "New Zealand",
  "Pakistan",
  "West Indies",
  "Sri Lanka",
  "Bangladesh",
  "Afghanistan",
] as const;

export const AVATARS = [
  { id: "ember", label: "Ember", accent: "#FF3B4A" },
  { id: "pitch", label: "Pitch", accent: "#2F9E5C" },
  { id: "flood", label: "Floodlight", accent: "#F3D36A" },
  { id: "navy", label: "Night Watch", accent: "#4C7CFF" },
  { id: "violet", label: "Crowd", accent: "#A56DFF" },
  { id: "ice", label: "Ice", accent: "#6EE7F2" },
] as const;
