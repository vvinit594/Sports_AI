const PROVIDER_MESSAGES: Record<string, string> = {
  unsupported_model:
    "PulseIQ could not reach the configured Gemini model. Ask the operator to set LLM_MODEL to a current Gemini id such as gemini-3.8-flash, then retry.",
  invalid_credentials:
    "Gemini rejected the server credentials. The API host needs a valid GEMINI_API_KEY.",
  invalid_request:
    "Gemini rejected this explanation request. Retry once; if it persists, the server model configuration needs an update.",
  rate_limited:
    "Gemini is rate-limiting PulseIQ. Wait a moment, then retry the same match and sequence.",
  timeout:
    "Gemini timed out before finishing this explanation. Retry the same match and sequence.",
  content_blocked:
    "Gemini blocked this prompt. Try a different delivery sequence from the same historical match.",
  provider_unavailable:
    "The explanation provider is not configured on the server.",
  provider_error:
    "The Gemini explanation service is temporarily unavailable. Retry the same match and sequence.",
  malformed_output:
    "Gemini returned an unusable explanation. Retry the same match and sequence; PulseIQ will not invent a substitute.",
  network_error: "Could not reach the PulseIQ API. Check your connection and retry.",
};

export function companionErrorMessage(code: string, fallback: string): string {
  return PROVIDER_MESSAGES[code] ?? fallback;
}

export function isRetryableCompanionError(code: string | undefined): boolean {
  if (!code) {
    return false;
  }
  return code !== "validation_error" && code !== "match_not_found";
}
