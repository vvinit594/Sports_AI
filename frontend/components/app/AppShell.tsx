"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppFooter } from "@/components/app/AppFooter";
import { AppNav } from "@/components/app/AppNav";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const companion = pathname.startsWith("/companion");
  const live = pathname.startsWith("/live");

  useEffect(() => {
    if (!companion) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [companion]);

  if (companion) {
    // Fixed to the visual viewport so 100svh/100vh cannot extend the document
    // and create a page-level scrollbar with empty ink below the chat chrome.
    return (
      <div className="fixed inset-0 flex flex-col overflow-hidden bg-[var(--ink)]">
        <AppNav />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {children}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[100svh] bg-[var(--ink)]">
      <AppNav />
      <div
        className={`mx-auto px-5 py-8 md:px-8 ${
          live ? "max-w-[90rem]" : "max-w-6xl"
        }`}
      >
        {children}
      </div>
      <AppFooter />
    </div>
  );
}
