import type { AudienceLevel } from "@/types/api";
import type { ChatMessage } from "@/types/companion";

export type ExplanationRetrySnapshot = {
  text: string;
  matchId: string;
  sequence: number | null;
  audience: AudienceLevel;
};

export function snapshotFromFailedMessage(
  message: ChatMessage,
  fallback?: { matchId: string | null; audience: AudienceLevel },
): ExplanationRetrySnapshot | null {
  if (message.role !== "assistant" || !message.error || !message.retryText) {
    return null;
  }
  const matchId = message.retryMatchId || fallback?.matchId || null;
  if (!matchId) {
    return null;
  }
  return {
    text: message.retryText,
    matchId,
    sequence: message.retrySequence ?? null,
    audience: message.retryAudience ?? fallback?.audience ?? "beginner",
  };
}

export function canRetryMessage(message: ChatMessage, pending: boolean): boolean {
  return (
    !pending &&
    message.role === "assistant" &&
    Boolean(message.error && message.retryText)
  );
}

export function replaceMessageById(
  messages: ChatMessage[],
  messageId: string,
  next: ChatMessage,
): ChatMessage[] {
  return messages.map((item) => (item.id === messageId ? next : item));
}

export function attachRetrySnapshot(
  message: ChatMessage,
  snapshot: ExplanationRetrySnapshot,
): ChatMessage {
  return {
    ...message,
    retryText: snapshot.text,
    retryMatchId: snapshot.matchId,
    retrySequence: snapshot.sequence,
    retryAudience: snapshot.audience,
  };
}
