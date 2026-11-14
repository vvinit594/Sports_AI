import type { Metadata } from "next";
import localFont from "next/font/local";

import { OnboardingProvider } from "@/components/providers/OnboardingProvider";
import { ProgressProvider } from "@/components/providers/ProgressProvider";

import "./globals.css";

const display = localFont({
  src: "./fonts/oswald-latin-wght-normal.woff2",
  variable: "--font-oswald",
  display: "swap",
  weight: "200 700",
});

const body = localFont({
  src: "./fonts/plus-jakarta-sans-latin-wght-normal.woff2",
  variable: "--font-jakarta",
  display: "swap",
  weight: "200 800",
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
        <OnboardingProvider>
          <ProgressProvider>{children}</ProgressProvider>
        </OnboardingProvider>
      </body>
    </html>
  );
}
