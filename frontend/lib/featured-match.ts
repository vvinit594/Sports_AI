import type { MatchSummary } from "@/types/api";

function dateKey(match: MatchSummary): string {
  return match.dates[0] ?? "9999-99-99";
}

export function sortMatches(matches: MatchSummary[]): MatchSummary[] {
  return [...matches].sort((left, right) => {
    const byDate = dateKey(left).localeCompare(dateKey(right));
    if (byDate !== 0) {
      return byDate;
    }
    return left.source_match_id.localeCompare(right.source_match_id);
  });
}

function teamMatchesFavourite(team: string, favourite: string): boolean {
  const left = team.toLowerCase();
  const right = favourite.toLowerCase();
  return left === right || left.includes(right) || right.includes(left);
}

export function selectFeaturedMatch(
  matches: MatchSummary[],
  favouriteTeam: string | null,
): MatchSummary | null {
  const ordered = sortMatches(matches);
  if (ordered.length === 0) {
    return null;
  }
  if (favouriteTeam) {
    const withTeam = ordered.filter((match) =>
      match.teams.some((team) => teamMatchesFavourite(team, favouriteTeam)),
    );
    if (withTeam.length > 0) {
      return withTeam[0];
    }
  }
  return ordered[0];
}
