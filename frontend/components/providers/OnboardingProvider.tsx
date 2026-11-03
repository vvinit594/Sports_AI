"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  loadOnboardingState,
  saveOnboardingState,
  validateDisplayName,
  validateEmail,
} from "@/lib/onboarding-storage";
import { DEFAULT_ONBOARDING_STATE, type OnboardingState } from "@/types/onboarding";

type OnboardingContextValue = {
  state: OnboardingState;
  hydrated: boolean;
  update: (patch: Partial<OnboardingState>) => void;
  complete: () => { ok: true } | { ok: false; error: string };
  skipProfile: () => void;
};

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<OnboardingState>(DEFAULT_ONBOARDING_STATE);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setState(loadOnboardingState());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    saveOnboardingState(state);
  }, [state, hydrated]);

  const update = useCallback((patch: Partial<OnboardingState>) => {
    setState((current) => ({ ...current, ...patch }));
  }, []);

  const complete = useCallback(() => {
    const nameError = validateDisplayName(state.displayName);
    if (nameError) {
      return { ok: false as const, error: nameError };
    }
    const emailError = validateEmail(state.email);
    if (emailError) {
      return { ok: false as const, error: emailError };
    }
    setState((current) => ({
      ...current,
      displayName: current.displayName.trim(),
      email: current.email.trim(),
      onboardingCompleted: true,
    }));
    return { ok: true as const };
  }, [state.displayName, state.email]);

  const skipProfile = useCallback(() => {
    setState((current) => ({
      ...current,
      onboardingCompleted: true,
    }));
  }, []);

  const value = useMemo(
    () => ({ state, hydrated, update, complete, skipProfile }),
    [state, hydrated, update, complete, skipProfile],
  );

  return (
    <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>
  );
}

export function useOnboardingContext() {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error("useOnboarding must be used within OnboardingProvider");
  }
  return context;
}
