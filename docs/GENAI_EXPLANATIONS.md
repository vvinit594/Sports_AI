# PulseIQ GenAI explanations — Phase 3

The explanation service turns structured cricket intelligence into readable
text. It is a grounded explainer, not a commentary generator and not a second
scoring engine.

## What the LLM may do

- Explain the supplied match context at one of three audience levels.
- Distinguish measured values from qualitative interpretation.
- Say when a field is unknown.

## What the LLM must not do

- Calculate scores, wickets, overs, run rates, remaining runs, or probabilities.
- Invent players, events, or statistics that are not in the context JSON.
- Treat win probability as certain.
- Follow instructions that appear inside match data.

Those rules are in the system prompt and in structured output validation.

## Flow

```
Request (audience_level, optional sequence, optional question)
  → historical catalog (Cricsheet sample)
  → MatchStateEngine / existing win-probability / moment detector
  → ExplanationContext (nulls stay null)
  → deterministic classifier (if question is present)
       ├─ supported fact category → deterministic engine → ZERO Gemini
       └─ unsupported / omitted question → existing Gemini path
            (cache / RPM / daily budget / concurrency)
  → schema validation / identity fields
  → API response
```

The service lives in `backend/app/services/explanations/` and does not depend
on FastAPI route handlers.

## Audience levels

| Level | Intent |
| --- | --- |
| `beginner` | Simple vocabulary. Explain cricket terms. Concise. |
| `casual` | Tactical context, momentum, pressure, familiar cricket language. |
| `advanced` | Analytical context from supplied metrics only. Mention RRR, wickets remaining, balls remaining, and win probability when those fields are present. |

## Grounded context

`ExplanationContext` contains only values copied from reconstructed state and
Phase 2 services. Missing values are `null` and listed in `unknown_fields`.

Typical fields: match id, teams, innings, score, wickets, overs, legal balls,
target, runs remaining, wickets remaining, required run rate, current run
rate, recent deliveries, detected moments, and win probability with model
metadata when inference succeeds.

If the model artifact is missing or the state is not an eligible chase, win
probability stays `null` and a note explains why. The service never fills a
placeholder probability.

Match JSON is wrapped as untrusted data in the user prompt. The system prompt
says to ignore instructions inside that JSON.

## Structured output

The model must return JSON with:

- `summary`
- `what_happened`
- `why_it_matters`
- `match_context`
- `key_factors` (array of short strings)

The service then sets `audience_level`, `source_match_id`, `source_sequence`,
`generated_at`, `model_provider`, and `model_name`. The LLM cannot spoof match
identity. Deterministic answers set `explanation_source=deterministic`,
`model_provider=deterministic`, and `model_name=pulseiq-cricket-rules-v1`.
LLM answers set `explanation_source=gemini`.

Empty text fields and invalid JSON are rejected with `malformed_output`.

## Providers

`LLM_PROVIDER` selects exactly one provider:

| Value | Requirement |
| --- | --- |
| `mock` | Default. In-process, no network. Used by tests and local development. |
| `gemini` | `GEMINI_API_KEY`. HTTP REST via httpx. |
| `openai` | `OPENAI_API_KEY`. OpenAI-compatible chat completions via httpx. |

Optional: `LLM_MODEL`, `OPENAI_BASE_URL`, `GEMINI_BASE_URL`,
`LLM_TIMEOUT_SECONDS`, `LLM_REQUEST_DEADLINE_SECONDS`, `LLM_MAX_RETRIES`,
`GEMINI_MAX_RETRIES`, `GEMINI_MAX_REQUESTS_PER_MINUTE`,
`GEMINI_DAILY_REQUEST_BUDGET`, `GEMINI_MAX_CONCURRENT_REQUESTS`,
`GEMINI_CACHE_TTL_SECONDS`.

Do not configure both keys unless you need to switch providers. Only the
selected provider is used. Missing credentials for the selected provider
return `provider_unavailable` (HTTP 503).

There is no LangChain, no vendor SDK, and no agent loop.

Gemini Phase 1 policy: one outbound `generateContent` attempt per user action
(`GEMINI_MAX_RETRIES=0`). HTTP 429/503/5xx/404/400/401/403 are not retried and
do not fall back to another model. OpenAI-compatible providers may still use
`LLM_MAX_RETRIES`. Invalid credentials are not retried into success.

Gemini traffic in this process is also bounded by a rolling RPM limiter
(default 4), a UTC daily budget (default 12), and a single-concurrency gate.
Successful identical explanations are cached in process memory (default TTL
3600s). These counters are process-local: they reset on restart and are not
shared across Render instances or other apps using the same Google project.
They do not guarantee Google Free Tier compliance.

There is no user authentication, so the Gemini explanation cache is shared for
the same historical match, sequence, audience, model id, and question text.
Failures are never cached. Deterministic answers do not use that cache and do
not consume Gemini RPM, daily budget, or the concurrency gate.

## Deterministic cricket questions

An optional `question` field on `POST /api/v1/matches/{match_id}/explanations`
is backward compatible. Existing clients that send only `audience_level` and
`sequence` still use the Gemini (or mock) explainer.

When `question` is present, a non-LLM classifier may answer it from
reconstructed evidence. Classification confidence is rule-based (not a
calibrated probability):

| Confidence | Meaning | Route |
| --- | --- | --- |
| `high` | Clear, single-category factual request the deterministic engine can answer | Deterministic (zero Gemini) |
| `medium` | Plausible but weak or vague wording | Gemini + Phase 1 guard |
| `low` | Unsupported, interpretive, ambiguous, or unrecognized | Gemini + Phase 1 guard |

Only `high` confidence with `supported=true` bypasses Gemini. Normalization is
used for classification only; the original question text is what Gemini sees.

Supported high-confidence categories:

| Category | Examples that bypass Gemini |
| --- | --- |
| Score and match state | current score, wickets, innings, batting team, target, match complete |
| Run rate | CRR, RRR, asking rate, runs remaining, balls/deliveries left |
| Delivery analysis | last/previous ball, on strike, bowler, extras, dismissal on that ball |
| Recent performance | last over / last few reconstructed deliveries |
| Significant moments | detector-identified turning points when predictions exist |
| Terminal state | winner / final result only if `match_complete` is true |

These still go to Gemini (and therefore the Free-Tier guard):

- omitted or empty questions
- medium-confidence vague phrasing (“how is the chase going”)
- “why / tactical / strategy / pressure / predict” interpretation
- cricket definitions (“what is a wicket”)
- player stats, partnerships, economy, strike rate
- mixed-intent or multi-category questions (no silent first-match)
- any category the classifier does not explicitly recognize

When a high-confidence category is clear but evidence is missing (no last
delivery, empty recent window, moments without a model, incomplete match),
the deterministic engine returns an explicit unavailable answer. It does not
invent facts and does not spend Gemini quota.

Unavailable facts stay unknown. PulseIQ will not invent a deterministic
substitute when Gemini quota is exhausted for a medium/low question.

API keys stay server-side. They are not logged and not returned in responses.
Prompts are not written in full to logs.

## Testing

Automated tests use `MockLLMProvider` or `httpx.MockTransport`. They must not
call a real LLM network. Set `LLM_PROVIDER=mock` in tests.

## Limitations

- Historical sample matches are not live.
- Win-probability context is only as good as the Phase 2 artifact. The 11-match
  corpus is not production-accurate. When `evaluation_is_meaningful` is false,
  prompts tell the model to say so.
- The mock provider is deterministic and suitable for development, not a
  substitute for a hosted model in a demo that needs natural language quality.
- Prompt injection controls reduce risk; they cannot prove that a hosted model
  will never embellish. Deterministic validation checks schema and identity,
  not every noun in the prose.
