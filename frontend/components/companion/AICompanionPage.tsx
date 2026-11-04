"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";

import { ChatHeader } from "@/components/companion/ChatHeader";
import { ChatSidebar } from "@/components/companion/ChatSidebar";
import { ChatWelcome } from "@/components/companion/ChatWelcome";
import { CompanionProvider, useCompanion } from "@/hooks/useCompanion";
import { MatchContextPanel } from "@/components/companion/MatchContextPanel";
import { MatchSelector } from "@/components/companion/MatchSelector";
import { MessageComposer } from "@/components/companion/MessageComposer";
import { MessageList } from "@/components/companion/MessageList";
import { SuggestedQuestions } from "@/components/companion/SuggestedQuestions";

export function AICompanionPage() {
  return (
    <CompanionProvider>
      <CompanionLayout />
    </CompanionProvider>
  );
}

function CompanionLayout() {
  const { hydrated, active, pending, send, retry } = useCompanion();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const reduceMotion = useReducedMotion();
  const messages = active?.messages ?? [];
  const hasMatch = Boolean(active?.selectedMatchId);

  return (
    <div className="flex h-full min-h-0 bg-[var(--ink)]">
      <motion.aside
        initial={false}
        animate={{
          width: sidebarCollapsed ? 0 : 288,
          opacity: sidebarCollapsed ? 0 : 1,
        }}
        transition={reduceMotion ? { duration: 0 } : { duration: 0.22, ease: "easeOut" }}
        className={`hidden h-full shrink-0 overflow-hidden border-white/10 lg:block ${
          sidebarCollapsed ? "pointer-events-none border-0" : "border-r"
        }`}
        aria-hidden={sidebarCollapsed}
      >
        <div className="h-full w-72">
          <ChatSidebar />
        </div>
      </motion.aside>
      <AnimatePresence>
        {sidebarOpen ? (
          <Drawer
            side="left"
            hideFrom="lg"
            reduceMotion={Boolean(reduceMotion)}
            onClose={() => setSidebarOpen(false)}
          >
            <ChatSidebar />
          </Drawer>
        ) : null}
      </AnimatePresence>

      <section className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          desktopSidebarExpanded={!sidebarCollapsed}
          onOpenMobileSidebar={() => setSidebarOpen(true)}
          onToggleDesktopSidebar={() => setSidebarCollapsed((current) => !current)}
          onOpenContext={() => setContextOpen(true)}
        />
        <div className="min-h-0 flex-1 overflow-y-auto">
          {!hydrated ? (
            <p className="p-6 text-sm text-muted">Restoring conversations…</p>
          ) : messages.length === 0 ? (
            <ChatWelcome
              level={active?.audienceLevel ?? "beginner"}
              hasMatch={hasMatch}
              disabled={pending}
              onPick={(prompt) => void send(prompt)}
            />
          ) : (
            <>
              <MessageList messages={messages} pending={pending} onRetry={(text) => void retry(text)} />
              <div className="px-4 pb-4">
                <SuggestedQuestions
                  level={active?.audienceLevel ?? "beginner"}
                  hasMatch={hasMatch}
                  disabled={pending}
                  onPick={(prompt) => void send(prompt)}
                />
              </div>
            </>
          )}
        </div>
        <MessageComposer pending={pending} disabled={!hydrated} onSend={(text) => void send(text)} />
      </section>

      <aside className="hidden h-full w-80 shrink-0 border-l border-white/10 xl:block">
        <MatchContextPanel onChangeMatch={() => setSelectorOpen(true)} />
      </aside>
      <AnimatePresence>
        {contextOpen ? (
          <Drawer
            side="right"
            hideFrom="xl"
            reduceMotion={Boolean(reduceMotion)}
            onClose={() => setContextOpen(false)}
          >
            <MatchContextPanel
              onChangeMatch={() => {
                setContextOpen(false);
                setSelectorOpen(true);
              }}
            />
          </Drawer>
        ) : null}
      </AnimatePresence>
      <MatchSelector open={selectorOpen} onClose={() => setSelectorOpen(false)} />
    </div>
  );
}

function Drawer({
  side,
  hideFrom,
  onClose,
  reduceMotion,
  children,
}: {
  side: "left" | "right";
  hideFrom: "lg" | "xl";
  onClose: () => void;
  reduceMotion: boolean;
  children: ReactNode;
}) {
  const x = side === "left" ? -24 : 24;
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <motion.div
      className={`fixed inset-0 z-40 ${hideFrom === "lg" ? "lg:hidden" : "xl:hidden"}`}
      initial={{ opacity: reduceMotion ? 1 : 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: reduceMotion ? 1 : 0 }}
    >
      <button
        type="button"
        aria-label="Close panel"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      <motion.div
        initial={reduceMotion ? false : { x }}
        animate={{ x: 0 }}
        exit={reduceMotion ? undefined : { x }}
        className={`absolute top-0 h-full w-[min(20rem,90vw)] border-white/10 bg-[var(--ink)] ${
          side === "left" ? "left-0 border-r" : "right-0 border-l"
        }`}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}
