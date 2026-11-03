"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Activity, Eye, Sparkles } from "lucide-react";

const features = [
  {
    icon: Eye,
    title: "Understand the game",
    copy: "See why a delivery matters, not just what the scoreboard says.",
  },
  {
    icon: Activity,
    title: "Discover turning points",
    copy: "Catch momentum swings, wickets under pressure and chase-shifting balls.",
  },
  {
    icon: Sparkles,
    title: "AI-powered insights",
    copy: "Explanations tailored to beginner, casual and advanced cricket fans.",
  },
];

export function FeatureSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="about" className="relative bg-[var(--ink)] px-5 py-24 md:px-8">
      <div className="mx-auto max-w-6xl">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--red)]">
          Why PulseIQ?
        </p>
        <h2 className="mt-3 max-w-3xl text-3xl font-bold uppercase sm:text-5xl">
          Built for fans who want the story behind every ball.
        </h2>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {features.map((feature, index) => (
            <motion.article
              key={feature.title}
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ delay: index * 0.08 }}
              className="rounded-[var(--radius-lg)] border border-white/10 bg-[var(--surface)] p-6"
            >
              <feature.icon className="mb-5 text-[var(--gold)]" />
              <h3 className="text-xl font-semibold">{feature.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted">{feature.copy}</p>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
