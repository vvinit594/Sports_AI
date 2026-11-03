import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Welcome to PulseIQ",
};

export default function WelcomeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
