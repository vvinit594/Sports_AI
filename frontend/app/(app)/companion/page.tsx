import type { Metadata } from "next";
import { Suspense } from "react";

import { AICompanionPage } from "@/components/companion/AICompanionPage";

export const metadata: Metadata = {
  title: "PulseIQ — AI Companion",
  description: "Your cricket brain. Always in the game.",
};

export default function CompanionRoute() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Opening companion…</p>}>
      <AICompanionPage />
    </Suspense>
  );
}
