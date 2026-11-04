import type { AudienceLevel } from "@/types/api";
import { findKnowledgeTopic, knowledgeAnswer, type KnowledgeTopic } from "@/lib/cricket-knowledge";

export type CompanionIntent =
  | { type: "knowledge"; topic: KnowledgeTopic }
  | { type: "match"; sequence: number | undefined; preferMoment: boolean }
  | { type: "need_match" }
  | { type: "unsupported" };

const MATCH_HINTS = [
  "this match",
  "this situation",
  "that wicket",
  "that delivery",
  "turning point",
  "momentum",
  "probability",
  "match-state",
  "match state",
  "sequence",
  "why was that",
  "analyse the",
  "analyze the",
  "explain this match",
  "explain the latest",
  "wicket important",
  "wicket tactically",
  "batting team",
  "this chase",
];

export function parseRequestedSequence(question: string): number | null {
  const match =
    question.match(/\bsequence\s+(\d+)\b/i) ??
    question.match(/\bdelivery\s+(\d+)\b/i);
  if (!match) {
    return null;
  }
  const value = Number.parseInt(match[1], 10);
  return Number.isFinite(value) ? value : null;
}

export function resolveIntent(
  question: string,
  hasMatch: boolean,
): CompanionIntent {
  const topic = findKnowledgeTopic(question);
  const sequence = parseRequestedSequence(question);
  const matchLike = isMatchQuestion(question) || sequence !== null;

  if (topic && !matchLike) {
    return { type: "knowledge", topic };
  }
  if (topic && matchLike && !hasMatch) {
    return { type: "knowledge", topic };
  }
  if (matchLike && !hasMatch) {
    return { type: "need_match" };
  }
  if (matchLike && hasMatch) {
    return {
      type: "match",
      sequence: sequence ?? undefined,
      preferMoment: prefersMoment(question),
    };
  }
  if (topic) {
    return { type: "knowledge", topic };
  }
  return { type: "unsupported" };
}

export function formatKnowledgeReply(
  topic: KnowledgeTopic,
  level: AudienceLevel,
): string {
  return `${topic.title}\n\n${knowledgeAnswer(topic, level)}\n\nThis is PulseIQ’s curated cricket learning layer, not a live model answer and not a match reconstruction.`;
}

export const NEED_MATCH_COPY =
  "That question is about a specific historical match. Choose a sample match in the context panel, then ask again. PulseIQ will not invent a fixture.";

export const UNSUPPORTED_COPY =
  "This companion can answer curated cricket basics, or explain a reconstructed state from a selected historical match using the Phase 3 explanation API. It cannot hold a free-form conversation or remember earlier turns on the server. Try a cricket definition, or select a match and ask about that situation.";

function isMatchQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return MATCH_HINTS.some((hint) => normalized.includes(hint));
}

function prefersMoment(question: string): boolean {
  const normalized = question.toLowerCase();
  return [
    "turning point",
    "momentum",
    "that wicket",
    "probability",
    "significant",
  ].some((hint) => normalized.includes(hint));
}
