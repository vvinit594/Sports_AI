"use client";

import { useOnboardingContext } from "@/components/providers/OnboardingProvider";

export function useOnboarding() {
  return useOnboardingContext();
}
