import type { DeliveryApplied, MatchState } from "@/types/api";

export type PlaybackSpeed = 0.5 | 1 | 2 | 4;

export const PLAYBACK_SPEEDS: PlaybackSpeed[] = [0.5, 1, 2, 4];

export const PLAYBACK_INTERVAL_MS: Record<PlaybackSpeed, number> = {
  0.5: 1600,
  1: 800,
  2: 400,
  4: 200,
};

export type DeliveryKind =
  | "start"
  | "dot"
  | "runs"
  | "four"
  | "six"
  | "wicket"
  | "wide"
  | "noball"
  | "extra";

export function classifyDelivery(delivery: DeliveryApplied | null): DeliveryKind {
  if (!delivery) {
    return "start";
  }
  if (delivery.wickets.length > 0) {
    return "wicket";
  }
  if (delivery.is_wide) {
    return "wide";
  }
  if (delivery.is_noball) {
    return "noball";
  }
  if (!delivery.non_boundary && delivery.batter_runs === 6) {
    return "six";
  }
  if (!delivery.non_boundary && delivery.batter_runs === 4) {
    return "four";
  }
  if (delivery.extras_runs > 0) {
    return "extra";
  }
  if (delivery.total_runs > 0) {
    return "runs";
  }
  return "dot";
}

export function deliveryMarkerClass(kind: DeliveryKind): string {
  switch (kind) {
    case "wicket":
      return "bg-[var(--red)]";
    case "six":
      return "bg-[var(--gold)]";
    case "four":
      return "bg-[var(--electric)]";
    case "wide":
    case "noball":
      return "border border-dashed border-white/50 bg-transparent";
    case "extra":
      return "bg-[#a56dff]";
    case "runs":
      return "bg-white/55";
    case "start":
      return "bg-white/20";
    default:
      return "bg-white/20";
  }
}

export function deliveryLabel(kind: DeliveryKind, delivery: DeliveryApplied | null): string {
  if (!delivery) {
    return "Pre-match snapshot";
  }
  switch (kind) {
    case "wicket":
      return `Wicket · ${delivery.wickets.map((item) => item.kind).join(", ")}`;
    case "six":
      return "Six";
    case "four":
      return "Four";
    case "wide":
      return `Wide · ${delivery.total_runs} run${delivery.total_runs === 1 ? "" : "s"}`;
    case "noball":
      return `No-ball · ${delivery.total_runs} run${delivery.total_runs === 1 ? "" : "s"}`;
    case "extra":
      return `Extra · ${delivery.total_runs}`;
    case "runs":
      return `${delivery.total_runs} run${delivery.total_runs === 1 ? "" : "s"}`;
    default:
      return "Dot ball";
  }
}

export function statesBySequence(states: MatchState[]): Map<number, MatchState> {
  return new Map(states.map((state) => [state.sequence, state]));
}

export function orderedSequences(states: MatchState[]): number[] {
  return [...new Set(states.map((state) => state.sequence))].sort((a, b) => a - b);
}

export function adjacentSequence(
  sequences: number[],
  current: number,
  delta: -1 | 1,
): number | null {
  const index = sequences.indexOf(current);
  if (index < 0) {
    return sequences[0] ?? null;
  }
  return sequences[index + delta] ?? null;
}

export function nearestSequence(sequences: number[], value: number): number | null {
  if (sequences.length === 0) {
    return null;
  }
  if (sequences.includes(value)) {
    return value;
  }
  return sequences.reduce((best, item) =>
    Math.abs(item - value) < Math.abs(best - value) ? item : best,
  );
}

export function formatUnavailable(value: number | string | null | undefined): string {
  if (value == null || value === "") {
    return "—";
  }
  return String(value);
}

export function formatRate(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return value.toFixed(2);
}
