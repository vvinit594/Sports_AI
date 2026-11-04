"use client";

import {
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
} from "lucide-react";
import type { ReactNode } from "react";

import { PLAYBACK_SPEEDS } from "@/lib/replay";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function ReplayControls() {
  const {
    sequence,
    sequences,
    playing,
    speed,
    setSpeed,
    play,
    pause,
    next,
    previous,
    restart,
    seek,
    currentState,
  } = useLiveIntelligence();

  const min = sequences[0] ?? 0;
  const max = sequences[sequences.length - 1] ?? 0;
  const delivery = currentState?.last_delivery;
  const atEnd = sequence === max;
  const atStart = sequence === min;

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
            Ball-by-ball replay
          </p>
          <p className="mt-1 text-sm text-white/80">
            Sequence {sequence} of {max}
            {delivery
              ? ` · ${delivery.batter} vs ${delivery.bowler}`
              : " · pre-match snapshot"}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {PLAYBACK_SPEEDS.map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={speed === item}
              onClick={() => setSpeed(item)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                speed === item
                  ? "bg-[var(--red)] text-white"
                  : "border border-white/15 text-white/70 hover:text-white"
              }`}
            >
              {item}x
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Control
          label="Restart replay"
          onClick={restart}
          icon={<RotateCcw size={16} />}
        />
        <Control
          label="Previous delivery"
          onClick={previous}
          disabled={atStart}
          icon={<SkipBack size={16} />}
        />
        <button
          type="button"
          onClick={playing ? pause : play}
          disabled={!playing && atEnd}
          className="grid h-12 w-12 place-items-center rounded-full bg-[var(--red)] text-white disabled:opacity-40"
          aria-label={playing ? "Pause replay" : "Play replay"}
        >
          {playing ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <Control
          label="Next delivery"
          onClick={next}
          disabled={atEnd}
          icon={<SkipForward size={16} />}
        />
      </div>

      <label className="mt-4 block">
        <span className="sr-only">Seek delivery sequence</span>
        <input
          type="range"
          min={min}
          max={max}
          value={sequence}
          onChange={(event) => seek(Number(event.target.value))}
          className="w-full accent-[var(--red)]"
        />
      </label>
    </section>
  );
}

function Control({
  label,
  onClick,
  icon,
  disabled,
}: {
  label: string;
  onClick: () => void;
  icon: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="grid h-11 w-11 place-items-center rounded-full border border-white/15 text-white hover:bg-white/10 disabled:opacity-40"
    >
      {icon}
    </button>
  );
}
