"use client";

import { motion, useReducedMotion } from "framer-motion";

import { suggestedQuestions } from "@/lib/companion-questions";
import type { AudienceLevel } from "@/types/api";

type SuggestedQuestionsProps = {
  level: AudienceLevel;
  hasMatch: boolean;
  disabled?: boolean;
  onPick: (prompt: string) => void;
};

export function SuggestedQuestions({
  level,
  hasMatch,
  disabled,
  onPick,
}: SuggestedQuestionsProps) {
  const reduceMotion = useReducedMotion();
  const questions = suggestedQuestions(level, hasMatch);

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {questions.map((question) => (
        <motion.button
          key={question.id}
          type="button"
          disabled={disabled}
          whileHover={reduceMotion || disabled ? undefined : { y: -2 }}
          whileTap={reduceMotion || disabled ? undefined : { scale: 0.98 }}
          onClick={() => onPick(question.prompt)}
          className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-left text-sm text-white/85 hover:border-[var(--red)] hover:text-white disabled:opacity-40"
        >
          {question.label}
        </motion.button>
      ))}
    </div>
  );
}
