"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useRouter } from "next/navigation";

import { StadiumBackdrop } from "@/components/atmosphere/StadiumBackdrop";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";

export function HeroSection() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();

  return (
    <section className="stadium-hero relative isolate min-h-[100svh] overflow-hidden">
      <StadiumBackdrop />
      <SiteHeader />
      <div className="relative z-10 mx-auto flex min-h-[100svh] max-w-5xl flex-col items-center justify-center px-5 pb-28 pt-28 text-center md:px-8">
        <motion.p
          initial={reduceMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-5 text-xs font-semibold uppercase tracking-[0.38em] text-[var(--gold)]"
        >
          Feel Every Moment. Understand Every Move.
        </motion.p>
        <motion.h1
          initial={reduceMotion ? false : { opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.08 }}
          className="max-w-4xl text-4xl leading-[0.95] font-bold uppercase sm:text-6xl md:text-7xl lg:text-8xl"
        >
          The game is more than just a score.
        </motion.h1>
        <motion.p
          initial={reduceMotion ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.18 }}
          className="mt-6 max-w-2xl text-base text-white/75 sm:text-lg"
        >
          Experience cricket differently. Discover the moments, understand the
          momentum and feel every move with AI-powered match intelligence.
        </motion.p>
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.28 }}
          className="absolute inset-x-0 bottom-10 flex justify-center px-5"
        >
          <Button
            size="xl"
            className="min-w-[240px]"
            onClick={() => router.push("/onboarding")}
          >
            Let&apos;s play
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
