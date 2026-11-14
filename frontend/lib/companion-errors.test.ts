import assert from "node:assert/strict";
import { test } from "node:test";

import { companionErrorMessage, isRetryableCompanionError } from "./companion-errors.ts";

test("maps provider codes to actionable companion copy", () => {
  const unsupported = companionErrorMessage("unsupported_model", "fallback");
  assert.match(unsupported, /Gemini model/);
  assert.match(unsupported, /gemini-3\.8-flash/);
  assert.doesNotMatch(unsupported, /gemini-2\.0-flash/);
  assert.match(companionErrorMessage("invalid_credentials", "fallback"), /GEMINI_API_KEY/);
  assert.match(companionErrorMessage("rate_limited", "fallback"), /rate-limiting/);
  assert.match(companionErrorMessage("timeout", "fallback"), /timed out/);
  assert.match(companionErrorMessage("content_blocked", "fallback"), /blocked/);
  assert.equal(
    companionErrorMessage("unknown_code", "Keep the original"),
    "Keep the original",
  );
});

test("permanent catalog errors are not retryable as provider failures", () => {
  assert.equal(isRetryableCompanionError("match_not_found"), false);
  assert.equal(isRetryableCompanionError("unsupported_model"), true);
  assert.equal(isRetryableCompanionError("provider_error"), true);
});
