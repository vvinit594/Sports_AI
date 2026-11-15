import assert from "node:assert/strict";
import { test } from "node:test";

import type { ChatMessage } from "../types/companion.ts";
import {
  companionErrorMessage,
  composerUsable,
  isRetryableCompanionError,
  messageIsRetryable,
  retryActionVisible,
  shouldApplyRequestResult,
  suggestedQuestionsDisabled,
} from "./companion-errors.ts";

function assistant(error: string): ChatMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "failed",
    createdAt: "2024-01-01T00:00:00.000Z",
    kind: "match",
    error,
    retryText: "Explain sequence 43",
    retryMatchId: "335988",
    retrySequence: 43,
    retryAudience: "casual",
  };
}

test("maps provider codes to actionable companion copy", () => {
  const unsupported = companionErrorMessage("unsupported_model", "fallback");
  assert.match(unsupported, /Gemini model/);
  assert.match(unsupported, /gemini-3\.8-flash/);
  assert.doesNotMatch(unsupported, /gemini-2\.0-flash/);
  assert.match(
    companionErrorMessage("invalid_credentials", "fallback"),
    /provider configuration issue/,
  );
  assert.match(companionErrorMessage("rate_limited", "fallback"), /temporarily busy/);
  assert.match(
    companionErrorMessage("timeout", "fallback"),
    /couldn't finish this explanation in time/,
  );
  assert.match(
    companionErrorMessage("provider_error", "fallback"),
    /temporarily unavailable/,
  );
  assert.match(companionErrorMessage("timeout", "fallback", "abc123"), /Reference abc123/);
  assert.equal(
    companionErrorMessage("unknown_code", "Keep the original"),
    "Keep the original",
  );
});

test("classifies retryable versus permanent errors", () => {
  assert.equal(isRetryableCompanionError("timeout", 504), true);
  assert.equal(isRetryableCompanionError("provider_error", 502), true);
  assert.equal(isRetryableCompanionError("rate_limited", 429), true);
  assert.equal(isRetryableCompanionError("network_error", 0), true);
  assert.equal(isRetryableCompanionError("request_failed", 504), true);
  assert.equal(isRetryableCompanionError("invalid_credentials", 401), false);
  assert.equal(isRetryableCompanionError("invalid_credentials", 403), false);
  assert.equal(isRetryableCompanionError("unsupported_model", 404), false);
  assert.equal(isRetryableCompanionError("invalid_request", 400), false);
  assert.equal(isRetryableCompanionError("validation_error", 422), false);
});

test("timeout remains retryable while pending only hides the button", () => {
  const failed = assistant("timeout");
  assert.equal(messageIsRetryable(failed), true);
  assert.equal(retryActionVisible(failed, false), true);
  assert.equal(retryActionVisible(failed, true), false);
  assert.equal(messageIsRetryable(assistant("invalid_credentials")), false);
  assert.equal(retryActionVisible(assistant("invalid_credentials"), false), false);
});

test("pending failure still leaves composer and suggestions gated only by pending", () => {
  assert.equal(composerUsable(true, true), false);
  assert.equal(composerUsable(false, true), true);
  assert.equal(suggestedQuestionsDisabled(true), true);
  assert.equal(suggestedQuestionsDisabled(false), false);
});

test("stale conversation results are ignored", () => {
  assert.equal(shouldApplyRequestResult(1, 1, "c1", "c1"), true);
  assert.equal(shouldApplyRequestResult(1, 2, "c1", "c1"), false);
  assert.equal(shouldApplyRequestResult(1, 1, "c1", "c2"), false);
});
