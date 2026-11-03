"use client";

import { Gauge, Sparkles, Trophy } from "lucide-react";

import { LevelCard } from "@/components/onboarding/LevelCard";
import type { ExperienceLevel } from "@/types/onboarding";

type LevelSelectionProps = {
  selected: ExperienceLevel | null;
  onSelect: (level: ExperienceLevel) => void;
};

const levels: Array<{
  id: ExperienceLevel;
  title: string;
  description: string;
  icon: typeof Sparkles;
}> = [
  {
    id: "beginner",
    title: "Beginner",
    description: "I'm just getting started. Help me understand cricket.",
    icon: Sparkles,
  },
  {
    id: "intermediate",
    title: "Intermediate",
    description: "I know the game and want to understand it better.",
    icon: Gauge,
  },
  {
    id: "advanced",
    title: "Advanced",
    description: "I know the game. Give me deeper insights and analytics.",
    icon: Trophy,
  },
];

export function LevelSelection({ selected, onSelect }: LevelSelectionProps) {
  return (
    <div>
      <h1 className="text-3xl font-bold uppercase sm:text-5xl">Choose Your Level!</h1>
      <p className="mt-3 max-w-xl text-muted">How deeply do you understand the game?</p>
      <div className="mt-8 grid gap-4 md:grid-cols-3" role="radiogroup" aria-label="Experience level">
        {levels.map((level) => (
          <LevelCard
            key={level.id}
            title={level.title}
            description={level.description}
            icon={<level.icon />}
            selected={selected === level.id}
            onSelect={() => onSelect(level.id)}
          />
        ))}
      </div>
    </div>
  );
}
