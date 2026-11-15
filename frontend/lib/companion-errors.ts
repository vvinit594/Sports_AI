import type { ChatMessage } from "../types/companion";

const PROVIDER_MESSAGES: Record<string, string> = {
  unsupported_model:
    "PulseIQ could not reach the configured Gemini model. Ask the operator to set LLM_MODEL to a current Gemini id such as gemini-3.8-flash, then retry.",
  invalid_credentials:
    "AI explanations are temporarily unavailable due to a provider configuration issue.",
  invalid_request:
    "Gemini rejected this explanation request. The server model configuration needs an update.",
  rate_limited:
    "Gemini is temporarily busy. Please wait a moment before retrying.",
  timeout:
    "PulseIQ couldn't finish this explanation in time. Your match context is preserved. Please try again.",
  content_blocked:
    "Gemini blocked this prompt. Try a different delivery sequence from the same historical match.",
  provider_unavailable:
    "The explanation provider is not configured on the server.",
  provider_error:
    "The AI service is temporarily unavailable. Your question has been saved.",
  malformed_output:
    "Gemini returned an unusable explanation. Retry the same match and sequence; PulseIQ will not invent a substitute.",
  network_error: "Could not reach the PulseIQ API. Check your connection and retry.",
  request_failed:
    "The AI service is temporarily unavailable. Your question has been saved.",
};

const RETRYABLE_CODES = new Set([
  "network_error",
  "timeout",
  "rate_limited",
  "provider_error",
  "provider_unavailable",
  "malformed_output",
  "request_failed",
  "content_blocked",
]);

const PERMANENT_CODES = new Set([
  "invalid_credentials",
  "unsupported_model",
  "invalid_request",
  "validation_error",
  "match_not_found",
  "sequence_not_found",
]);

export function companionErrorMessage(
  code: string,
  fallback: string,
  requestId?: string | null,
): string {
  const base = PROVIDER_MESSAGES[code] ?? fallback;
  if (!requestId) {
    return base;
  }
  return `${base}\nReference ${requestId}`;
}

export function isRetryableCompanionError(
  code: string | undefined,
  status?: number,
): boolean {
  if (code && PERMANENT_CODES.has(code)) {
    return false;
  }
  if (code && RETRYABLE_CODES.has(code)) {
    return true;
  }
  if (status === 401 || status === 403 || status === 422 || status === 400) {
    return false;
  }
  if (
    status === 0 ||
    status === 429 ||
    status === 502 ||
    status === 503 ||
    status === 504
  ) {
    return true;
  }
  return false;
}

export function shouldApplyRequestResult(
  startedSeq: number,
  currentSeq: number,
  startedConversationId: string,
  currentConversationId: string | null,
): boolean {
  return (
    startedSeq === currentSeq && startedConversationId === currentConversationId
  );
}

export function composerUsable(pending: boolean, hydrated: boolean): boolean {
  return hydrated && !pending;
}

export function suggestedQuestionsDisabled(pending: boolean): boolean {
  return pending;
}

export function messageIsRetryable(message: ChatMessage): boolean {
  return (
    message.role === "assistant" &&
    Boolean(message.error && message.retryText) &&
    isRetryableCompanionError(message.error)
  );
}

export function retryActionVisible(message: ChatMessage, pending: boolean): boolean {
  return !pending && messageIsRetryable(message);
}
