import type { AudienceLevel } from "@/types/api";

export type SuggestedQuestion = {
  id: string;
  label: string;
  prompt: string;
  requiresMatch: boolean;
};

const GENERAL: Record<AudienceLevel, SuggestedQuestion[]> = {
  beginner: [
    {
      id: "b-wicket",
      label: "What is a wicket?",
      prompt: "What is a wicket?",
      requiresMatch: false,
    },
    {
      id: "b-rrr",
      label: "Explain required run rate.",
      prompt: "Explain required run rate.",
      requiresMatch: false,
    },
    {
      id: "b-powerplay",
      label: "What is a powerplay?",
      prompt: "What is a powerplay?",
      requiresMatch: false,
    },
  ],
  casual: [
    {
      id: "c-rrr",
      label: "How does required run rate affect match pressure?",
      prompt: "How does required run rate affect match pressure?",
      requiresMatch: false,
    },
    {
      id: "c-crr",
      label: "Explain current run rate versus required run rate.",
      prompt: "Explain current run rate versus required run rate.",
      requiresMatch: false,
    },
    {
      id: "c-drs",
      label: "How does DRS work?",
      prompt: "How does DRS work?",
      requiresMatch: false,
    },
  ],
  advanced: [
    {
      id: "a-wickets",
      label: "How do wickets remaining affect chase strategy?",
      prompt: "How do wickets remaining affect chase strategy?",
      requiresMatch: false,
    },
    {
      id: "a-death",
      label: "What are death overs in T20?",
      prompt: "What are death overs in T20?",
      requiresMatch: false,
    },
    {
      id: "a-super",
      label: "What is a super over?",
      prompt: "What is a super over?",
      requiresMatch: false,
    },
  ],
};

const MATCH: Record<AudienceLevel, SuggestedQuestion[]> = {
  beginner: [
    {
      id: "bm-delivery",
      label: "Why was that delivery important?",
      prompt: "Why was that delivery important?",
      requiresMatch: true,
    },
    {
      id: "bm-situation",
      label: "Explain this match situation.",
      prompt: "Explain this match situation.",
      requiresMatch: true,
    },
  ],
  casual: [
    {
      id: "cm-momentum",
      label: "When did the momentum shift?",
      prompt: "When did the momentum shift in this match?",
      requiresMatch: true,
    },
    {
      id: "cm-wicket",
      label: "Why was that wicket tactically important?",
      prompt: "Why was that wicket tactically important?",
      requiresMatch: true,
    },
    {
      id: "cm-situation",
      label: "Explain this match situation.",
      prompt: "Explain this match situation.",
      requiresMatch: true,
    },
  ],
  advanced: [
    {
      id: "am-prob",
      label: "Explain the significant probability changes.",
      prompt: "Explain the significant probability changes in this match.",
      requiresMatch: true,
    },
    {
      id: "am-state",
      label: "Analyse the latest match-state transition.",
      prompt: "Analyse the latest match-state transition.",
      requiresMatch: true,
    },
    {
      id: "am-wickets",
      label: "How did wickets remaining shape this chase?",
      prompt: "How did wickets remaining shape this chase?",
      requiresMatch: true,
    },
  ],
};

export function suggestedQuestions(
  level: AudienceLevel,
  hasMatch: boolean,
): SuggestedQuestion[] {
  const general = GENERAL[level];
  if (!hasMatch) {
    return general;
  }
  return [...MATCH[level], ...general.slice(0, 1)];
}
