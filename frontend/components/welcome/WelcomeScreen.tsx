"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { useOnboarding } from "@/hooks/useOnboarding";

export function WelcomeScreen() {
  const { state, hydrated } = useOnboarding();
  const reduceMotion = useReducedMotion();
  const name = state.displayName.trim();

  return (
    <main className="stadium-hero relative min-h-[100svh] px-5 py-10 md:px-8">
      <div className="relative z-10 mx-auto flex min-h-[88svh] max-w-3xl flex-col items-center justify-center text-center">
        <Logo />
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-10 rounded-[32px] border border-white/10 bg-black/40 px-6 py-12 backdrop-blur-sm md:px-12"
        >
          <p className="text-xs uppercase tracking-[0.32em] text-[var(--gold)]">Welcome</p>
          <h1 className="mt-4 text-4xl font-bold uppercase sm:text-6xl">
            {hydrated && name ? `Welcome, ${name}.` : "Welcome to PulseIQ."}
          </h1>
          <p className="mt-4 text-lg text-white/75">Your game starts here.</p>
          <dl className="mt-8 grid gap-3 text-left text-sm sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <dt className="text-muted">Sport</dt>
              <dd className="mt-1 text-lg capitalize">
                {hydrated ? (state.selectedSport ?? "Not set") : "…"}
              </dd>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <dt className="text-muted">Experience</dt>
              <dd className="mt-1 text-lg capitalize">
                {hydrated ? (state.selectedLevel ?? "Not set") : "…"}
              </dd>
            </div>
            {name ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 sm:col-span-2">
                <dt className="text-muted">Display name</dt>
                <dd className="mt-1 text-lg">{name}</dd>
              </div>
            ) : null}
          </dl>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link href="/">
              <Button variant="outline">Back to home</Button>
            </Link>
            <Link href="/onboarding">
              <Button variant="secondary">Edit setup</Button>
            </Link>
          </div>
        </motion.div>
      </div>
    </main>
  );
}
