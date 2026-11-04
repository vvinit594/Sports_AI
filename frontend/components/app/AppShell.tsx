import type { ReactNode } from "react";

import { AppFooter } from "@/components/app/AppFooter";
import { AppNav } from "@/components/app/AppNav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100svh] bg-[var(--ink)]">
      <AppNav />
      <div className="mx-auto max-w-6xl px-5 py-8 md:px-8">{children}</div>
      <AppFooter />
    </div>
  );
}
