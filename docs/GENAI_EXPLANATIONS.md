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
Request
  → historical catalog (Cricsheet sample)
  → MatchStateEngine / existing win-probability / moment detector
  → ExplanationContext (nulls stay null)
  → audience prompt
  → LLM provider (JSON only)
  → schema validation
  → identity fields overwritten by the service
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
identity.

Empty text fields and invalid JSON are rejected with `malformed_output`.

## Providers

`LLM_PROVIDER` selects exactly one provider:

| Value | Requirement |
| --- | --- |
| `mock` | Default. In-process, no network. Used by tests and local development. |
| `gemini` | `GEMINI_API_KEY`. HTTP REST via httpx. |
| `openai` | `OPENAI_API_KEY`. OpenAI-compatible chat completions via httpx. |

Optional: `LLM_MODEL`, `OPENAI_BASE_URL`, `GEMINI_BASE_URL`,
`LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`.

Do not configure both keys unless you need to switch providers. Only the
selected provider is used. Missing credentials for the selected provider
return `provider_unavailable` (HTTP 503).

There is no LangChain, no vendor SDK, and no agent loop. Timeouts and 429/5xx
responses use bounded retries (`LLM_MAX_RETRIES`, default 2, maximum 5).
Invalid credentials are not retried into success.

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
