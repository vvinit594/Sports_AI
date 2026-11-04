"use client";

import { Logo } from "@/components/brand/Logo";
import { SuggestedQuestions } from "@/components/companion/SuggestedQuestions";
import type { AudienceLevel } from "@/types/api";

type ChatWelcomeProps = {
  level: AudienceLevel;
  hasMatch: boolean;
  disabled?: boolean;
  onPick: (prompt: string) => void;
};

export function ChatWelcome({ level, hasMatch, disabled, onPick }: ChatWelcomeProps) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-10 text-center">
      <Logo />
      <h2 className="mt-8 text-4xl font-bold uppercase sm:text-5xl">
        Let&apos;s talk cricket.
      </h2>
      <p className="mt-4 max-w-lg text-white/75">
        Ask a cricket question, or pick a historical sample and we&apos;ll explain a
        reconstructed match state. This companion does not invent live scores and
        does not remember turns on the server.
      </p>
      <div className="mt-8 w-full">
        <SuggestedQuestions
          level={level}
          hasMatch={hasMatch}
          disabled={disabled}
          onPick={onPick}
        />
      </div>
    </div>
  );
}
