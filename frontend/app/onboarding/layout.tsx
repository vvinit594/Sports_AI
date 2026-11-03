import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Set up PulseIQ",
  description: "Choose your sport, level and profile to start PulseIQ.",
};

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
