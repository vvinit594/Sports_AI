import Link from "next/link";

import { Button } from "@/components/ui/Button";

export function AboutContent() {
  return (
    <article className="max-w-3xl">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        About
      </p>
      <h1 className="mt-3 text-4xl font-bold uppercase sm:text-6xl">PulseIQ</h1>
      <p className="mt-4 text-lg text-white/80">
        PulseIQ is an AI-powered cricket match intelligence layer. This build
        helps you discover historical sample matches, inspect reconstructed
        moments, and read grounded explanations.
      </p>
      <p className="mt-4 text-white/75">
        It is a sports-intelligence product, not a betting product and not a live
        broadcast. The catalog is official Cricsheet T20 samples. Chase
        probabilities use a small training corpus and are labelled as limited
        whenever they appear.
      </p>
      <Link href="/home" className="mt-8 inline-block">
        <Button>Back to insights</Button>
      </Link>
    </article>
  );
}

export function DataContent() {
  return (
    <article className="max-w-3xl">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Data and methodology
      </p>
      <h1 className="mt-3 text-4xl font-bold uppercase sm:text-6xl">
        How PulseIQ knows a ball
      </h1>
      <ul className="mt-6 space-y-4 text-white/80">
        <li>
          <strong className="text-white">Source.</strong> Official Cricsheet T20
          JSON samples. Files are completed historical matches.
        </li>
        <li>
          <strong className="text-white">State.</strong> Phase 1 reconstructs
          ball-by-ball match state. The API does not recompute cricket maths in
          the frontend.
        </li>
        <li>
          <strong className="text-white">Moments.</strong> Phase 2 detects
          significant moments from chase win-probability movement. If the model
          artifact is missing, the API says so instead of inventing highlights.
        </li>
        <li>
          <strong className="text-white">Explanations.</strong> The language model
          may only narrate supplied evidence. Scores, rates and probabilities are
          copied from the match engine.
        </li>
        <li>
          <strong className="text-white">Limitation.</strong> Eleven usable
          completed matches are not enough for production-accurate probabilities.
        </li>
      </ul>
      <Link href="/home" className="mt-8 inline-block">
        <Button>Back to insights</Button>
      </Link>
    </article>
  );
}
