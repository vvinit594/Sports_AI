"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppFooter } from "@/components/app/AppFooter";
import { AppNav } from "@/components/app/AppNav";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const companion = pathname.startsWith("/companion");

  if (companion) {
    return (
      <div className="flex h-[100svh] flex-col overflow-hidden bg-[var(--ink)]">
        <AppNav />
        <div className="min-h-0 flex-1">{children}</div>
      </div>
    );
  }

  return (
    <div className="min-h-[100svh] bg-[var(--ink)]">
      <AppNav />
      <div className="mx-auto max-w-6xl px-5 py-8 md:px-8">{children}</div>
      <AppFooter />
    </div>
  );
}
