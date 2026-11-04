"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect } from "react";

import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function AchievementNotification() {
  const { toast, dismissToast } = useLiveIntelligence();
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(dismissToast, 4200);
    return () => window.clearTimeout(timer);
  }, [toast, dismissToast]);

  return (
    <AnimatePresence>
      {toast ? (
        <motion.div
          role="status"
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: 8 }}
          className="fixed right-4 bottom-4 z-40 max-w-sm rounded-2xl border border-[var(--gold)]/40 bg-black/90 px-4 py-3 shadow-[0_16px_40px_rgba(0,0,0,0.45)]"
        >
          <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--gold)]">
            Exploration
          </p>
          <p className="mt-1 font-display text-lg uppercase">{toast.title}</p>
          <p className="mt-1 text-sm text-white/75">{toast.body}</p>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
