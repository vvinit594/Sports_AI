"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { LevelSelection } from "@/components/onboarding/LevelSelection";
import { ProfileSetup } from "@/components/onboarding/ProfileSetup";
import { ProgressIndicator } from "@/components/onboarding/ProgressIndicator";
import { SportSelection } from "@/components/onboarding/SportSelection";
import { Button } from "@/components/ui/Button";
import { useOnboarding } from "@/hooks/useOnboarding";
import { validateDisplayName, validateEmail } from "@/lib/onboarding-storage";

export function OnboardingFlow() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const { state, hydrated, update, complete, skipProfile } = useOnboarding();
  const [direction, setDirection] = useState(1);
  const [nameError, setNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  const canAdvance = useMemo(() => {
    if (state.currentStep === 1) {
      return state.selectedSport === "cricket";
    }
    if (state.currentStep === 2) {
      return state.selectedLevel !== null;
    }
    return true;
  }, [state.currentStep, state.selectedLevel, state.selectedSport]);

  function goTo(step: 1 | 2 | 3) {
    setDirection(step > state.currentStep ? 1 : -1);
    update({ currentStep: step });
  }

  function handleLetsGo() {
    const result = complete();
    if (!result.ok) {
      setNameError(validateDisplayName(state.displayName));
      setEmailError(validateEmail(state.email));
      return;
    }
    setNameError(null);
    setEmailError(null);
    router.push("/welcome");
  }

  function handleSkip() {
    skipProfile();
    router.push("/welcome");
  }

  const variants = reduceMotion
    ? { enter: { opacity: 1 }, center: { opacity: 1 }, exit: { opacity: 1 } }
    : {
        enter: { x: direction * 48, opacity: 0 },
        center: { x: 0, opacity: 1 },
        exit: { x: direction * -48, opacity: 0 },
      };

  if (!hydrated) {
    return (
      <div className="min-h-[100svh] bg-[var(--ink)]" aria-busy="true">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 md:px-8">
          <Link href="/" aria-label="PulseIQ home">
            <Logo />
          </Link>
        </header>
      </div>
    );
  }

  return (
    <div className="min-h-[100svh] bg-[var(--ink)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 md:px-8">
        <Link href="/" aria-label="PulseIQ home">
          <Logo />
        </Link>
        <p className="hidden text-sm text-muted sm:block">Game setup</p>
      </header>
      <main className="mx-auto max-w-6xl px-5 pb-28 md:px-8">
        <ProgressIndicator step={state.currentStep} />
        <div className="relative mt-8 overflow-hidden">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={state.currentStep}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: reduceMotion ? 0 : 0.28 }}
            >
              {state.currentStep === 1 ? (
                <SportSelection
                  selected={state.selectedSport}
                  onSelect={(sport) => {
                    if (sport !== "cricket") {
                      return;
                    }
                    update({ selectedSport: sport });
                  }}
                />
              ) : null}
              {state.currentStep === 2 ? (
                <LevelSelection
                  selected={state.selectedLevel}
                  onSelect={(level) => update({ selectedLevel: level })}
                />
              ) : null}
              {state.currentStep === 3 ? (
                <ProfileSetup
                  state={state}
                  nameError={nameError}
                  emailError={emailError}
                  onChange={(patch) => {
                    setNameError(null);
                    setEmailError(null);
                    update(patch);
                  }}
                />
              ) : null}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <div className="fixed inset-x-0 bottom-0 border-t border-white/10 bg-black/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-4 md:px-8">
          <Button
            variant="ghost"
            onClick={() => {
              if (state.currentStep === 1) {
                router.push("/");
                return;
              }
              goTo((state.currentStep - 1) as 1 | 2);
            }}
          >
            Back
          </Button>
          {state.currentStep < 3 ? (
            <Button
              disabled={!canAdvance}
              onClick={() => goTo((state.currentStep + 1) as 2 | 3)}
            >
              Next
            </Button>
          ) : (
            <div className="flex flex-wrap items-center justify-end gap-3">
              <button
                type="button"
                className="text-sm font-semibold uppercase tracking-[0.16em] text-white/70 underline-offset-4 hover:text-white hover:underline"
                onClick={handleSkip}
              >
                Skip for now
              </button>
              <Button onClick={handleLetsGo}>Let&apos;s go!</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
