import type { AudienceLevel } from "@/types/api";

export function companionMomentHref(
  matchId: string,
  sequence: number,
  audience: AudienceLevel,
): string {
  const params = new URLSearchParams({
    match: matchId,
    sequence: String(sequence),
    level: audience,
  });
  return `/companion?${params.toString()}`;
}

export function isAudienceLevel(value: string | null): value is AudienceLevel {
  return value === "beginner" || value === "casual" || value === "advanced";
}
