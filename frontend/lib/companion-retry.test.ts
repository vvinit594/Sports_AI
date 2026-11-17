import assert from "node:assert/strict";
import { test } from "node:test";

import type { ChatMessage } from "../types/companion.ts";
import {
  attachRetrySnapshot,
  canRetryMessage,
  replaceMessageById,
  snapshotFromFailedMessage,
} from "./companion-retry.ts";

function assistant(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "LLM provider request failed",
    createdAt: "2024-01-01T00:00:00.000Z",
    kind: "match",
    error: "provider_error",
    retryText: "Explain sequence 195",
    retryMatchId: "335988",
    retrySequence: 195,
    retryAudience: "casual",
    ...overrides,
  };
}

test("retry snapshot preserves match, sequence, and audience", () => {
  const snapshot = snapshotFromFailedMessage(assistant());
  assert.deepEqual(snapshot, {
    text: "Explain sequence 195",
    matchId: "335988",
    sequence: 195,
    audience: "casual",
  });
});

test("retry is blocked while a request is already pending", () => {
  const failed = assistant();
  assert.equal(canRetryMessage(failed, false), true);
  assert.equal(canRetryMessage(failed, true), false);
  assert.equal(
    snapshotFromFailedMessage(assistant({ retryMatchId: undefined })),
    null,
  );
  assert.deepEqual(
    snapshotFromFailedMessage(assistant({ retryMatchId: undefined }), {
      matchId: "335988",
      audience: "beginner",
    }),
    {
      text: "Explain sequence 195",
      matchId: "335988",
      sequence: 195,
      audience: "casual",
    },
  );
});

test("successful retry replaces the failed assistant without duplicating it", () => {
  const user: ChatMessage = {
    id: "u1",
    role: "user",
    content: "Explain sequence 195",
    createdAt: "2024-01-01T00:00:00.000Z",
  };
  const failed = assistant();
  const success = assistant({
    content: "Deccan Chargers were batting",
    error: undefined,
    retryText: undefined,
    retryMatchId: undefined,
    response: {
      summary: "Deccan Chargers were batting",
      what_happened: "A delivery in the chase",
      why_it_matters: "Required rate pressure",
      match_context: "IPL 2008 Hyderabad",
      key_factors: ["sequence 195"],
      audience_level: "casual",
      source_match_id: "335988",
      source_sequence: 195,
      generated_at: "2024-01-01T00:00:01.000Z",
      model_provider: "gemini",
      model_name: "gemini-3.8-flash",
      data_source: "historical_cricsheet",
      grounded: true,
    },
  });
  const next = replaceMessageById([user, failed], failed.id, success);
  assert.equal(next.length, 2);
  assert.equal(next[0].id, "u1");
  assert.equal(next[1].id, "a1");
  assert.equal(next[1].response?.source_match_id, "335988");
  assert.equal(next[1].response?.source_sequence, 195);
  assert.equal(next[1].error, undefined);
});

test("degraded fallback responses remain retryable without an error code", () => {
  const degraded = assistant({
    error: undefined,
    content: "AI explanation is temporarily unavailable",
    response: {
      summary: "AI explanation is temporarily unavailable",
      what_happened: "Verified facts",
      why_it_matters: "Degraded mode",
      match_context: "Historical",
      key_factors: ["score"],
      audience_level: "casual",
      source_match_id: "335988",
      source_sequence: 195,
      generated_at: "2024-01-01T00:00:01.000Z",
      model_provider: "deterministic",
      model_name: "pulseiq-cricket-rules-v1",
      data_source: "historical_cricsheet",
      grounded: true,
      explanation_source: "fallback",
      degraded: true,
      fallback_reason: "daily_budget_exhausted",
    },
  });
  assert.equal(canRetryMessage(degraded, false), true);
  assert.deepEqual(snapshotFromFailedMessage(degraded), {
    text: "Explain sequence 195",
    matchId: "335988",
    sequence: 195,
    audience: "casual",
  });
});

test("failed retry keeps the same assistant slot retryable", () => {
  const failed = assistant();
  const again = attachRetrySnapshot(
    assistant({
      id: "a1",
      content: "PulseIQ couldn't finish this explanation in time. Your match context is preserved. Please try again.",
      error: "timeout",
    }),
    {
      text: "Explain sequence 195",
      matchId: "335988",
      sequence: 195,
      audience: "casual",
    },
  );
  const next = replaceMessageById([failed], failed.id, again);
  const snapshot = snapshotFromFailedMessage(next[0]);
  assert.equal(next.length, 1);
  assert.equal(snapshot?.matchId, "335988");
  assert.equal(snapshot?.sequence, 195);
  assert.equal(snapshot?.audience, "casual");
});
