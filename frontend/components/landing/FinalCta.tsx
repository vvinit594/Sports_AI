"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";

export function FinalCta() {
  const router = useRouter();

  return (
    <section className="relative overflow-hidden px-5 py-24 md:px-8">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,59,74,0.18),transparent_55%)]" />
      <div className="relative mx-auto max-w-4xl rounded-[32px] border border-white/10 bg-[var(--surface)] px-6 py-16 text-center md:px-16">
        <h2 className="text-3xl font-bold uppercase sm:text-5xl">Step onto the field.</h2>
        <p className="mx-auto mt-4 max-w-xl text-muted">
          Set your sport, pick your level and start seeing cricket with PulseIQ
          intelligence.
        </p>
        <div className="mt-8 flex justify-center">
          <Button size="xl" onClick={() => router.push("/onboarding")}>
            Let&apos;s play
          </Button>
        </div>
      </div>
    </section>
  );
}
