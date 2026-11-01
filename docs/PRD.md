# PulseIQ Product Requirements — Phase 1, Phase 2, and Phase 3

## Status

Phase 1: data foundation and historical match replay engine.

Phase 2: chase-win feature pipeline, baseline models, inference, and
deterministic moment detection. The 15-match sample is not a production
training corpus.

Phase 3: backend API and grounded GenAI explanations over historical
Cricsheet samples. This is not a live cricket integration, and it is not a
production-accurate win-probability product.

## Problem

Live cricket produces a dense stream of deliveries, extras, wickets, and
scoreboard changes. Before PulseIQ can rank moments or explain them, it must
reconstruct the match situation after every ball from historical source data.
Fans then need that situation explained at a level they can understand,
without the model inventing the scoreboard.

## Phase 1 goal

Build a reliable cricket data-processing foundation that can:

1. Parse official Cricsheet T20 JSON.
2. Normalize match metadata, innings, and deliveries.
3. Reconstruct score, wickets, legal balls, overs, run rates, target, and
   remaining runs after every delivery.
4. Replay a historical match deterministically.
5. Validate reconstructed totals against the original source records.

## In scope

- Men's and women's T20 club and unofficial international matches from Cricsheet.
- Legal vs illegal delivery classification.
- Wides, no-balls, byes, leg-byes, and penalty extras.
- Wickets that do and do not count toward all-out.
- Innings transitions, one-innings matches, ties, no-results, D/L targets.
- Super overs treated as a separate phase.
- Miscounted overs, absent hurt, retired hurt, and retired out as they appear
  in the source.

## Phase 2 goal

1. Extract leakage-safe features from Phase 1 match states.
2. Build delivery-level chase-win examples with match-level chronological splits.
3. Fit simple baselines (heuristic, logistic regression, random forest).
4. Persist models and run bounded-probability inference.
5. Detect significant moments from win-probability change.

## Out of scope for Phase 2

- Claiming a reliable production win-probability model from 15 matches.
- XGBoost or deep-learning models.
- LLM explanations and agent orchestration.
- Fan profiles and personalization.
- FastAPI, PostgreSQL, Redis, and the Next.js application.
- Live cricket APIs.
- Deployment.

## Phase 3 goal

1. Expose historical match metadata and reconstructed state over HTTP.
2. Expose Phase 2 win-probability and significant-moment results without
   duplicating cricket or ML logic.
3. Generate beginner, casual, and advanced explanations from supplied evidence
   only.
4. Support one configured LLM provider (mock, Gemini, or OpenAI-compatible)
   without hardcoding keys.

## Out of scope for Phase 3

- Next.js / React frontend and dashboards.
- User authentication, profiles, and personalization storage.
- Redis, background workers, WebSockets.
- Real-time live data providers.
- Autonomous agents, RAG, vector databases.
- Kafka, microservices, and production deployment infrastructure.
- Claiming that historical sample files are live matches.
- Claiming that the 11-match model corpus is production-accurate.

## Authentication decision

Phase 3 does not add authentication. This PRD does not define user accounts,
and the API currently serves local historical samples. Auth is deferred until
a later phase that introduces users or a public network deployment.

## Success criteria

- Parser handles representative real Cricsheet T20 files without inventing fields.
- Reconstructed innings totals match source delivery sums.
- The same match replayed twice produces identical states.
- Unit, real-match, API, and mocked GenAI tests pass.
- Missing model artifacts and unsupported states return explicit unavailable
  payloads instead of fabricated numbers.
- Explanation tests do not call a hosted LLM.
