import type { Metadata } from "next";

import { InsightsDashboard } from "@/components/dashboard/InsightsDashboard";

export const metadata: Metadata = {
  title: "PulseIQ — Personalized Insights",
  description: "Discover historical cricket matches and grounded match intelligence.",
};

export default function HomePage() {
  return <InsightsDashboard />;
}
