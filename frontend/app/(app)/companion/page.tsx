import type { Metadata } from "next";

import { AICompanionPage } from "@/components/companion/AICompanionPage";

export const metadata: Metadata = {
  title: "PulseIQ — AI Companion",
  description: "Your cricket brain. Always in the game.",
};

export default function CompanionRoute() {
  return <AICompanionPage />;
}
