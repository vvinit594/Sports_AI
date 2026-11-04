"use client";

import { PanelLeft, PanelRight } from "lucide-react";

type ChatHeaderProps = {
  desktopSidebarExpanded: boolean;
  onOpenMobileSidebar: () => void;
  onToggleDesktopSidebar: () => void;
  onOpenContext: () => void;
};

export function ChatHeader({
  desktopSidebarExpanded,
  onOpenMobileSidebar,
  onToggleDesktopSidebar,
  onOpenContext,
}: ChatHeaderProps) {
  return (
    <div className="border-b border-white/10 px-4 py-4 md:px-6">
      <div className="flex items-start justify-between gap-3">
        <button
          type="button"
          className="grid h-10 w-10 place-items-center rounded-full border border-white/15 lg:hidden"
          aria-label="Open conversations"
          onClick={onOpenMobileSidebar}
        >
          <PanelLeft size={16} />
        </button>
        <button
          type="button"
          className="hidden h-10 w-10 place-items-center rounded-full border border-white/15 lg:grid"
          aria-label={desktopSidebarExpanded ? "Hide conversations" : "Show conversations"}
          aria-expanded={desktopSidebarExpanded}
          onClick={onToggleDesktopSidebar}
        >
          <PanelLeft size={16} />
        </button>
        <div className="min-w-0 flex-1 text-center lg:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
            Your cricket brain. Always in the game.
          </p>
          <h1 className="mt-1 text-2xl font-bold uppercase sm:text-3xl">
            PulseIQ AI Companion
          </h1>
          <p className="mt-1 text-sm text-white/70">Every question has a game behind it.</p>
        </div>
        <button
          type="button"
          className="grid h-10 w-10 place-items-center rounded-full border border-white/15 xl:hidden"
          aria-label="Open match context"
          onClick={onOpenContext}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </div>
  );
}
