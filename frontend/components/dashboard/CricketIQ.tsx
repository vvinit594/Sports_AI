"use client";

import { Card } from "@/components/ui/Card";
import { learningStreak } from "@/lib/progress-storage";
import { useProgress } from "@/hooks/useProgress";

const BADGES = [
  {
    id: "first-match",
    title: "First Match Explored",
    hint: "Open any historical match page.",
    earned: (explored: number) => explored >= 1,
  },
  {
    id: "momentum",
    title: "Momentum Reader",
    hint: "Open a detected moment card.",
    earned: (_explored: number, moments: number) => moments >= 1,
  },
  {
    id: "basics",
    title: "Cricket Basics",
    hint: "Complete a Learn the Game topic.",
    earned: (_e: number, _m: number, topics: number) => topics >= 1,
  },
  {
    id: "analyst",
    title: "Match Analyst",
    hint: "Explore three matches or ask PulseIQ once.",
    earned: (explored: number, _m: number, _t: number, asked: boolean) =>
      explored >= 3 || asked,
  },
] as const;

const CHALLENGES = [
  "Open a historical match from the catalog.",
  "Read a detected chase moment.",
  "Ask PulseIQ a grounded question.",
  "Finish the required-run-rate lesson.",
];

export function CricketIQ() {
  const { progress, hydrated } = useProgress();
  const explored = progress.exploredMatchIds.length;
  const moments = progress.readMomentKeys.length;
  const topics = progress.completedTopicIds.length;
  const asked = progress.askedPulseIQ;
  const earnedCount = BADGES.filter((badge) =>
    badge.earned(explored, moments, topics, asked),
  ).length;
  const percent = Math.round((earnedCount / BADGES.length) * 100);
  const streak = learningStreak(progress.visitDates);

  return (
    <section className="mt-12">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Cricket IQ
      </p>
      <h2 className="mt-2 text-3xl font-bold uppercase">Learning &amp; progress</h2>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        Local progress on this device. These badges track exploration and learning.
        They are not competitive rankings and they are not stored on the server.
      </p>
      <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm text-muted">Cricket IQ</p>
              <p className="font-display text-5xl">{hydrated ? `${percent}` : "—"}</p>
            </div>
            <p className="text-sm text-[var(--electric)]">
              {hydrated ? `${streak}-day learning streak` : "…"}
            </p>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="progress-fill h-full rounded-full bg-[var(--red)]"
              style={{ width: `${hydrated ? percent : 0}%` }}
            />
          </div>
          <ul className="mt-5 space-y-2 text-sm text-white/80">
            {CHALLENGES.map((challenge) => (
              <li key={challenge} className="flex gap-2">
                <span className="text-[var(--gold)]">▸</span>
                {challenge}
              </li>
            ))}
          </ul>
        </Card>
        <div className="grid gap-3 sm:grid-cols-2">
          {BADGES.map((badge) => {
            const earned = hydrated
              ? badge.earned(explored, moments, topics, asked)
              : false;
            return (
              <Card
                key={badge.id}
                className={earned ? "border-[var(--electric)]/40" : "opacity-80"}
              >
                <p className="text-xs uppercase tracking-[0.16em] text-muted">
                  {earned ? "Earned" : "Locked"} · local
                </p>
                <h3 className="mt-2 font-display text-xl uppercase">{badge.title}</h3>
                <p className="mt-2 text-sm text-muted">{badge.hint}</p>
              </Card>
            );
          })}
        </div>
      </div>
      {topics > 0 ? (
        <p className="mt-4 text-sm text-white/70">
          Completed learning topics: {progress.completedTopicIds.join(", ")}
        </p>
      ) : (
        <p className="mt-4 text-sm text-muted">No learning topics completed yet.</p>
      )}
    </section>
  );
}
