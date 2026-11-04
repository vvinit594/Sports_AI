import type { Metadata } from "next";

import { MatchLibrary } from "@/components/matches/MatchLibrary";

export const metadata: Metadata = {
  title: "PulseIQ — Historical Matches",
};

export default function MatchesPage() {
  return <MatchLibrary />;
}
