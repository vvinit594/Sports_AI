# PulseIQ Architecture — Phase 1, Phase 2, and Phase 3

## Scope

Phase 1 reconstructs cricket match state. Phase 2 adds chase-win features,
baseline models, inference, and deterministic moment detection. Phase 3 adds a
modular FastAPI application and a provider-independent GenAI explanation
service. There is still no database, cache, frontend, live cricket provider,
authentication, or agent framework.

```
Cricsheet JSON (historical samples)
      │
      ▼
ingestion.parser
      │
      ▼
NormalizedMatch
      │
      ├── match_engine.MatchStateEngine ──► MatchState[]
      ├── match_engine.validate_match ───► ValidationReport
      ├── replay.ReplayEngine ───────────► seek / next / restart
      │
      ▼
ml.features / ml.dataset_builder
      │
      ├── ml.train / ml.evaluate / ml.model_registry
      ├── ml.inference
      └── intelligence.moment_detector
      │
      ▼
services.api.catalog / intelligence   (read-only wrappers)
services.explanations                 (grounded LLM explainer)
      │
      ▼
FastAPI  /api/v1
```

## Package layout

| Path | Responsibility |
| --- | --- |
| `backend/app/core` | Cricket rules, constants, exceptions, settings, logging |
| `backend/app/schemas` | Normalized Pydantic models and API contracts |
| `backend/app/api` | FastAPI routes, dependencies, structured errors |
| `backend/app/services/ingestion` | Cricsheet parser |
| `backend/app/services/match_engine` | State reconstruction and validation |
| `backend/app/services/replay` | Deterministic historical replay |
| `backend/app/services/ml` | Features, dataset, train, evaluate, inference |
| `backend/app/services/intelligence` | Win-probability series and moment detection |
| `backend/app/services/api` | Historical catalog and API wrappers |
| `backend/app/services/explanations` | Grounded explanation service and LLM providers |
| `backend/models` | Local Joblib artifacts (gitignored binaries) |
| `backend/scripts` | Ingest, replay, audit, train, and evaluate CLIs |
| `backend/tests` | Unit, validation, real-match, Phase 2, and API tests |
| `data/raw/cricsheet/samples` | Small official Cricsheet T20 sample |

The API does not duplicate cricket calculations. Route handlers call catalog
and explanation services. Those services call the existing Phase 1 and Phase 2
modules.

See `docs/API.md`, `docs/GENAI_EXPLANATIONS.md`, and `docs/MODEL_CARD.md`.

## Design decisions

### Modular monolith, not services

Parsing, reconstruction, replay, ML, explanations, and HTTP stay in one
package. There is no message bus, Kafka, Redis, or microservice split.

### Historical catalog, live-ready boundary

`MatchCatalog` loads local Cricsheet JSON and reconstructs states once. The
lookup surface (`list_summaries`, `get`, `state_at`) is the seam for a future
live provider. API contracts already label payloads as
`historical_cricsheet`. Historical files are not presented as live matches.

### Source fields vs derived fields

The parser copies Cricsheet fields. The engine derives match-state metrics
that cricket requires but the file does not store on every ball:

- legal-ball count
- overs notation
- current and required run rate
- balls remaining
- wickets remaining
- runs remaining

Derived values are labeled. Super-over chase targets are the one case where
Cricsheet often omits `target`; the engine may derive `previous super-over
total + 1` and marks `target_source = derived_previous_innings`.

Regulation chase targets are taken from Cricsheet. They are not invented,
because Duckworth-Lewis matches would be wrong if we assumed `first innings + 1`.

### Legal deliveries

A delivery is illegal only when `extras.wides` or `extras.noballs` is present.
Byes, leg-byes, and penalty extras remain legal. A wicket does not imply a
legal delivery.

### Wickets

`retired hurt` and `retired not out` are stored as wicket events but do not
count toward all-out. `retired out` does count. Unknown future kinds count, so
all-out cannot be silently under-counted.

### Super overs

Super-over innings are flagged from the source `super_over` field. Their runs
are not added to regulation innings totals. Multiple super-over pairs are
supported.

### Replay determinism

`ReplayEngine` reconstructs the full state list once. `next`, `seek`, and
`restart` only move a cursor. No clock, network, or random source is used.

### Win probability and moments

The API loads one registry artifact or reports `model_artifact_missing`. It
does not silently substitute a heuristic when no file exists. Moment detection
reuses `detect_significant_moments` unchanged.

The 11-match labeled sample is not a production training corpus.
`evaluation_is_meaningful` and `evaluation_limitation` are returned with
predictions.

### GenAI explanations

The LLM explains supplied evidence. Scores, wickets, run rates, and
probabilities come from the match engine and ML services. Providers are
selected by `LLM_PROVIDER` (`mock`, `gemini`, or `openai`). HTTP calls use
httpx with bounded timeouts and retries. Tests use the mock provider and never
open a real LLM network connection.

### Authentication

Not implemented. The PRD does not require user accounts in this phase.

### CORS and secrets

CORS origins come from `PULSEIQ_CORS_ORIGINS`. API keys stay in environment
variables, are not logged, and are not returned in responses. `.env` remains
gitignored.

### Redis and PostgreSQL

Not used. Redis remains optional for later caching and must not become a
local-development requirement for match processing.

## Data flow for one delivery

1. Parser assigns a match-wide sequence number.
2. Engine adds `runs.total` to the innings score.
3. Engine increments legal balls only for legal deliveries.
4. Engine increments counting wickets from dismissal kind.
5. Engine recalculates overs, CRR, remaining balls/runs, and RRR.
6. After each delivery the engine checks chase-complete, all-out, and
   overs-exhausted conditions. The first innings ending does not end the match.
7. Post-innings penalty runs are applied only on the after-innings snapshot.
   `innings_runs_at_delivery` keeps the score that was known on the ball.
8. Later source deliveries after a terminal condition are preserved and flagged
   as `source_delivery_after_terminal`. They are not active prediction states.

## HTTP data flow

1. Catalog returns a cached `NormalizedMatch` and reconstructed `MatchState` list.
2. Win-probability calls `win_probabilities_for_match` with those states.
3. Moments call `detect_significant_moments` on that prediction series.
4. Explanations build `ExplanationContext` from the same objects, then call one
   configured LLM provider for structured JSON.
