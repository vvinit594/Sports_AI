import type { Metadata } from "next";
import { Oswald, Plus_Jakarta_Sans } from "next/font/google";

import { OnboardingProvider } from "@/components/providers/OnboardingProvider";

import "./globals.css";

const display = Oswald({
  subsets: ["latin"],
  variable: "--font-oswald",
  weight: ["500", "600", "700"],
});

const body = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
});

export const metadata: Metadata = {
  title: "PulseIQ — Feel Every Moment",
  description:
    "AI-powered cricket match intelligence. Discover moments, understand momentum, and feel every move.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} antialiased`}>
        <OnboardingProvider>{children}</OnboardingProvider>
      </body>
    </html>
  );
}
