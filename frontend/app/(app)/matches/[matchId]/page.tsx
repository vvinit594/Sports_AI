import type { Metadata } from "next";

import { MatchDestination } from "@/components/matches/MatchDestination";

export const metadata: Metadata = {
  title: "PulseIQ — Match",
};

export default async function MatchPage({
  params,
}: {
  params: Promise<{ matchId: string }>;
}) {
  const { matchId } = await params;
  return <MatchDestination matchId={matchId} />;
}
