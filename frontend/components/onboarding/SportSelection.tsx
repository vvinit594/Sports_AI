"use client";

import { useState } from "react";

import { SportCard } from "@/components/onboarding/SportCard";
import type { SportId } from "@/types/onboarding";

type SportSelectionProps = {
  selected: SportId | null;
  onSelect: (sport: SportId) => void;
};

export function SportSelection({ selected, onSelect }: SportSelectionProps) {
  const [lockedPulse, setLockedPulse] = useState<SportId | null>(null);

  function handleLocked(sport: SportId) {
    setLockedPulse(sport);
    window.setTimeout(() => setLockedPulse(null), 600);
  }

  return (
    <div>
      <h1 className="text-3xl font-bold uppercase sm:text-5xl">What&apos;s your Favourite Sport?</h1>
      <p className="mt-3 max-w-xl text-muted">
        Choose the sport you love. More sports are coming soon!
      </p>
      <div className="mt-8 grid gap-4 md:grid-cols-3" role="radiogroup" aria-label="Favourite sport">
        <SportCard
          title="Cricket"
          description="Unlocked. Ball-by-ball intelligence starts here."
          selected={selected === "cricket"}
          onSelect={() => onSelect("cricket")}
          visual={<CricketVisual />}
        />
        <div className={lockedPulse === "football" ? "animate-pulse" : ""}>
          <SportCard
            title="Football"
            description="Stadium nights are on the way."
            locked
            onSelect={() => handleLocked("football")}
            visual={<LockedPitch color="#3b82f6" />}
          />
        </div>
        <div className={lockedPulse === "basketball" ? "animate-pulse" : ""}>
          <SportCard
            title="Basketball"
            description="Court vision lands in a later drop."
            locked
            onSelect={() => handleLocked("basketball")}
            visual={<LockedPitch color="#f97316" />}
          />
        </div>
      </div>
    </div>
  );
}

function CricketVisual() {
  return (
    <div className="relative h-full w-full bg-[linear-gradient(180deg,#146338,#0c2418)]">
      <div className="absolute inset-x-8 bottom-4 top-6 rounded-full border border-white/20" />
      <div className="absolute left-1/2 top-1/2 h-16 w-8 -translate-x-1/2 -translate-y-1/2 rounded bg-[#d9c27a]/50" />
    </div>
  );
}

function LockedPitch({ color }: { color: string }) {
  return (
    <div className="h-full w-full" style={{ background: `linear-gradient(180deg, ${color}33, #0b0d12)` }} />
  );
}
