import type { Metadata } from "next";

import { LiveIntelligencePage } from "@/components/live/LiveIntelligencePage";

export const metadata: Metadata = {
  title: "PulseIQ — Live Intelligence",
  description: "Every ball. Every shift. Every insight.",
};

export default function LiveIntelligenceRoute() {
  return <LiveIntelligencePage />;
}
