import type { MatchState, MomentView, OutcomeInfo } from "@/types/api";

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Date not in source";
  }
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function teamInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 3).toUpperCase();
  }
  return parts
    .slice(0, 3)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function teamAccent(name: string): string {
  let hash = 0;
  for (const char of name) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  const palette = ["#FF3B4A", "#2F9E5C", "#F3D36A", "#4C7CFF", "#A56DFF", "#6EE7F2"];
  return palette[hash % palette.length];
}

export function formatOutcome(outcome: OutcomeInfo | null | undefined): string | null {
  if (!outcome) {
    return null;
  }
  if (outcome.winner && outcome.win_by_runs != null) {
    return `${outcome.winner} won by ${outcome.win_by_runs} run${outcome.win_by_runs === 1 ? "" : "s"}`;
  }
  if (outcome.winner && outcome.win_by_wickets != null) {
    return `${outcome.winner} won by ${outcome.win_by_wickets} wicket${outcome.win_by_wickets === 1 ? "" : "s"}`;
  }
  if (outcome.winner && outcome.win_by_innings != null) {
    return `${outcome.winner} won by ${outcome.win_by_innings} innings`;
  }
  if (outcome.winner) {
    return `${outcome.winner} won`;
  }
  if (outcome.result) {
    return outcome.result.replace(/_/g, " ");
  }
  if (outcome.eliminator) {
    return `Eliminator: ${outcome.eliminator}`;
  }
  if (outcome.bowl_out_winner) {
    return `Bowl out: ${outcome.bowl_out_winner}`;
  }
  return null;
}

export function formatInningsScore(state: MatchState | null | undefined): string | null {
  if (!state?.batting_team) {
    return null;
  }
  return `${state.batting_team} ${state.innings_runs}/${state.innings_wickets} (${state.overs} ov)`;
}

export function formatMomentType(value: string): string {
  return value.replaceAll("_", " ");
}

export function contextString(
  context: Record<string, unknown>,
  key: string,
): string | null {
  const value = context[key];
  return typeof value === "string" && value.trim() ? value : null;
}

export function contextNumber(
  context: Record<string, unknown>,
  key: string,
): number | null {
  const value = context[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function momentScoreline(moment: MomentView): string | null {
  const batting = contextString(moment.match_context, "batting_team");
  const score = contextNumber(moment.match_context, "score");
  const wickets = contextNumber(moment.match_context, "wickets");
  const overs = contextString(moment.match_context, "overs");
  if (batting == null || score == null || wickets == null) {
    return null;
  }
  return `${batting} ${score}/${wickets}${overs ? ` (${overs} ov)` : ""}`;
}

export function formatProbability(value: number | null | undefined): string | null {
  if (value == null || Number.isNaN(value)) {
    return null;
  }
  return `${Math.round(value * 100)}%`;
}

export function formatProbabilityDelta(value: number | null | undefined): string | null {
  if (value == null || Number.isNaN(value)) {
    return null;
  }
  const points = Math.round(Math.abs(value) * 100);
  return `${value >= 0 ? "+" : "−"}${points} pts`;
}
